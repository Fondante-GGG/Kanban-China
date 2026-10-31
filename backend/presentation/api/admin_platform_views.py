from decimal import Decimal, InvalidOperation
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from backend.infrastructure.persistence.models import AdminAssetModel, AdminAssetLogModel, AdminNoticeModel, EmployeeModel, AdminLicenseModel, DepartmentModel, AdminSupplyModel, AdminSupplyRequestModel, AdminMeetingRoomModel, AdminMeetingBookingModel
from django.db import transaction
from backend.presentation.api.platform_views import _require
from backend.presentation.api.utils import parse_json_body
from backend.presentation.middlewares import login_required_domain

@csrf_exempt
@login_required_domain
def assets_view(request):
    denied=_require(request,"admin.asset.manage" if request.method!="GET" else "admin.asset.read")
    if denied:return denied
    if request.method=="GET": return JsonResponse({"items":[{"id":x.id,"asset_no":x.asset_no,"name":x.name,"category":x.category,"owner_id":x.owner_id,"status":x.status,"price":str(x.price)} for x in AdminAssetModel.objects.select_related("owner").all()]})
    if request.method!="POST":return JsonResponse({"error":"Method not allowed"},status=405)
    b=parse_json_body(request)
    if not b.get("asset_no") or not b.get("name") or not b.get("category"):return JsonResponse({"error":"asset_no, name and category are required"},status=400)
    try: price=Decimal(str(b.get("price",0)))
    except InvalidOperation:return JsonResponse({"error":"invalid price"},status=400)
    owner=EmployeeModel.objects.filter(id=b.get("owner_id")).first() if b.get("owner_id") else None
    x=AdminAssetModel.objects.create(asset_no=str(b["asset_no"]),name=str(b["name"]),category=str(b["category"]),price=price,owner=owner)
    return JsonResponse({"id":x.id,"asset_no":x.asset_no},status=201)


@csrf_exempt
@login_required_domain
def asset_custody_view(request, asset_id):
    """Records the custody chain used by the mandatory termination check."""
    denied = _require(request, "admin.asset.manage" if request.method == "POST" else "admin.asset.read")
    if denied: return denied
    with transaction.atomic():
        asset = AdminAssetModel.objects.select_for_update().filter(id=asset_id).first()
        if not asset: return JsonResponse({"error": "Asset not found"}, status=404)
        if request.method == "GET":
            return JsonResponse({"asset_id": asset.id, "owner_id": asset.owner_id, "logs": [{"id": log.id, "employee_id": log.employee_id, "operation": log.operation, "comment": log.comment, "created_at": log.created_at.isoformat()} for log in asset.logs.all()]})
        if request.method != "POST": return JsonResponse({"error": "Method not allowed"}, status=405)
        body = parse_json_body(request); operation = body.get("operation")
        if operation not in ("issued", "returned"): return JsonResponse({"error": "operation must be issued or returned"}, status=400)
        employee = EmployeeModel.objects.filter(id=body.get("employee_id")).first()
        if not employee: return JsonResponse({"error": "Employee not found"}, status=404)
        if operation == "issued":
            if asset.owner_id: return JsonResponse({"error": "Asset is already issued"}, status=409)
            if asset.status != "in_use": return JsonResponse({"error": "Only usable assets can be issued"}, status=409)
            asset.owner = employee; asset.save(update_fields=["owner"])
        else:
            if asset.owner_id != employee.id: return JsonResponse({"error": "Asset is not issued to this employee"}, status=409)
            asset.owner = None; asset.save(update_fields=["owner"])
        log = AdminAssetLogModel.objects.create(asset=asset, employee=employee, operation=operation, performed_by_id=request.user_entity.id, comment=str(body.get("comment", "")))
    return JsonResponse({"id": log.id, "asset_id": asset.id, "owner_id": asset.owner_id, "operation": log.operation}, status=201)


@csrf_exempt
@login_required_domain
def supply_requests_view(request):
    """Employees submit their own stationery requests; an administrator approves stock issue."""
    can_manage = _require(request, "admin.request.manage") is None
    if request.method == "GET":
        qs = AdminSupplyRequestModel.objects.select_related("supply", "requester")
        if not can_manage: qs = qs.filter(requester_id=request.user_entity.id)
        return JsonResponse({"items": [{"id": x.id, "supply_id": x.supply_id, "supply_name": x.supply.name, "qty": str(x.qty), "status": x.status, "comment": x.comment, "requester_id": x.requester_id} for x in qs[:200]]})
    if request.method != "POST": return JsonResponse({"error": "Method not allowed"}, status=405)
    body = parse_json_body(request)
    if body.get("action") in ("approve", "reject"):
        if not can_manage: return JsonResponse({"error": "Permission denied"}, status=403)
        with transaction.atomic():
            item = AdminSupplyRequestModel.objects.select_for_update().select_related("supply").filter(id=body.get("request_id"), status="pending").first()
            if not item: return JsonResponse({"error": "Pending request not found"}, status=404)
            if body["action"] == "approve":
                if item.supply.stock_qty < item.qty: return JsonResponse({"error": "Insufficient stationery stock"}, status=409)
                item.supply.stock_qty -= item.qty; item.supply.save(update_fields=["stock_qty"]); item.status = "approved"
            else: item.status = "rejected"
            item.save(update_fields=["status"])
        return JsonResponse({"id": item.id, "status": item.status})
    try:
        supply = AdminSupplyModel.objects.get(id=body["supply_id"]); qty = Decimal(str(body["qty"]))
        if qty <= 0: raise ValueError
    except (KeyError, AdminSupplyModel.DoesNotExist, InvalidOperation, ValueError): return JsonResponse({"error": "valid supply_id and positive qty are required"}, status=400)
    item = AdminSupplyRequestModel.objects.create(supply=supply, requester_id=request.user_entity.id, qty=qty, status="pending", comment=str(body.get("comment", "")))
    return JsonResponse({"id": item.id, "status": item.status}, status=201)


