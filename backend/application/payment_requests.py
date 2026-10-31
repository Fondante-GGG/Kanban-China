"""Payment authorization invariants shared by finance and the approval inbox.

Call mutation functions in an atomic block; every writer locks the request before
its approval, payable, account and posting month, in that order.
"""
import re
from datetime import date
from decimal import Decimal
from uuid import UUID
from django.db import transaction
from django.utils import timezone
from backend.application.finance_periods import require_open_date
from backend.infrastructure.persistence.models import (
    ApprovalRequestModel, ApprovalActionModel, ApprovalFlowModel,
    FinancePaymentRequestModel, FinancePayableModel, FinanceAccountModel,
    FinancePaymentModel, FinancePaymentProofModel, UserModel, OperationLogModel,
    NotificationModel,
)
from backend.infrastructure.persistence.storage import PrivateMediaStorage

BUSINESS_TYPE = "finance_payment_request"
EDITABLE = {"draft", "returned"}


class PaymentRequestError(Exception):
    def __init__(self, message, code="invalid_input", status=400):
        self.message, self.code, self.status = message, code, status


def permissions(user):
    from backend.presentation.api.platform_views import _permissions
    return _permissions(user.id)


def can_read(user):
    return bool({"finance.payable.read", "finance.payment.manage"} & permissions(user))


def can_manage(user):
    return "finance.payment.manage" in permissions(user)


def integer(value, name):
    if type(value) is not int or not 0 < value <= 9223372036854775807:
        raise PaymentRequestError(f"A positive integer {name} is required")
    return value


def text(value, name, maximum):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum or "\x00" in value:
        raise PaymentRequestError(f"A nonempty {name} of at most {maximum} characters is required")
    return value.strip()


