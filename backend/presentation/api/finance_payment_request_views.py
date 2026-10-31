"""Financial request API and protected proof storage; all writes are server-owned."""
from collections import defaultdict
from functools import wraps
from io import BytesIO
from pathlib import Path
from uuid import uuid4
import re

from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.db.models import Q, Count
from django.http import JsonResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.text import get_valid_filename
from django.core.exceptions import SuspiciousFileOperation

from backend.application import payment_requests as service
from backend.application.finance_periods import ClosedFinancePeriod, require_open_date
from backend.infrastructure.persistence.models import (
    FinancePaymentRequestModel, FinancePayableModel, FinanceAccountModel,
    FinancePaymentProofModel, FinancePaymentModel, ApprovalRequestModel, ApprovalActionModel,
    ApprovalFlowModel, OperationLogModel,
)
from backend.infrastructure.persistence.storage import PrivateMediaStorage
from backend.presentation.api.utils import parse_json_body
from backend.presentation.api.warehouse_writeoff_views import canonical_photo
from backend.presentation.api.warehouse_views import WmsError
from backend.presentation.middlewares import login_required_domain


def endpoint(view):
    @csrf_exempt
    @login_required_domain
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        try:
            if not service.can_read(request.user_entity):
                raise service.PaymentRequestError("Permission denied", "permission_denied", 403)
            if request.method not in ("GET", "HEAD") and not service.can_manage(request.user_entity):
                raise service.PaymentRequestError("Permission denied", "permission_denied", 403)
            with transaction.atomic(): response = view(request, *args, **kwargs)
            response["Cache-Control"] = "private, no-store"
            return response
        except service.PaymentRequestError as exc:
            return JsonResponse({"error": exc.message, "code": exc.code}, status=exc.status)
        except ClosedFinancePeriod:
            return JsonResponse({"error": "Financial period is closed", "code": "period_closed"}, status=409)
    return wrapper


def page(request, key, default, maximum):
    value = request.GET.get(key, str(default))
    if not re.fullmatch(r"[0-9]{1,10}", value) or int(value)>maximum or (key=="limit" and int(value)==0):
        raise service.PaymentRequestError(f"Invalid {key}")
    return int(value)


def query_docs():
    return FinancePaymentRequestModel.objects.select_related("payable__supplier", "account", "created_by", "approval__assigned_to")


def result(doc, request, status=200):
    return JsonResponse(service.serialize(query_docs().get(id=doc.id), request.user_entity), status=status)


@endpoint
def payment_requests_view(request):
    if request.method == "GET":
        limit,offset=page(request,"limit",20,100),page(request,"offset",0,1000000000)
        qs=query_docs().order_by("-id")
        if "id" in request.GET:
            raw=request.GET["id"]
            if not re.fullmatch(r"[0-9]{1,18}",raw):raise service.PaymentRequestError("Invalid id")
            qs=qs.filter(id=int(raw))
        if request.GET.get("status"):qs=qs.filter(status=request.GET["status"])
        q=request.GET.get("q", "").strip()
        if len(q)>128:raise service.PaymentRequestError("q is too long")
        if q:qs=qs.filter(Q(request_no__icontains=q)|Q(payable__supplier__name_ru__icontains=q))
        # List DTO omits verbose history, which is always loaded in exact detail.
        docs=list(qs[offset:offset+limit])
        payments={p.payment_request_id:p for p in FinancePaymentModel.objects.filter(payment_request_id__in=[d.id for d in docs])}
        counts=dict(OperationLogModel.objects.filter(business_type=service.BUSINESS_TYPE,business_id__in=[d.id for d in docs]).values("business_id").annotate(n=Count("id")).values_list("business_id","n"))
        managing=service.can_manage(request.user_entity)
        for doc in docs: doc._list_mode=True;doc._payment_cached=payments.get(doc.id);doc._history_count=counts.get(doc.id,0)
        return JsonResponse({"items":[service.serialize(d,request.user_entity,managing) for d in docs],"count":qs.count(),"limit":limit,"offset":offset,"can_create":service.can_manage(request.user_entity)})
    if request.method!="POST":return JsonResponse({"error":"Method not allowed"},status=405)
    data=service.payload(parse_json_body(request)); fingerprint=service.canonical(data)
    existing=FinancePaymentRequestModel.objects.filter(request_id=data["request_id"]).first()
    if existing:
        if existing.creation_payload!=fingerprint:raise service.PaymentRequestError("UUID already used with different data","idempotency_conflict",409)
        return result(existing,request)
    service.validate_source(data);require_open_date(data["planned_payment_date"])
    try:
        with transaction.atomic():
            doc=FinancePaymentRequestModel.objects.create(**data,created_by_id=request.user_entity.id,creation_payload=fingerprint)
            service.audit(doc,request.user_entity,"created",ip_address=request.META.get("REMOTE_ADDR",""))
    except IntegrityError:
        existing=FinancePaymentRequestModel.objects.filter(request_id=data["request_id"]).first()
        if existing and existing.creation_payload==fingerprint:return result(existing,request)
        raise service.PaymentRequestError("Request identifier already exists","idempotency_conflict",409) from None
    return result(doc,request,201)