@csrf_exempt
@login_required_domain
def meeting_bookings_view(request):
    """Self-service room reservation with overlap protection and owner-only cancellation."""
    if request.method == "GET":
        qs = AdminMeetingBookingModel.objects.select_related("room").filter(requester_id=request.user_entity.id)
        return JsonResponse({"items": [{"id": x.id, "room_id": x.room_id, "room_name": x.room.name, "start_at": x.start_at.isoformat(), "end_at": x.end_at.isoformat(), "status": x.status} for x in qs.order_by("start_at")[:200]]})
    if request.method != "POST": return JsonResponse({"error": "Method not allowed"}, status=405)
    body = parse_json_body(request)
    if body.get("action") == "cancel":
        booking = AdminMeetingBookingModel.objects.filter(id=body.get("booking_id"), requester_id=request.user_entity.id, status="booked").first()
        if not booking: return JsonResponse({"error": "Active own booking not found"}, status=404)
        booking.status = "cancelled"; booking.save(update_fields=["status"])
        return JsonResponse({"id": booking.id, "status": booking.status})
    from django.utils.dateparse import parse_datetime
    start_at, end_at = parse_datetime(str(body.get("start_at", ""))), parse_datetime(str(body.get("end_at", "")))
    room = AdminMeetingRoomModel.objects.filter(id=body.get("room_id"), is_active=True).first()
    if not room or not start_at or not end_at or end_at <= start_at: return JsonResponse({"error": "active room and valid start_at/end_at are required"}, status=400)
    with transaction.atomic():
        # Lock current bookings for this room so competing requests cannot both win.
        overlaps = AdminMeetingBookingModel.objects.select_for_update().filter(room=room, status="booked", start_at__lt=end_at, end_at__gt=start_at)
        if overlaps.exists(): return JsonResponse({"error": "Room is already booked for this time"}, status=409)
        booking = AdminMeetingBookingModel.objects.create(room=room, requester_id=request.user_entity.id, start_at=start_at, end_at=end_at)
    return JsonResponse({"id": booking.id, "status": booking.status}, status=201)

@csrf_exempt
@login_required_domain
def notices_view(request):
    denied=_require(request,"admin.notice.manage" if request.method!="GET" else "admin.notice.read")
    if denied:return denied
    if request.method=="GET":return JsonResponse({"items":[{"id":x.id,"title_ru":x.title_ru,"title_zh":x.title_zh,"title_ky":x.title_ky,"content_ru":x.content_ru,"content_zh":x.content_zh,"content_ky":x.content_ky,"is_top":x.is_top,"published_at":x.published_at.isoformat()} for x in AdminNoticeModel.objects.all()]})
    if request.method!="POST":return JsonResponse({"error":"Method not allowed"},status=405)
    b=parse_json_body(request)
    if not b.get("title_ru") or not b.get("content_ru"):return JsonResponse({"error":"Russian title and content are required"},status=400)
    x=AdminNoticeModel.objects.create(title_ru=str(b["title_ru"]),title_zh=str(b.get("title_zh", "")),title_ky=str(b.get("title_ky", "")),content_ru=str(b["content_ru"]),content_zh=str(b.get("content_zh", "")),content_ky=str(b.get("content_ky", "")),is_top=bool(b.get("is_top",False)),published_by_id=request.user_entity.id)
    return JsonResponse({"id":x.id},status=201)

@csrf_exempt
@login_required_domain
def licenses_view(request):
    denied=_require(request,"admin.license.manage" if request.method!="GET" else "admin.license.read")
    if denied:return denied
    if request.method=="GET":return JsonResponse({"items":[{"id":x.id,"license_type":x.license_type,"owner_department_id":x.owner_department_id,"issue_date":x.issue_date.isoformat(),"expiry_date":x.expiry_date.isoformat(),"file_path":x.file_path} for x in AdminLicenseModel.objects.all()]})
    if request.method!="POST":return JsonResponse({"error":"Method not allowed"},status=405)
    b=parse_json_body(request)
    from datetime import date
    try:issue=date.fromisoformat(b["issue_date"]);expiry=date.fromisoformat(b["expiry_date"]);department=DepartmentModel.objects.get(id=b["owner_department_id"])
    except (KeyError,ValueError,DepartmentModel.DoesNotExist):return JsonResponse({"error":"valid owner_department_id, issue_date and expiry_date are required"},status=400)
    if expiry<=issue:return JsonResponse({"error":"expiry_date must be after issue_date"},status=400)
    x=AdminLicenseModel.objects.create(license_type=str(b.get("license_type","")),file_path=str(b.get("file_path","")),issue_date=issue,expiry_date=expiry,owner_department=department,created_by_id=request.user_entity.id)
    return JsonResponse({"id":x.id},status=201)
