"""Supplier and SKU master-data API (Phase 2)."""
from decimal import Decimal, InvalidOperation
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from backend.infrastructure.persistence.models import SupplierModel, GoodsSKUModel, GoodsCategoryModel, SupplierQuoteModel, PurchaseOrderModel, PurchaseOrderItemModel, DepartmentModel, PurchaseReceiptModel, PurchaseReceiptItemModel, WarehouseModel, WarehouseLocationModel, StockInventoryModel, StockMovementModel, StockTransferModel, StockTransferItemModel, StockCountModel, StockCountItemModel, StockBatchModel, GoodsCertificateModel
from django.db import transaction
from backend.presentation.api.platform_views import _require
from backend.presentation.api.utils import parse_json_body
from backend.presentation.middlewares import login_required_domain


def _supplier(x):
    return {"id": x.id, "name_ru": x.name_ru, "name_zh": x.name_zh, "name_ky": x.name_ky, "country": x.country, "contact": x.contact, "phone": x.phone, "tax_no": x.tax_no, "currency": x.currency, "status": x.status}

def _sku(x):
    return {"id": x.id, "sku_code": x.sku_code, "barcode": x.barcode, "name_ru": x.name_ru, "name_zh": x.name_zh, "name_ky": x.name_ky, "category_id": x.category_id, "brand": x.brand, "origin": x.origin, "shelf_life_days": x.shelf_life_days, "status": x.status}

@csrf_exempt
@login_required_domain
def suppliers_view(request):
    denied = _require(request, "procurement.supplier.read" if request.method == "GET" else "procurement.supplier.manage")
    if denied: return denied
    if request.method == "GET":
        qs = SupplierModel.objects.all()
        if request.GET.get("status"): qs = qs.filter(status=request.GET["status"])
        if request.GET.get("q"): qs = qs.filter(name_ru__icontains=request.GET["q"])
        return JsonResponse({"items": [_supplier(x) for x in qs[:200]]})
    if request.method != "POST": return JsonResponse({"error": "Method not allowed"}, status=405)
    body = parse_json_body(request)
    if not str(body.get("name_ru", "")).strip(): return JsonResponse({"error": "name_ru is required"}, status=400)
    x = SupplierModel.objects.create(name_ru=body["name_ru"].strip(), name_zh=str(body.get("name_zh", "")), name_ky=str(body.get("name_ky", "")), country=str(body.get("country", "")), contact=str(body.get("contact", "")), phone=str(body.get("phone", "")), tax_no=str(body.get("tax_no", "")), currency=str(body.get("currency", "KGS")).upper(), created_by_id=request.user_entity.id)
    return JsonResponse(_supplier(x), status=201)

@csrf_exempt
@login_required_domain
def supplier_submit_view(request, supplier_id):
    denied = _require(request, "procurement.supplier.manage")
    if denied: return denied
    if request.method != "POST": return JsonResponse({"error": "Method not allowed"}, status=405)
    from backend.infrastructure.persistence.models import ApprovalRequestModel, OperationLogModel, UserModel
    with transaction.atomic():
        supplier=SupplierModel.objects.select_for_update().filter(id=supplier_id,status="draft").first()
        if not supplier:return JsonResponse({"error":"Draft supplier not found"},status=404)
        assignee = UserModel.objects.filter(role="general_director", is_active=True).order_by("id").first()
        if not assignee: return JsonResponse({"error": "No active director is available for approval"}, status=409)
        supplier.status="pending_approval";supplier.save(update_fields=["status","updated_at"])
        approval=ApprovalRequestModel.objects.create(business_type="supplier",business_id=supplier.id,applicant_id=request.user_entity.id,assigned_to=assignee,status="pending",snapshot=_supplier(supplier))
        OperationLogModel.objects.create(actor_id=request.user_entity.id, action="supplier.submitted", business_type="supplier", business_id=supplier.id, new_data={"status": supplier.status, "approval_id": approval.id})
    return JsonResponse({"id":approval.id,"status":approval.status},status=202)


@csrf_exempt
@login_required_domain
def skus_view(request):
    denied = _require(request, "procurement.sku.read" if request.method == "GET" else "procurement.sku.manage")
    if denied: return denied
    if request.method == "GET": return JsonResponse({"items": [_sku(x) for x in GoodsSKUModel.objects.select_related("category").all()[:200]]})
    if request.method != "POST": return JsonResponse({"error": "Method not allowed"}, status=405)
    body = parse_json_body(request)
    if not str(body.get("sku_code", "")).strip() or not str(body.get("name_ru", "")).strip(): return JsonResponse({"error": "sku_code and name_ru are required"}, status=400)
    category = GoodsCategoryModel.objects.filter(id=body.get("category_id")).first() if body.get("category_id") else None
    x = GoodsSKUModel.objects.create(sku_code=body["sku_code"].strip(), name_ru=body["name_ru"].strip(), name_zh=str(body.get("name_zh", "")), name_ky=str(body.get("name_ky", "")), barcode=str(body.get("barcode", "")), category=category, brand=str(body.get("brand", "")), origin=str(body.get("origin", "")), shelf_life_days=body.get("shelf_life_days") or None, created_by_id=request.user_entity.id)
    return JsonResponse(_sku(x), status=201)

