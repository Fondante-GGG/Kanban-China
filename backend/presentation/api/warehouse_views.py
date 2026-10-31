"""Scoped online WMS API. Inventory changes only through audited documents.

Warehouse row locks serialize all API writers, including new inventory rows for
nullable locations (the legacy unique constraint alone does not protect NULL).
"""
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from functools import wraps

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from backend.domain.exceptions import ValidationException
from backend.infrastructure.persistence.models import (
    WarehouseModel, WarehouseLocationModel, GoodsSKUModel, PurchaseOrderModel,
    PurchaseOrderItemModel, PurchaseReceiptModel, PurchaseReceiptItemModel,
    StockInventoryModel, StockMovementModel, StockBatchModel, StockCountModel,
    StockCountItemModel, StockTransferModel, StockTransferItemModel,
    GoodsCertificateModel, OperationLogModel, StockWriteoffModel,
)
from backend.presentation.api.platform_views import _permissions
from backend.presentation.api.utils import parse_json_body
from backend.presentation.middlewares import login_required_domain


class WmsError(Exception):
    def __init__(self, message, code="validation_error", status=400):
        self.message, self.code, self.status = message, code, status


def endpoint(permission):
    def decorate(fn):
        @csrf_exempt
        @login_required_domain
        @wraps(fn)
        def wrapped(request, *args, **kwargs):
            request.wms_permissions = _permissions(request.user_entity.id)
            required = permission(request) if callable(permission) else permission
            if required and required not in request.wms_permissions:
                return JsonResponse({"error": "Permission denied", "code": "permission_denied"}, status=403)
            try:
                return fn(request, *args, **kwargs)
            except WmsError as exc:
                return JsonResponse({"error": exc.message, "code": exc.code}, status=exc.status)
            except (ValidationException, ValueError, TypeError, KeyError, InvalidOperation):
                return JsonResponse({"error": "Invalid warehouse request", "code": "validation_error"}, status=400)
            except IntegrityError:
                return JsonResponse({"error": "Document number or inventory conflicts with an existing record", "code": "conflict"}, status=409)
        return wrapped
    return decorate


def method(request, *allowed):
    if request.method not in allowed:
        raise WmsError("Method not allowed", "method_not_allowed", 405)


def integer(value, low=1, high=2147483647):
    if isinstance(value, bool) or not str(value).isdigit():
        raise WmsError("A valid integer is required")
    number = int(value)
    if not low <= number <= high:
        raise WmsError("Integer outside permitted range")
    return number


def decimal(value, places=3, maximum="99999999999.999"):
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise WmsError("A valid decimal is required")
    number = Decimal(str(value))
    if not number.is_finite() or not 0 <= number <= Decimal(maximum) or number != number.quantize(Decimal(1).scaleb(-places)):
        raise WmsError("Decimal outside permitted range or precision")
    return number


def text(value, maximum, required=False):
    if not isinstance(value, str) or len(value) > maximum or (required and not value.strip()):
        raise WmsError("Invalid text field")
    return value.strip()


def rows(body):
    result = body.get("items")
    if not isinstance(result, list) or not 1 <= len(result) <= 100 or any(not isinstance(row, dict) for row in result):
        raise WmsError("1 to 100 document lines are required")
    return result


def scope(request):
    qs = WarehouseModel.objects.all()
    return qs if request.user_entity.role == "general_director" else qs.filter(manager_id=request.user_entity.id)


def warehouse(request, value):
    found = scope(request).filter(id=integer(value)).first()
    if not found:
        raise WmsError("Warehouse not available", "permission_denied", 403)
    return found


def filtered(request, qs, field="warehouse_id"):
    ids = scope(request).values("id")
    qs = qs.filter(**{field + "__in": ids})
    if "warehouse_id" in request.GET:
        qs = qs.filter(**{field: warehouse(request, request.GET["warehouse_id"]).id})
    return qs


def lock_warehouses(*ids):
    # Stable ordering also prevents cross-transfer lock inversions.
    return list(WarehouseModel.objects.select_for_update().filter(id__in=ids).order_by("id"))