@endpoint
def payment_request_catalog_view(request):
    if request.method!="GET":return JsonResponse({"error":"Method not allowed"},status=405)
    limit,offset=page(request,"limit",20,100),page(request,"offset",0,1000000000)
    qs=FinancePayableModel.objects.select_related("supplier").filter(status__in=("open","partially_paid"),outstanding_amount__gt=0).order_by("id")
    q=request.GET.get("q","").strip()
    if len(q)>128:raise service.PaymentRequestError("q is too long")
    if q:qs=qs.filter(Q(supplier__name_ru__icontains=q)|Q(source_id__in=[int(q)] if re.fullmatch(r"[0-9]{1,18}",q) else []))
    if request.GET.get("payable_id"):
        raw=request.GET["payable_id"]
        if not re.fullmatch(r"[0-9]{1,18}",raw):raise service.PaymentRequestError("Invalid payable_id")
        qs=qs.filter(id=int(raw));offset=0
    accounts=FinanceAccountModel.objects.filter(is_active=True).order_by("id")
    # Accounts are bounded too; an exact account remains selectable beyond page.
    if request.GET.get("account_id"):
        raw=request.GET["account_id"]
        if not re.fullmatch(r"[0-9]{1,18}",raw):raise service.PaymentRequestError("Invalid account_id")
        accounts=accounts.filter(id=int(raw))
    return JsonResponse({"payables":[{"id":p.id,"supplier_id":p.supplier_id,"supplier_name":p.supplier.name_ru,"source_id":p.source_id,"amount":format(p.amount,".2f"),"outstanding_amount":format(p.outstanding_amount,".2f"),"currency":p.currency,"status":p.status}for p in qs[offset:offset+limit]],"payable_count":qs.count(),"accounts":[{"id":a.id,"name":a.name,"currency":a.currency}for a in accounts[:100]],"limit":limit,"offset":offset,"flow_configured":ApprovalFlowModel.objects.filter(business_type=service.BUSINESS_TYPE,is_active=True,nodes__isnull=False).exists()})


@endpoint
def payment_request_detail_view(request, request_id):
    doc=service.locked(request_id) if request.method!="GET" else query_docs().filter(id=request_id).first()
    if not doc:raise service.PaymentRequestError("Request not found","not_found",404)
    if request.method=="GET":return result(doc,request)
    if request.method!="PATCH":return JsonResponse({"error":"Method not allowed"},status=405)
    if doc.created_by_id!=request.user_entity.id:raise service.PaymentRequestError("Only the creator may edit this request","permission_denied",403)
    if doc.status not in service.EDITABLE:raise service.PaymentRequestError("Request is immutable in this state","invalid_state",409)
    before={**service.financial_snapshot(doc),"status":doc.status}
    data=service.payload(parse_json_body(request),False)
    for day in sorted({doc.planned_payment_date,data["planned_payment_date"]}):require_open_date(day)
    service.validate_source(data)
    for key,value in data.items():setattr(doc,key,value)
    doc.save(update_fields=list(data));service.audit(doc,request.user_entity,"updated",before=before,ip_address=request.META.get("REMOTE_ADDR",""))
    return result(doc,request)


@endpoint
def payment_request_action_view(request, request_id, action):
    if request.method!="POST":return JsonResponse({"error":"Method not allowed"},status=405)
    doc=service.locked(request_id);body=parse_json_body(request)
    if doc.created_by_id!=request.user_entity.id:raise service.PaymentRequestError("Only the creator may submit or cancel this request","permission_denied",403)
    if action=="submit":
        if body:raise service.PaymentRequestError("submit expects an empty object")
        service.submit(doc,request.user_entity,request.META.get("REMOTE_ADDR",""))
        return result(doc,request,202)
    if action!="cancel":raise service.PaymentRequestError("Unknown action")
    if set(body)!={"comment"}:raise service.PaymentRequestError("comment is required")
    comment=service.text(body["comment"],"comment",4000)
    if doc.status=="cancelled":return result(doc,request)
    if doc.status not in service.EDITABLE|{"pending_approval","approved"}:raise service.PaymentRequestError("Request cannot be cancelled","invalid_state",409)
    require_open_date(doc.planned_payment_date)
    before={**service.financial_snapshot(doc),"status":doc.status}
    if doc.approval_id:
        approval=ApprovalRequestModel.objects.select_for_update().get(id=doc.approval_id)
        if approval.status=="pending":
            approval.status="withdrawn";approval.save(update_fields=["status"])
            ApprovalActionModel.objects.create(approval=approval,actor_id=request.user_entity.id,action="withdraw",comment=comment)
    doc.status="cancelled";doc.save(update_fields=["status"]);service.audit(doc,request.user_entity,"cancelled",comment,before=before,ip_address=request.META.get("REMOTE_ADDR",""))
    service.notify(doc.created_by_id,doc)
    return result(doc,request)


