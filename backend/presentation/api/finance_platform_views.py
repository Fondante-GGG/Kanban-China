from backend.application.finance_periods import finance_transaction, require_open_date
from decimal import Decimal, InvalidOperation
from django.db import transaction, IntegrityError
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from backend.infrastructure.persistence.models import FinanceAccountModel, FinancePayableModel, FinancePaymentModel, FinancePeriodModel, SupplierStatementModel, PurchaseOrderModel
from backend.presentation.api.platform_views import _require
from backend.presentation.api.utils import parse_json_body
from backend.presentation.middlewares import login_required_domain


def _payable(x):
    return {"id": x.id, "supplier_id": x.supplier_id, "purchase_order_id": x.purchase_order_id, "amount": str(x.amount), "outstanding_amount": str(x.outstanding_amount), "currency": x.currency, "due_date": x.due_date.isoformat() if x.due_date else None, "status": x.status}


def _statement(x):
    return {"id": x.id, "statement_no": x.statement_no, "supplier_id": x.supplier_id, "purchase_order_id": x.purchase_order_id, "period_start": x.period_start.isoformat(), "period_end": x.period_end.isoformat(), "total_amount": str(x.total_amount), "currency": x.currency, "status": x.status}

@csrf_exempt
@login_required_domain
def finance_accounts_view(request):
    denied = _require(request, "finance.account.manage")
    if denied: return denied
    if request.method == "GET": return JsonResponse({"items": [{"id": x.id, "name": x.name, "bank_name": x.bank_name, "currency": x.currency, "balance": str(x.balance), "is_active": x.is_active} for x in FinanceAccountModel.objects.all()]})
    if request.method != "POST": return JsonResponse({"error": "Method not allowed"}, status=405)
    body = parse_json_body(request)
    if not body.get("name") or not body.get("currency"): return JsonResponse({"error": "name and currency are required"}, status=400)
    x = FinanceAccountModel.objects.create(name=str(body["name"]).strip(), bank_name=str(body.get("bank_name", "")), currency=str(body["currency"]).upper())
    return JsonResponse({"id": x.id, "name": x.name, "currency": x.currency}, status=201)

@login_required_domain
def finance_payables_view(request):
    denied = _require(request, "finance.payable.read")
    if denied: return denied
    if request.method != "GET": return JsonResponse({"error": "Method not allowed"}, status=405)
    return JsonResponse({"items": [_payable(x) for x in FinancePayableModel.objects.select_related("supplier", "purchase_order").all()[:200]]})


@csrf_exempt
@login_required_domain
@finance_transaction
def supplier_statements_view(request):
    """Supplier reconciliation documents become payables only after explicit confirmation."""
    denied = _require(request, "finance.payable.read" if request.method == "GET" else "finance.payable.manage")
    if denied: return denied
    if request.method == "GET":
        qs = SupplierStatementModel.objects.select_related("supplier", "purchase_order").all()
        if request.GET.get("supplier_id"): qs = qs.filter(supplier_id=request.GET["supplier_id"])
        if request.GET.get("status"): qs = qs.filter(status=request.GET["status"])
        return JsonResponse({"items": [_statement(x) for x in qs[:200]]})
    if request.method != "POST": return JsonResponse({"error": "Method not allowed"}, status=405)
    body = parse_json_body(request)
    number = str(body.get("statement_no", "")).strip()
    if not number or SupplierStatementModel.objects.filter(statement_no=number).exists(): return JsonResponse({"error": "unique statement_no is required"}, status=400)
    try:
        from datetime import date
        period_start, period_end = date.fromisoformat(body["period_start"]), date.fromisoformat(body["period_end"])
        total = Decimal(str(body["total_amount"]))
    except (KeyError, ValueError, InvalidOperation):
        return JsonResponse({"error": "valid period_start, period_end and total_amount are required"}, status=400)
    order = PurchaseOrderModel.objects.select_related("supplier").filter(id=body.get("purchase_order_id")).first()
    if not order or order.supplier_id != body.get("supplier_id") or period_end < period_start or total < 0:
        return JsonResponse({"error": "Supplier, purchase order, date range or total is invalid"}, status=400)
    if str(body.get("currency", order.currency)).upper() != order.currency:
        return JsonResponse({"error": "Statement currency must match purchase order currency"}, status=400)
    require_open_date(period_end)
    try:
        statement = SupplierStatementModel.objects.create(statement_no=number, supplier=order.supplier, purchase_order=order, period_start=period_start, period_end=period_end, total_amount=total, currency=order.currency, created_by_id=request.user_entity.id)
    except IntegrityError:
        return JsonResponse({"error": "A statement for this purchase-order period already exists"}, status=409)
    return JsonResponse(_statement(statement), status=201)

@csrf_exempt
@login_required_domain
@finance_transaction
def finance_payment_view(request, payable_id):
    denied = _require(request, "finance.payment.manage")
    if denied: return denied
    if request.method != "POST": return JsonResponse({"error": "Method not allowed"}, status=405)
    from backend.application.payment_requests import execute_payment, PaymentRequestError
    try:
        payment, created = execute_payment(request.user_entity, payable_id, parse_json_body(request),request.META.get("REMOTE_ADDR",""))
    except PaymentRequestError as exc:
        return JsonResponse({"error":exc.message,"code":exc.code},status=exc.status)
    return JsonResponse({"id":payment.id,"payment_request_id":payment.payment_request_id,"payable":_payable(payment.payable)},status=201 if created else 200)

@csrf_exempt
@login_required_domain
@finance_transaction
def confirm_supplier_statement_view(request, statement_id):
    denied = _require(request, "finance.payable.manage")
    if denied: return denied
    if request.method != "POST": return JsonResponse({"error": "Method not allowed"}, status=405)
    with transaction.atomic():
        statement = SupplierStatementModel.objects.select_for_update().select_related("purchase_order", "supplier").filter(id=statement_id).first()
        if not statement: return JsonResponse({"error": "Statement not found"}, status=404)
        if statement.status != "draft": return JsonResponse({"error": "Only draft statement may be confirmed"}, status=409)
        if statement.purchase_order.status not in ("partially_received", "received", "closed"): return JsonResponse({"error": "Confirmed receiving is required before reconciliation"}, status=400)
        require_open_date(statement.period_end)
        payable, created = FinancePayableModel.objects.get_or_create(source_type="supplier_statement", source_id=statement.id, defaults={"supplier": statement.supplier, "purchase_order": statement.purchase_order, "amount": statement.total_amount, "outstanding_amount": statement.total_amount, "currency": statement.currency})
        if not created: return JsonResponse({"error": "Payable already exists"}, status=409)
        from django.utils import timezone
        statement.status = "confirmed"; statement.confirmed_by_id = request.user_entity.id; statement.confirmed_at = timezone.now(); statement.save(update_fields=["status", "confirmed_by", "confirmed_at"])
    return JsonResponse({"statement_id": statement.id, "payable": _payable(payable)}, status=201)