def order_scope(request):
    qs = PurchaseOrderModel.objects.all()
    if request.user_entity.role != "general_director":
        qs = qs.filter(department_id=request.user_entity.department_id) if request.user_entity.department_id else qs.none()
    return qs


def page(request, qs, serializer):
    limit = integer(request.GET.get("limit", "50"), high=100)
    offset = integer(request.GET.get("offset", "0"), low=0, high=1000000)
    return JsonResponse({"items": [serializer(item) for item in qs[offset:offset + limit]], "count": qs.count()})


def sku_data(sku):
    return {"sku_id": sku.id, "sku_code": sku.sku_code, "name_ru": sku.name_ru, "name_ky": sku.name_ky, "name_zh": sku.name_zh}


def wh_data(wh):
    return {"warehouse_id": wh.id, "warehouse_name_ru": wh.name_ru, "warehouse_name_ky": wh.name_ky, "warehouse_name_zh": wh.name_zh}


def audit(request, obj, kind, action, data=None):
    OperationLogModel.objects.create(actor_id=request.user_entity.id, action=action, business_type=kind,
                                    business_id=obj.id, new_data=data or {}, ip_address=request.META.get("REMOTE_ADDR", ""))


def balance(wh, sku, location=None):
    return StockInventoryModel.objects.select_for_update().get_or_create(warehouse=wh, sku=sku, location=location, defaults={"qty": 0, "avg_cost": 0})[0]


@endpoint(None)
def warehouse_catalog_view(request):
    method(request, "GET")
    permissions = sorted(code for code in request.wms_permissions if code.startswith("warehouse."))
    if not permissions:
        raise WmsError("Permission denied", "permission_denied", 403)
    warehouses = list(scope(request).prefetch_related("locations").order_by("id"))
    orders = []
    if warehouses and "warehouse.receipt.manage" in permissions:
        for order in order_scope(request).filter(status__in=["approved", "partially_received"]).prefetch_related("items__sku").order_by("id"):
            lines = []
            for item in order.items.all():
                if item.received_qty >= item.ordered_qty:
                    continue
                line = {"id": item.id, **sku_data(item.sku), "ordered_qty": item.ordered_qty, "received_qty": item.received_qty}
                if "warehouse.cost.read" in permissions:
                    line["unit_cost"] = str(item.unit_price)
                lines.append(line)
            if lines:
                orders.append({"id": order.id, "po_no": order.po_no, "currency": order.currency, "items": lines})
    return JsonResponse({"permissions": permissions,
        "warehouses": [{"id": wh.id, "name_ru": wh.name_ru, "name_ky": wh.name_ky, "name_zh": wh.name_zh,
                        "locations": [{"id": loc.id, "code": loc.code} for loc in wh.locations.all()]} for wh in warehouses],
        "skus": [{"id": sku.id, **{k: v for k, v in sku_data(sku).items() if k != "sku_id"}} for sku in GoodsSKUModel.objects.filter(status="active").order_by("sku_code")] if warehouses else [],
        "purchase_orders": orders})


@endpoint("warehouse.inventory.read")
def warehouse_inventory_view(request):
    method(request, "GET")
    qs = filtered(request, StockInventoryModel.objects.select_related("warehouse", "location", "sku").prefetch_related("batches")).order_by("id")
    def data(item):
        result = {"id": item.id, **wh_data(item.warehouse), **sku_data(item.sku), "location_id": item.location_id,
                  "location_code": item.location.code if item.location else None, "qty": str(item.qty),
                  "batches": [{"batch_no": b.batch_no, "expiry_date": b.expiry_date.isoformat(), "qty": str(b.qty)} for b in item.batches.all()]}
        if "warehouse.cost.read" in request.wms_permissions:
            result["avg_cost"] = str(item.avg_cost)
        return result
    return page(request, qs, data)