def canonical_proof(upload):
    if upload is None or not 0<upload.size<=15*1024*1024:raise service.PaymentRequestError("A proof up to 15 MiB is required")
    if upload.content_type=="application/pdf":
        raw=upload.read(15*1024*1024+1)
        if len(raw)>15*1024*1024 or not raw.startswith(b"%PDF-") or b"%%EOF" not in raw[-1024:]:
            raise service.PaymentRequestError("Invalid PDF")
        try:name=get_valid_filename(Path(upload.name.replace('\\','/')).stem[:200])+".pdf"
        except SuspiciousFileOperation:name="proof.pdf"
        return raw,"application/pdf",name,".pdf"
    try:return canonical_photo(upload)
    except WmsError as exc:raise service.PaymentRequestError(str(exc),"invalid_input",400) from None


@endpoint
def payment_request_proofs_view(request, request_id):
    if request.method!="POST":return JsonResponse({"error":"Method not allowed"},status=405)
    saved=None;storage=PrivateMediaStorage()
    try:
        # The nested atomic exits (and rolls back metadata/audit) before file cleanup.
        with transaction.atomic():
            doc=service.locked(request_id)
            if doc.status not in service.EDITABLE|{"approved"}:raise service.PaymentRequestError("Proofs are immutable in this state","invalid_state",409)
            require_open_date(doc.planned_payment_date)
            if doc.proofs.filter(is_active=True).count()>=5:raise service.PaymentRequestError("At most five active proofs are supported")
            if set(request.FILES)!={"file"} or len(request.FILES.getlist("file"))!=1:raise service.PaymentRequestError("Exactly one file is required")
            encoded,content_type,name,extension=canonical_proof(request.FILES["file"])
            saved=storage.save(f"payment-proofs/{uuid4().hex}{extension}",ContentFile(encoded))
            proof=FinancePaymentProofModel.objects.create(payment_request=doc,file_path=saved,file_name=name,content_type=content_type,size=len(encoded),uploaded_by_id=request.user_entity.id)
            service.audit(doc,request.user_entity,"proof_uploaded",name,before={"proof_id":None},extra={"proof_id":proof.id,"file_name":name},ip_address=request.META.get("REMOTE_ADDR",""))
            response=JsonResponse(service.proof_data(proof),status=201)
        return response
    except Exception:
        if saved:storage.delete(saved)
        raise


@endpoint
def payment_request_proof_delete_view(request, request_id, proof_id):
    if request.method!="DELETE":return JsonResponse({"error":"Method not allowed"},status=405)
    doc=service.locked(request_id)
    if doc.status not in service.EDITABLE|{"approved"}:raise service.PaymentRequestError("Proofs are immutable","invalid_state",409)
    require_open_date(doc.planned_payment_date)
    proof=doc.proofs.filter(id=proof_id,is_active=True).first()
    if not proof:raise service.PaymentRequestError("Proof not found","not_found",404)
    proof.is_active=False;proof.save(update_fields=["is_active"]);service.audit(doc,request.user_entity,"proof_removed",proof.file_name,before={"proof_id":proof.id,"is_active":True},extra={"proof_id":proof.id,"is_active":False},ip_address=request.META.get("REMOTE_ADDR",""))
    return JsonResponse({"id":proof.id})


@login_required_domain
def payment_request_proof_download_view(request, request_id, proof_id):
    if request.method!="GET":return JsonResponse({"error":"Method not allowed"},status=405)
    doc=FinancePaymentRequestModel.objects.filter(id=request_id).first()
    if not doc or not service.can_download(request.user_entity,doc,proof_id):return JsonResponse({"error":"Permission denied","code":"permission_denied"},status=403)
    proof=doc.proofs.filter(id=proof_id,is_active=True).first();storage=PrivateMediaStorage()
    if not proof or not storage.exists(proof.file_path):return JsonResponse({"error":"Proof not found","code":"not_found"},status=404)
    response=FileResponse(storage.open(proof.file_path,"rb"),as_attachment=True,filename=proof.file_name,content_type=proof.content_type)
    response["Cache-Control"]="private, no-store";response["X-Content-Type-Options"]="nosniff"
    return response