@csrf_exempt
@login_required_domain
def sku_submit_view(request, sku_id):
    denied = _require(request, "procurement.sku.manage")
    if denied: return denied
    if request.method != "POST": return JsonResponse({"error": "Method not allowed"}, status=405)
    from backend.infrastructure.persistence.models import ApprovalRequestModel, OperationLogModel, UserModel
    with transaction.atomic():
        sku=GoodsSKUModel.objects.select_for_update().filter(id=sku_id,status="draft").first()
        if not sku:return JsonResponse({"error":"Draft SKU not found"},status=404)
        assignee = UserModel.objects.filter(role="general_director", is_active=True).order_by("id").first()
        if not assignee: return JsonResponse({"error": "No active director is available for approval"}, status=409)
        sku.status="pending_approval";sku.save(update_fields=["status","updated_at"])
        approval=ApprovalRequestModel.objects.create(business_type="sku",business_id=sku.id,applicant_id=request.user_entity.id,assigned_to=assignee,status="pending",snapshot=_sku(sku))
        OperationLogModel.objects.create(actor_id=request.user_entity.id, action="sku.submitted", business_type="sku", business_id=sku.id, new_data={"status": sku.status, "approval_id": approval.id})
    return JsonResponse({"id":approval.id,"status":approval.status},status=202)


@csrf_exempt
@login_required_domain
def sku_certificates_view(request, sku_id):
    denied = _require(request, "procurement.sku.read" if request.method == "GET" else "procurement.sku.manage")
    if denied: return denied
    sku = GoodsSKUModel.objects.filter(id=sku_id).first()
    if not sku: return JsonResponse({"error": "SKU not found"}, status=404)
    if request.method == "GET":
        return JsonResponse({"items": [{"id": x.id, "number": x.number, "file_path": x.file_path, "expires_at": x.expires_at.isoformat(), "created_at": x.created_at.isoformat()} for x in GoodsCertificateModel.objects.filter(sku=sku).order_by("expires_at")]})
    if request.method != "POST": return JsonResponse({"error": "Method not allowed"}, status=405)
    body = parse_json_body(request); number = str(body.get("number", "")).strip(); file_path = str(body.get("file_path", "")).strip()
    try:
        from datetime import date
        expires_at = date.fromisoformat(body["expires_at"])
    except (KeyError, ValueError):
        return JsonResponse({"error": "valid number, file_path and expires_at are required"}, status=400)
    if not number or not file_path: return JsonResponse({"error": "valid number, file_path and expires_at are required"}, status=400)
    try:
        certificate = GoodsCertificateModel.objects.create(sku=sku, number=number, file_path=file_path, expires_at=expires_at, created_by_id=request.user_entity.id)
    except Exception:
        return JsonResponse({"error": "Certificate number already exists for this SKU"}, status=409)
    return JsonResponse({"id": certificate.id, "number": certificate.number, "expires_at": certificate.expires_at.isoformat()}, status=201)

@csrf_exempt
@login_required_domain
def supplier_quotes_view(request):
    denied = _require(request, "procurement.quote.manage")
    if denied: return denied
    if request.method != "POST": return JsonResponse({"error": "Method not allowed"}, status=405)
    body = parse_json_body(request)
    try: price = Decimal(str(body["price"]))
    except (KeyError, InvalidOperation): return JsonResponse({"error": "valid price is required"}, status=400)
    supplier = SupplierModel.objects.filter(id=body.get("supplier_id"), status="active").first(); sku = GoodsSKUModel.objects.filter(id=body.get("sku_id"), status="active").first()
    if not supplier or not sku: return JsonResponse({"error": "Only active supplier and SKU may have a quote"}, status=400)
    currency = str(body.get("currency", "KGS")).upper()
    try:
        moq, delivery_days = int(body.get("moq", 1)), int(body.get("delivery_days", 0))
        if moq < 1 or delivery_days < 0: raise ValueError
    except (TypeError, ValueError): return JsonResponse({"error": "moq and delivery_days must be non-negative valid values"}, status=400)
    from backend.infrastructure.persistence.models import ApprovalRequestModel, UserModel
    with transaction.atomic():
        quote = SupplierQuoteModel.objects.select_for_update().filter(supplier=supplier, sku=sku, currency=currency).first()
        if quote and quote.price != price:
            assignee = UserModel.objects.filter(role="general_director", is_active=True).order_by("id").first()
            if not assignee: return JsonResponse({"error": "No active director is available for approval"}, status=409)
            approval = ApprovalRequestModel.objects.create(business_type="supplier_quote_price", business_id=quote.id, applicant_id=request.user_entity.id, assigned_to=assignee, status="pending", snapshot={"quote_id": quote.id, "supplier_id": supplier.id, "sku_id": sku.id, "currency": currency, "old_price": str(quote.price), "new_price": str(price), "moq": moq, "delivery_days": delivery_days})
            return JsonResponse({"id": approval.id, "status": approval.status, "quote_id": quote.id}, status=202)
        if quote:
            quote.moq, quote.delivery_days = moq, delivery_days; quote.save(update_fields=["moq", "delivery_days"])
        else:
            quote = SupplierQuoteModel.objects.create(supplier=supplier, sku=sku, currency=currency, price=price, moq=moq, delivery_days=delivery_days)
    return JsonResponse({"id": quote.id, "supplier_id": quote.supplier_id, "sku_id": quote.sku_id, "price": str(quote.price), "currency": quote.currency}, status=201)