@endpoint("warehouse.inventory.read")
def warehouse_movements_view(request):
    method(request, "GET")
    qs = filtered(request, StockMovementModel.objects.select_related("warehouse", "location", "sku")).order_by("-posted_at", "-id")
    limit = integer(request.GET.get("limit", "50"), high=100)
    offset = integer(request.GET.get("offset", "0"), low=0, high=1000000)
    entries = list(qs[offset:offset + limit])
    ids = {kind: {entry.source_id for entry in entries if entry.source_type == kind}
           for kind in ("purchase_receipt", "stock_count", "stock_transfer", "stock_writeoff")}
    numbers = {}
    for kind, model, field in [("purchase_receipt", PurchaseReceiptModel, "receipt_no"), ("stock_count", StockCountModel, "count_no"), ("stock_writeoff", StockWriteoffModel, "writeoff_no")]:
        numbers[kind] = dict(model.objects.filter(id__in=ids[kind], warehouse__in=scope(request)).values_list("id", field))
    # Transfer counterparties may read their shared document number, never the other inventory.
    numbers["stock_transfer"] = dict(StockTransferModel.objects.filter(Q(source_warehouse__in=scope(request)) | Q(destination_warehouse__in=scope(request)), id__in=ids["stock_transfer"]).values_list("id", "transfer_no"))
    items = []
    for item in entries:
        result = {"id": item.id, **wh_data(item.warehouse), **sku_data(item.sku), "location_id": item.location_id,
                  "location_code": item.location.code if item.location else None, "qty_delta": str(item.qty_delta),
                  "movement_type": item.movement_type, "source_type": item.source_type, "source_id": item.source_id,
                  "source_no": numbers.get(item.source_type, {}).get(item.source_id),
                  "reason": item.reason, "posted_at": item.posted_at.isoformat()}
        if "warehouse.cost.read" in request.wms_permissions:
            result["unit_cost"] = str(item.unit_cost)
        items.append(result)
    return JsonResponse({"items": items, "count": qs.count()})


def receipt_data(request, receipt):
    lines = []
    for item in receipt.items.all():
        line = {"id": item.id, "po_item_id": item.po_item_id, **sku_data(item.po_item.sku), "qty": item.qty,
                "location_id": item.location_id, "location_code": item.location.code if item.location else None,
                "batch_no": item.batch_no, "expiry_date": item.expiry_date.isoformat() if item.expiry_date else None,
                "discrepancy_reason": item.discrepancy_reason}
        if "warehouse.cost.read" in request.wms_permissions:
            line["unit_cost"] = str(item.unit_cost)
        lines.append(line)
    return {"id": receipt.id, "receipt_no": receipt.receipt_no, "purchase_order_id": receipt.purchase_order_id,
            "po_no": receipt.purchase_order.po_no, **wh_data(receipt.warehouse), "status": receipt.status,
            "comment": receipt.comment, "received_at": receipt.received_at.isoformat(), "items": lines,
            "allowed_actions": ["post"] if receipt.status == "draft" and "warehouse.receipt.post" in request.wms_permissions else []}