def money(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{1,14}(?:\.[0-9]{1,2})?", value) or Decimal(value) <= 0:
        raise PaymentRequestError("A positive decimal string with at most two decimal places is required")
    return Decimal(value)


def iso_date(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise PaymentRequestError("A YYYY-MM-DD date is required")
    try: return date.fromisoformat(value)
    except ValueError: raise PaymentRequestError("Invalid date") from None


def payload(body, creating=True):
    required = {"payable_id", "account_id", "amount", "currency", "planned_payment_date", "purpose"}
    if creating: required |= {"request_id", "request_no"}
    if set(body) != required:
        raise PaymentRequestError("Unexpected or missing payment request fields")
    result = {"payable_id": integer(body["payable_id"], "payable_id"),
        "account_id": integer(body["account_id"], "account_id"), "amount": money(body["amount"]),
        "planned_payment_date": iso_date(body["planned_payment_date"]),
        "purpose": text(body["purpose"], "purpose", 4000)}
    if not isinstance(body["currency"], str) or not re.fullmatch(r"[A-Z]{3}", body["currency"]):
        raise PaymentRequestError("An uppercase currency code is required")
    result["currency"] = body["currency"]
    if creating:
        try:
            if not isinstance(body["request_id"], str): raise ValueError
            result["request_id"] = UUID(body["request_id"])
        except ValueError: raise PaymentRequestError("A UUID request_id is required") from None
        result["request_no"] = text(body["request_no"], "request_no", 64)
    return result


def canonical(data):
    return {k: format(v, ".2f") if isinstance(v, Decimal) else str(v) if isinstance(v, (date, UUID)) else v for k,v in data.items()}


def validate_source(data):
    payable = FinancePayableModel.objects.filter(id=data["payable_id"], status__in=("open", "partially_paid"), outstanding_amount__gt=0).first()
    account = FinanceAccountModel.objects.filter(id=data["account_id"], is_active=True).first()
    if not payable or not account:
        raise PaymentRequestError("An open debt and active account are required", "request_conflict", 409)
    if payable.currency != data["currency"] or account.currency != data["currency"]:
        raise PaymentRequestError("Debt, account and request currency must match", "currency_mismatch", 409)
    if data["amount"] > payable.outstanding_amount:
        raise PaymentRequestError("Amount exceeds current debt", "insufficient_outstanding", 409)
    return payable, account


def locked(request_id):
    doc = FinancePaymentRequestModel.objects.select_for_update().filter(id=request_id).first()
    if not doc: raise PaymentRequestError("Payment request not found", "not_found", 404)
    return doc


def financial_snapshot(doc):
    return {"payment_request_id": doc.id, "request_no": doc.request_no,
        "payable_id": doc.payable_id, "supplier_id": doc.payable.supplier_id,
        "supplier_name": doc.payable.supplier.name_ru, "account_id": doc.account_id,
        "account_name": doc.account.name, "amount": format(doc.amount, ".2f"),
        "currency": doc.currency, "planned_payment_date": doc.planned_payment_date.isoformat(), "purpose": doc.purpose}


def proof_data(proof):
    return {"id": proof.id, "file_name": proof.file_name, "content_type": proof.content_type,
        "size": proof.size, "download_url": f"/api/finance/payment-requests/{proof.payment_request_id}/proofs/{proof.id}/download"}


def audit(doc, actor, action, comment="", before=None, extra=None, ip_address=""):
    OperationLogModel.objects.create(actor_id=actor.id, action="finance.payment_request_"+action,
        business_type=BUSINESS_TYPE, business_id=doc.id,
        old_data=before or {},
        new_data={**financial_snapshot(doc), "status": doc.status, "comment": comment, **(extra or {})},
        ip_address=ip_address)


def notify(user_id, doc):
    user = UserModel.objects.filter(id=user_id, is_active=True).first()
    if not user: return
    labels = {"ru": ("Заявка на оплату", "Статус заявки изменён"),
        "ky": ("Төлөм өтүнмөсү", "Өтүнмөнүн абалы өзгөрдү"),
        "zh-Hans": ("付款申请", "申请状态已更新"), "zh-Hant": ("付款申請", "申請狀態已更新")}
    title, message = labels.get(user.interface_language, labels["ru"])
    NotificationModel.objects.create(user=user, title=title, message=f"{message}: {doc.request_no}", entity_type=BUSINESS_TYPE, entity_id=doc.id)


def resolve_route(doc):
    flow = ApprovalFlowModel.objects.filter(business_type=BUSINESS_TYPE, is_active=True).first()
    if not flow or not flow.nodes.exists():
        raise PaymentRequestError("Configure an active payment approval route", "flow_unconfigured", 409)
    from backend.presentation.api.platform_views import _resolve_node_assignee
    # Reuse the configured sequential resolver, excluding the applicant for role
    # nodes rather than selecting an unsafe self-approver and falling back.
    route = []
    for node in flow.nodes.select_related("user", "role").order_by("order"):
        if node.approver_type == "role":
            candidates = UserModel.objects.filter(system_role_links__role_id=node.role_id, is_active=True).exclude(id=doc.created_by_id).order_by("id")
        elif node.approver_type == "department_leader":
            candidates = UserModel.objects.filter(department_id=doc.created_by.department_id, role="manager", is_active=True).exclude(id=doc.created_by_id).order_by("id")
        else:
            candidates = [node.user] if node.user_id else []
        actor = next((u for u in candidates if u and u.is_active and u.id != doc.created_by_id and {"approval.read", "approval.act"}.issubset(permissions(u))), None)
        if not actor or (node.role_id and not node.role.is_active):
            raise PaymentRequestError("A configured node has no independent active approver", "approver_unavailable", 409)
        route.append({"order": node.order, "assignee_id": actor.id, "assignee_name": actor.full_name})
    return flow, route


def allowed_actions(user, doc):
    return actions_for_manage(doc,user.id) if can_manage(user) else []


def actions_for_manage(doc,user_id=None):
    actions = []
    if doc.status in EDITABLE and doc.created_by_id==user_id: actions += ["edit", "submit"]
    if doc.status in EDITABLE | {"pending_approval", "approved"} and doc.created_by_id==user_id: actions += ["cancel"]
    if doc.status in EDITABLE | {"approved"}: actions += ["upload_proof", "delete_proof"]
    if doc.status == "approved": actions += ["pay"]
    return actions


def serialize(doc, user, managing=None):
    approval = doc.approval
    list_mode = getattr(doc,"_list_mode",False)
    logs = [] if list_mode else OperationLogModel.objects.filter(business_type=BUSINESS_TYPE,business_id=doc.id).select_related("actor").order_by("-id")[:100]
    payment = getattr(doc,"_payment_cached",None) if list_mode else FinancePaymentModel.objects.filter(payment_request_id=doc.id).first()
    proofs = [] if list_mode else [proof_data(p) for p in doc.proofs.filter(is_active=True).order_by("id")]
    return {"id": doc.id, "request_id": str(doc.request_id), **financial_snapshot(doc),
        "payable_outstanding_amount": format(doc.payable.outstanding_amount, ".2f"),
        "status": doc.status, "created_by_id": doc.created_by_id, "created_by_name": doc.created_by.full_name,
        "created_at": doc.created_at.isoformat(), "approval_id": doc.approval_id,
        "approval_status": approval.status if approval else None, "assigned_to_id": approval.assigned_to_id if approval else None,
        "assigned_to_name": approval.assigned_to.full_name if approval and approval.assigned_to_id else None,
        "current_node": approval.current_node if approval else None, "payment_id": payment.id if payment else None,
        "allowed_actions": allowed_actions(user,doc) if managing is None else actions_for_manage(doc,user.id) if managing else [], "proofs": proofs,
        "history_count": getattr(doc,"_history_count",0) if list_mode else OperationLogModel.objects.filter(business_type=BUSINESS_TYPE,business_id=doc.id).count(),
        "history": [{"action": l.action, "actor_id": l.actor_id, "actor_name": l.actor.full_name,
            "comment": l.new_data.get("comment", ""), "created_at": l.created_at.isoformat()} for l in logs]}


def submit(doc, actor, ip_address=""):
    if doc.status not in EDITABLE: raise PaymentRequestError("Only editable requests can be submitted", "invalid_state", 409)
    require_open_date(doc.planned_payment_date)
    validate_source({"payable_id": doc.payable_id, "account_id": doc.account_id, "amount": doc.amount, "currency": doc.currency})
    before={**financial_snapshot(doc),"status":doc.status}
    flow, route = resolve_route(doc)
    snapshot = {**financial_snapshot(doc), "route": route, "proofs": [proof_data(p) for p in doc.proofs.filter(is_active=True)]}
    approval = ApprovalRequestModel.objects.create(business_type=BUSINESS_TYPE, business_id=doc.id,
        applicant_id=doc.created_by_id, assigned_to_id=route[0]["assignee_id"], flow=flow,
        current_node=route[0]["order"], snapshot=snapshot)
    ApprovalActionModel.objects.create(approval=approval, actor_id=actor.id, action="submit")
    doc.approval = approval; doc.status = "pending_approval"; doc.save(update_fields=["approval", "status"])
    audit(doc, actor, "submit",before=before,ip_address=ip_address); notify(approval.assigned_to_id, doc)


def approval_actions(approval, user):
    if (approval.status != "pending" or approval.applicant_id == user.id or approval.assigned_to_id != user.id
            or not user.is_active or not {"approval.read", "approval.act"}.issubset(permissions(user))): return []
    current = FinancePaymentRequestModel.objects.filter(id=approval.business_id, approval_id=approval.id, status="pending_approval").exists()
    return ["approve", "reject", "return"] if current else []


def decide(approval_id, actor, action, comment, ip_address=""):
    # First read identifies the request; lock request before approval consistently
    # with edit/cancel/payment. No approval lock may be held by the caller.
    found = ApprovalRequestModel.objects.filter(id=approval_id, business_type=BUSINESS_TYPE).first()
    if not found: raise PaymentRequestError("Approval not found", "not_found", 404)
    doc = locked(found.business_id)
    approval = ApprovalRequestModel.objects.select_for_update().get(id=approval_id)
    if action not in approval_actions(approval, actor):
        raise PaymentRequestError("Approval is not actionable by this actor", "permission_denied", 403)
    require_open_date(doc.planned_payment_date)
    if action not in ("approve", "reject", "return"):
        raise PaymentRequestError("Invalid approval action")
    if action != "approve": comment = text(comment, "comment", 4000)
    elif not isinstance(comment, str) or len(comment) > 4000: raise PaymentRequestError("Invalid comment")
    if financial_snapshot(doc) != {k: approval.snapshot.get(k) for k in financial_snapshot(doc)}:
        raise PaymentRequestError("Financial snapshot changed", "request_conflict", 409)
    before={**financial_snapshot(doc),"status":doc.status,"approval_status":approval.status,"assigned_to_id":approval.assigned_to_id,"current_node":approval.current_node}
    route = approval.snapshot["route"]
    following = next((node for node in route if node["order"] > approval.current_node), None)
    ApprovalActionModel.objects.create(approval=approval, actor_id=actor.id, action=action, comment=comment)
    if action == "approve" and following:
        assignee = UserModel.objects.filter(id=following["assignee_id"], is_active=True).first()
        if not assignee or assignee.id == doc.created_by_id or not {"approval.read", "approval.act"}.issubset(permissions(assignee)):
            raise PaymentRequestError("Next approver is unavailable", "approver_unavailable", 409)
        approval.current_node = following["order"]; approval.assigned_to = assignee
        approval.save(update_fields=["current_node", "assigned_to"])
        notify(assignee.id, doc)
    else:
        approval.status = "approved" if action == "approve" else "returned" if action == "return" else "rejected"
        approval.decided_by_id = actor.id; approval.decided_at = timezone.now(); approval.save()
        doc.status = approval.status; doc.save(update_fields=["status"]); notify(doc.created_by_id, doc)
    audit(doc, actor, action, comment,before=before,extra={"approval_status":approval.status,"assigned_to_id":approval.assigned_to_id,"current_node":approval.current_node},ip_address=ip_address)
    return {"id": approval.id, "status": approval.status, "assigned_to_id": approval.assigned_to_id, "current_node": approval.current_node}


def can_download(user, doc, proof_id):
    if can_read(user): return True
    if not {"approval.read", "approval.act"}.issubset(permissions(user)): return False
    return any(any(p.get("id") == proof_id for p in a.snapshot.get("proofs", [])) for a in ApprovalRequestModel.objects.filter(business_type=BUSINESS_TYPE, business_id=doc.id, assigned_to_id=user.id))


def execute_payment(actor, payable_id, body, ip_address=""):
    if "payment_request_id" not in body:
        raise PaymentRequestError("An approved payment request is required", "approval_required", 409)
    fields = {"payment_request_id", "account_id", "amount", "payment_date", "transaction_no", "proof_id"}
    if set(body) != fields: raise PaymentRequestError("Unexpected or missing payment fields")
    doc = locked(integer(body["payment_request_id"], "payment_request_id"))
    account_id = integer(body["account_id"], "account_id"); amount = money(body["amount"])
    paid_on = iso_date(body["payment_date"]); number = text(body["transaction_no"], "transaction_no", 128)
    proof_id = integer(body["proof_id"], "proof_id")
    prior = FinancePaymentModel.objects.filter(payment_request=doc).first()
    signature = (payable_id, account_id, amount, paid_on, number, proof_id)
    if prior:
        if signature != (prior.payable_id, prior.account_id, prior.amount, prior.payment_date, prior.transaction_no, prior.proof_id):
            raise PaymentRequestError("Request was paid with different data", "idempotency_conflict", 409)
        return prior, False
    if doc.status != "approved" or not doc.approval_id or doc.approval.status != "approved":
        raise PaymentRequestError("An approved payment request is required", "approval_required", 409)
    snapshot = doc.approval.snapshot
    if (financial_snapshot(doc) != {k:snapshot.get(k) for k in financial_snapshot(doc)}
            or signature[:4] != (doc.payable_id, doc.account_id, doc.amount, doc.planned_payment_date)):
        raise PaymentRequestError("Payment must match approved request", "request_conflict", 409)
    payable = FinancePayableModel.objects.select_for_update().get(id=doc.payable_id)
    account = FinanceAccountModel.objects.select_for_update().get(id=doc.account_id)
    if not account.is_active or payable.status not in ("open", "partially_paid"):
        raise PaymentRequestError("Debt or account is no longer available", "request_conflict", 409)
    if payable.currency != doc.currency or account.currency != doc.currency:
        raise PaymentRequestError("Currency mismatch", "currency_mismatch", 409)
    if amount > payable.outstanding_amount:
        raise PaymentRequestError("Amount exceeds current debt", "insufficient_outstanding", 409)
    if amount > account.balance:
        raise PaymentRequestError("Insufficient account balance", "insufficient_balance", 409)
    proof = doc.proofs.filter(id=proof_id, is_active=True).first()
    if not proof or not PrivateMediaStorage().exists(proof.file_path):
        raise PaymentRequestError("An existing request payment proof is required", "proof_required", 409)
    require_open_date(paid_on)
    if FinancePaymentModel.objects.filter(account=account, transaction_no=number).exists():
        raise PaymentRequestError("Transaction number already exists", "transaction_conflict", 409)
    before={**financial_snapshot(doc),"status":doc.status,"debt_outstanding_amount":format(payable.outstanding_amount,".2f"),"account_balance":format(account.balance,".2f")}
    payment = FinancePaymentModel.objects.create(payment_request=doc, proof=proof, payable=payable, account=account,
        amount=amount, payment_date=paid_on, transaction_no=number, created_by_id=actor.id)
    account.balance -= amount; account.save(update_fields=["balance"])
    payable.outstanding_amount -= amount
    payable.status = "partially_paid" if payable.outstanding_amount else "settled_by_adjustment" if payable.return_corrections.exists() else "paid"
    payable.save(update_fields=["outstanding_amount", "status"])
    doc.status = "paid"; doc.save(update_fields=["status"])
    audit(doc, actor, "paid",before=before,extra={"payment_id":payment.id,"debt_outstanding_amount":format(payable.outstanding_amount,".2f"),"account_balance":format(account.balance,".2f")},ip_address=ip_address); notify(doc.created_by_id, doc)
    return payment, True