def _po(order):
    return {"id": order.id, "po_no": order.po_no, "supplier_id": order.supplier_id, "department_id": order.department_id, "order_date": order.order_date.isoformat(), "expected_delivery_date": order.expected_delivery_date.isoformat() if order.expected_delivery_date else None, "currency": order.currency, "status": order.status, "items": [{"sku_id": i.sku_id, "ordered_qty": i.ordered_qty, "received_qty": i.received_qty, "unit_price": str(i.unit_price)} for i in order.items.all()]}

@csrf_exempt
@login_required_domain
def purchase_orders_view(request):
    denied = _require(request, "procurement.order.read" if request.method == "GET" else "procurement.order.manage")
    if denied: return denied
    if request.method == "GET": return JsonResponse({"items": [_po(x) for x in PurchaseOrderModel.objects.select_related("supplier").prefetch_related("items").all()[:200]]})
    if request.method != "POST": return JsonResponse({"error": "Method not allowed"}, status=405)
    body = parse_json_body(request); rows = body.get("items")
    if not isinstance(rows, list) or not rows: return JsonResponse({"error": "items are required"}, status=400)
    supplier = SupplierModel.objects.filter(id=body.get("supplier_id"), status="active").first()
    if not supplier: return JsonResponse({"error": "An active supplier is required"}, status=400)
    try:
        from datetime import date
        order_date = date.fromisoformat(body.get("order_date", ""))
    except ValueError: return JsonResponse({"error": "valid order_date is required"}, status=400)
    po_no = str(body.get("po_no", "")).strip()
    if not po_no or PurchaseOrderModel.objects.filter(po_no=po_no).exists(): return JsonResponse({"error": "unique po_no is required"}, status=400)
    department = DepartmentModel.objects.filter(id=body.get("department_id")).first() if body.get("department_id") else None
    order = PurchaseOrderModel.objects.create(po_no=po_no, supplier=supplier, department=department, order_date=order_date, currency=str(body.get("currency", supplier.currency)).upper(), created_by_id=request.user_entity.id)
    try:
        for row in rows:
            sku = GoodsSKUModel.objects.get(id=row["sku_id"], status="active")
            qty = int(row["ordered_qty"]); price = Decimal(str(row["unit_price"]))
            if qty <= 0 or price < 0: raise ValueError
            PurchaseOrderItemModel.objects.create(purchase_order=order, sku=sku, ordered_qty=qty, unit_price=price)
    except (GoodsSKUModel.DoesNotExist, KeyError, ValueError, InvalidOperation):
        order.delete(); return JsonResponse({"error": "Each item requires an active SKU, positive quantity and price"}, status=400)
    return JsonResponse(_po(PurchaseOrderModel.objects.prefetch_related("items").get(id=order.id)), status=201)


@csrf_exempt
@login_required_domain
def purchase_order_submit_view(request, order_id):
    denied = _require(request, "procurement.order.manage")
    if denied: return denied
    if request.method != "POST": return JsonResponse({"error": "Method not allowed"}, status=405)
    from backend.infrastructure.persistence.models import ApprovalRequestModel, UserModel, OperationLogModel
    with transaction.atomic():
        order = PurchaseOrderModel.objects.select_for_update().select_related("supplier").prefetch_related("items").filter(id=order_id, status="draft").first()
        if not order: return JsonResponse({"error": "Draft purchase order not found"}, status=404)
        if not order.items.exists(): return JsonResponse({"error": "Purchase order needs at least one line"}, status=400)
        assignee = UserModel.objects.filter(role="general_director", is_active=True).order_by("id").first()
        if not assignee: return JsonResponse({"error": "No active director is available for approval"}, status=409)
        order.status = "pending_approval"; order.save(update_fields=["status"])
        approval = ApprovalRequestModel.objects.create(business_type="purchase_order", business_id=order.id, applicant_id=request.user_entity.id, assigned_to=assignee, status="pending", snapshot=_po(order))
        OperationLogModel.objects.create(actor_id=request.user_entity.id, action="purchase_order.submitted", business_type="purchase_order", business_id=order.id, new_data={"status": order.status, "approval_id": approval.id})
    return JsonResponse({"id": approval.id, "status": approval.status, "purchase_order_id": order.id}, status=202)


# Compatibility imports: all WMS routes use the scoped implementation.
from backend.presentation.api.warehouse_views import (
    purchase_receipts_view, stock_transfers_view, stock_counts_view,
    post_purchase_receipt_view, warehouse_inventory_view, expiry_alerts_view,
    approve_stock_count_view, post_stock_transfer_view,
)