@endpoint(lambda r: "warehouse.receipt.read" if r.method == "GET" else "warehouse.receipt.manage")
def purchase_receipts_view(request):
    method(request, "GET", "POST")
    if request.method == "GET":
        qs = filtered(request, PurchaseReceiptModel.objects.select_related("warehouse", "purchase_order").prefetch_related("items__po_item__sku", "items__location")).order_by("-id")
        if "id" in request.GET:
            qs = qs.filter(id=integer(request.GET["id"]))
        if "purchase_order_id" in request.GET:
            qs = qs.filter(purchase_order_id=integer(request.GET["purchase_order_id"]))
        return page(request, qs, lambda item: receipt_data(request, item))
    body = parse_json_body(request)
    wh = warehouse(request, body.get("warehouse_id"))
    with transaction.atomic():
        lock_warehouses(wh.id)
        order = order_scope(request).select_for_update().filter(id=integer(body.get("purchase_order_id")), status__in=["approved", "partially_received"]).first()
        if not order:
            raise WmsError("Approved purchase order not available", "permission_denied", 403)
        receipt = PurchaseReceiptModel.objects.create(receipt_no=text(body.get("receipt_no"), 64, True), purchase_order=order, warehouse=wh,
                                                    received_by_id=request.user_entity.id, comment=text(body.get("comment", ""), 4000))
        seen = set()
        for row in rows(body):
            item_id = integer(row.get("po_item_id"))
            item = PurchaseOrderItemModel.objects.select_related("sku").filter(id=item_id, purchase_order=order).first()
            if not item or item_id in seen:
                raise WmsError("Invalid or duplicate purchase order line")
            seen.add(item_id)
            qty = integer(row.get("qty"))
            if item.received_qty + qty > item.ordered_qty:
                raise WmsError("Quantity exceeds purchase order remainder")
            reason = text(row.get("discrepancy_reason", ""), 4000)
            if qty != item.ordered_qty - item.received_qty and not reason:
                raise WmsError("A discrepancy reason is required for partial receipt")
            cost = decimal(item.unit_price, places=2, maximum="999999999999.99")
            if "unit_cost" in row:
                if "warehouse.cost.read" not in request.wms_permissions:
                    raise WmsError("Cost override not permitted", "permission_denied", 403)
                cost = decimal(row["unit_cost"], places=2, maximum="999999999999.99")
            loc = None
            if row.get("location_id") is not None:
                loc = WarehouseLocationModel.objects.filter(id=integer(row["location_id"]), warehouse=wh).first()
                if not loc:
                    raise WmsError("Location belongs to another warehouse")
            batch_no = text(row.get("batch_no", ""), 128)
            expiry = date.fromisoformat(row["expiry_date"]) if row.get("expiry_date") else None
            if bool(batch_no) != bool(expiry):
                raise WmsError("Batch and expiry date must be provided together")
            PurchaseReceiptItemModel.objects.create(receipt=receipt, po_item=item, qty=qty, unit_cost=cost, location=loc,
                batch_no=batch_no, expiry_date=expiry, discrepancy_reason=reason)
        audit(request, receipt, "purchase_receipt", "warehouse.receipt_created", {"warehouse_id": wh.id, "purchase_order_id": order.id})
    return JsonResponse({"id": receipt.id, "receipt_no": receipt.receipt_no, "status": receipt.status}, status=201)


@endpoint("warehouse.receipt.post")
def post_purchase_receipt_view(request, receipt_id):
    method(request, "POST")
    with transaction.atomic():
        receipt = PurchaseReceiptModel.objects.select_related("warehouse").filter(id=receipt_id, warehouse__in=scope(request)).first()
        if not receipt:
            raise WmsError("Receipt not available", "not_found", 404)
        lock_warehouses(receipt.warehouse_id)
        receipt = PurchaseReceiptModel.objects.select_for_update().get(id=receipt.id)
        order = PurchaseOrderModel.objects.select_for_update().get(id=receipt.purchase_order_id)
        if receipt.status != "draft":
            raise WmsError("Only draft receipts may be posted", "conflict", 409)
        if order.status not in ("approved", "partially_received"):
            raise WmsError("Purchase order is not approved for receiving", "conflict", 409)
        lines = list(receipt.items.select_related("po_item__sku", "location").order_by("id"))
        if not lines:
            raise WmsError("Receipt requires lines")
        seen = set()
        for line in lines:
            po_item = PurchaseOrderItemModel.objects.select_for_update().get(id=line.po_item_id)
            if (po_item.id in seen or po_item.purchase_order_id != order.id or not line.qty or
                po_item.received_qty + line.qty > po_item.ordered_qty or
                (line.location_id and line.location.warehouse_id != receipt.warehouse_id)):
                raise WmsError("Invalid receipt line or order remainder")
            seen.add(po_item.id)
            if line.qty != po_item.ordered_qty - po_item.received_qty and not line.discrepancy_reason.strip():
                raise WmsError("A discrepancy reason is required for partial receipt")
            decimal(line.unit_cost, places=2, maximum="999999999999.99")
            if bool(line.batch_no) != bool(line.expiry_date):
                raise WmsError("Batch and expiry date must be provided together")
            stock = balance(receipt.warehouse, po_item.sku, line.location)
            new_qty = decimal(stock.qty + line.qty)
            stock.avg_cost = (stock.qty * stock.avg_cost + line.qty * line.unit_cost) / new_qty
            stock.qty = new_qty
            stock.save(update_fields=["qty", "avg_cost"])
            if line.batch_no:
                batch, _ = StockBatchModel.objects.select_for_update().get_or_create(inventory=stock, batch_no=line.batch_no,
                                                                                  defaults={"expiry_date": line.expiry_date, "qty": 0})
                if batch.expiry_date != line.expiry_date:
                    raise WmsError("Existing batch expiry date differs")
                batch.qty = decimal(batch.qty + line.qty)
                batch.save(update_fields=["qty"])
            StockMovementModel.objects.create(warehouse=receipt.warehouse, location=line.location, sku=po_item.sku,
                qty_delta=line.qty, unit_cost=line.unit_cost, movement_type="receipt", source_type="purchase_receipt",
                source_id=receipt.id, reason=line.discrepancy_reason, posted_by_id=request.user_entity.id)
            po_item.received_qty += line.qty
            po_item.save(update_fields=["received_qty"])
        receipt.status = "posted"
        receipt.save(update_fields=["status"])
        order.status = "received" if all(row.received_qty == row.ordered_qty for row in order.items.all()) else "partially_received"
        order.save(update_fields=["status"])
        audit(request, receipt, "purchase_receipt", "warehouse.receipt_posted", {"warehouse_id": receipt.warehouse_id})
    return JsonResponse({"id": receipt.id, "status": receipt.status, "purchase_order_status": order.status})


def count_data(request, count):
    return {"id": count.id, "count_no": count.count_no, **wh_data(count.warehouse), "status": count.status,
            "created_at": count.created_at.isoformat(), "allowed_actions": ["approve"] if count.status == "counted" and "warehouse.count.approve" in request.wms_permissions else [],
            "items": [{**sku_data(row.sku), "system_qty": str(row.system_qty), "actual_qty": str(row.actual_qty), "reason": row.reason} for row in count.items.all()]}


@endpoint(lambda r: "warehouse.count.read" if r.method == "GET" else "warehouse.count.manage")
def stock_counts_view(request):
    method(request, "GET", "POST")
    if request.method == "GET":
        qs = filtered(request, StockCountModel.objects.select_related("warehouse").prefetch_related("items__sku")).order_by("-id")
        if "id" in request.GET:
            qs = qs.filter(id=integer(request.GET["id"]))
        return page(request, qs, lambda item: count_data(request, item))
    body = parse_json_body(request)
    wh = warehouse(request, body.get("warehouse_id"))
    with transaction.atomic():
        lock_warehouses(wh.id)
        count = StockCountModel.objects.create(count_no=text(body.get("count_no"), 64, True), warehouse=wh, status="counted", created_by_id=request.user_entity.id)
        seen = set()
        for row in rows(body):
            sku_id = integer(row.get("sku_id"))
            sku = GoodsSKUModel.objects.filter(id=sku_id, status="active").first()
            if not sku or sku_id in seen:
                raise WmsError("Invalid or duplicate SKU")
            seen.add(sku_id)
            actual = decimal(row.get("actual_qty"))
            system = StockInventoryModel.objects.filter(warehouse=wh, location=None, sku=sku).values_list("qty", flat=True).first() or Decimal(0)
            reason = text(row.get("reason", ""), 4000)
            if actual != system and not reason:
                raise WmsError("A discrepancy reason is required")
            StockCountItemModel.objects.create(count=count, sku=sku, system_qty=system, actual_qty=actual, reason=reason)
        audit(request, count, "stock_count", "warehouse.count_created", {"warehouse_id": wh.id})
    return JsonResponse({"id": count.id, "count_no": count.count_no, "status": count.status}, status=201)


@endpoint("warehouse.count.approve")
def approve_stock_count_view(request, count_id):
    method(request, "POST")
    with transaction.atomic():
        count = StockCountModel.objects.filter(id=count_id, warehouse__in=scope(request)).first()
        if not count:
            raise WmsError("Count not available", "not_found", 404)
        lock_warehouses(count.warehouse_id)
        count = StockCountModel.objects.select_for_update().get(id=count.id)
        if count.status != "counted":
            raise WmsError("Only counted documents may be approved", "conflict", 409)
        lines = list(count.items.select_related("sku").order_by("sku_id"))
        if not lines:
            raise WmsError("Count requires lines")
        for row in lines:
            stock = balance(count.warehouse, row.sku)
            delta = row.actual_qty - row.system_qty
            if stock.qty != row.system_qty:
                raise WmsError("Inventory changed since count; create a fresh count", "conflict", 409)
            if delta and not row.reason.strip():
                raise WmsError("A discrepancy reason is required")
            if delta and stock.batches.filter(qty__gt=0).exists():
                raise WmsError("Batch-aware adjustment is required for this stock", "batch_adjustment_required", 409)
            decimal(row.actual_qty)
            if delta:
                stock.qty = row.actual_qty
                stock.save(update_fields=["qty"])
                StockMovementModel.objects.create(warehouse=count.warehouse, sku=row.sku, qty_delta=delta,
                    unit_cost=stock.avg_cost, movement_type="adjustment", source_type="stock_count", source_id=count.id,
                    reason=row.reason, posted_by_id=request.user_entity.id)
        count.status = "approved"
        count.save(update_fields=["status"])
        audit(request, count, "stock_count", "warehouse.count_approved", {"warehouse_id": count.warehouse_id})
    return JsonResponse({"id": count.id, "status": count.status})


def stock_transfers_view(request):
    # Lazy imports keep shared WMS validation helpers free of import cycles.
    from backend.presentation.api.warehouse_transfer_views import stock_transfers_view as view
    return view(request)


def post_stock_transfer_view(request, transfer_id):
    from backend.presentation.api.warehouse_transfer_views import post_stock_transfer_view as view
    return view(request, transfer_id)


@endpoint("warehouse.inventory.read")
def expiry_alerts_view(request):
    method(request, "GET")
    days = integer(request.GET.get("days", "30"), high=365)
    today = timezone.localdate()
    deadline = today + timedelta(days=days)
    inventories = filtered(request, StockInventoryModel.objects.all())
    batches = StockBatchModel.objects.select_related("inventory__warehouse", "inventory__sku", "inventory__location").filter(inventory__in=inventories, qty__gt=0, expiry_date__lte=deadline).order_by("expiry_date", "id")
    certificates = GoodsCertificateModel.objects.select_related("sku").filter(expires_at__lte=deadline)
    if request.user_entity.role != "general_director" or "warehouse_id" in request.GET:
        certificates = certificates.filter(sku_id__in=inventories.values("sku_id"))
    batches_count, certificates_count = batches.count(), certificates.count()
    return JsonResponse({"as_of": today.isoformat(), "days": days,
        "batches_count": batches_count, "certificates_count": certificates_count,
        "truncated": batches_count > 500 or certificates_count > 500,
        "batches": [{"id": item.id, **wh_data(item.inventory.warehouse), **sku_data(item.inventory.sku), "batch_no": item.batch_no,
                    "expiry_date": item.expiry_date.isoformat(), "qty": str(item.qty), "expired": item.expiry_date < today,
                    "location_id": item.inventory.location_id, "location_code": item.inventory.location.code if item.inventory.location else None} for item in batches[:500]],
        "certificates": [{"id": item.id, **sku_data(item.sku), "number": item.number, "expires_at": item.expires_at.isoformat(), "expired": item.expires_at < today}
                         for item in certificates.order_by("expires_at", "id")[:500]]})
