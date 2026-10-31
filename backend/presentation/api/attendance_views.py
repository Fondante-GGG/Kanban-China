import json
from datetime import datetime
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from backend.infrastructure.di.container import container
from backend.presentation.middlewares import login_required_domain
from backend.domain.entities import Office, WorkSchedule
from backend.domain.exceptions import PermissionDeniedException, ValidationException
from backend.application.dtos import (
    CheckInDTO, CheckOutDTO, LeaveAbsenceDTO, LocationLogDTO,
    AttendanceRecordEditDTO, ConsentDTO, DayStatusDTO, OfficeDTO, WorkScheduleDTO
)
from backend.presentation.api.platform_views import _require
from backend.infrastructure.persistence.models import EmployeeModel, MonthlyTimesheetModel, AttendanceRecordModel


def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


@csrf_exempt
@login_required_domain
def attendance_status_view(request):
    if request.method == "GET":
        use_case = container.get_attendance_status_use_case()
        data = use_case.execute(request.user_entity)
        return JsonResponse(data, status=200)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
@login_required_domain
def check_in_view(request):
    if request.method == "POST":
        try:
            body = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            body = {}

        dto = CheckInDTO(
            latitude=body.get("latitude"),
            longitude=body.get("longitude"),
            accuracy_meters=body.get("accuracy_meters"),
            office_id=body.get("office_id"),
            ip_address=get_client_ip(request)
        )
        use_case = container.get_check_in_use_case()
        res = use_case.execute(request.user_entity, dto)
        return JsonResponse(res, status=200)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
@login_required_domain
def check_out_view(request):
    if request.method == "POST":
        try:
            body = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            body = {}

        dto = CheckOutDTO(
            latitude=body.get("latitude"),
            longitude=body.get("longitude"),
            accuracy_meters=body.get("accuracy_meters"),
            office_id=body.get("office_id"),
            ip_address=get_client_ip(request)
        )
        use_case = container.get_check_out_use_case()
        res = use_case.execute(request.user_entity, dto)
        return JsonResponse(res, status=200)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
@login_required_domain
def leave_absence_view(request):
    if request.method == "POST":
        try:
            body = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON body"}, status=400)

        dto = LeaveAbsenceDTO(
            absence_type=body.get("absence_type", "lunch"),
            reason=body.get("reason", ""),
            comment=body.get("comment", "")
        )
        use_case = container.get_leave_absence_use_case()
        res = use_case.execute(request.user_entity, dto)
        return JsonResponse(res, status=200)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
@login_required_domain
def resume_absence_view(request):
    if request.method == "POST":
        use_case = container.get_resume_absence_use_case()
        res = use_case.execute(request.user_entity)
        return JsonResponse(res, status=200)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
@login_required_domain
def location_log_view(request):
    if request.method == "POST":
        try:
            body = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON body"}, status=400)

        if "latitude" not in body or "longitude" not in body:
            return JsonResponse({"error": "latitude and longitude are required"}, status=400)

        dto = LocationLogDTO(
            latitude=float(body["latitude"]),
            longitude=float(body["longitude"]),
            accuracy_meters=body.get("accuracy_meters"),
            source=body.get("source", "gps")
        )
        use_case = container.get_location_log_use_case()
        res = use_case.execute(request.user_entity, dto)
        return JsonResponse(res, status=200)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
@login_required_domain
def attendance_records_view(request):
    if request.method == "GET":
        user_id = request.GET.get("user_id")
        user_id = int(user_id) if user_id else None

        dept_id = request.GET.get("department_id")
        dept_id = int(dept_id) if dept_id else None

        start_date_str = request.GET.get("start_date")
        end_date_str = request.GET.get("end_date")

        start_date = None
        end_date = None
        if start_date_str:
            try:
                start_date = datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))
            except Exception:
                pass
        if end_date_str:
            try:
                end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
            except Exception:
                pass

        use_case = container.get_list_attendance_records_use_case()
        records = use_case.execute(
            current_user=request.user_entity,
            user_id=user_id,
            department_id=dept_id,
            start_date=start_date,
            end_date=end_date
        )
        return JsonResponse({"records": records}, status=200)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
@login_required_domain
def attendance_record_detail_view(request, record_id: int):
    if request.method == "PUT":
        try:
            body = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON body"}, status=400)

        timestamp_str = body.get("timestamp")
        edit_reason = body.get("edit_reason")

        if not timestamp_str or not edit_reason:
            return JsonResponse({"error": "timestamp and edit_reason are required"}, status=400)

        dto = AttendanceRecordEditDTO(
            timestamp=timestamp_str,
            edit_reason=edit_reason
        )
        use_case = container.get_edit_attendance_record_use_case()
        res = use_case.execute(request.user_entity, record_id, dto)
        return JsonResponse(res, status=200)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
@login_required_domain
def consent_view(request):
    use_case = container.get_manage_consent_use_case()
    if request.method == "GET":
        data = use_case.get_status(request.user_entity)
        return JsonResponse(data, status=200)

    elif request.method == "POST":
        try:
            body = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON body"}, status=400)

        dto = ConsentDTO(
            is_granted=bool(body.get("is_granted", True)),
            consent_version=body.get("consent_version", "1.0"),
            consent_text=body.get("consent_text", "")
        )
        res = use_case.set_consent(request.user_entity, dto)
        return JsonResponse(res, status=200)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
@login_required_domain
def day_status_view(request):
    if request.method == "POST":
        try:
            body = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON body"}, status=400)

        dto = DayStatusDTO(
            user_id=body.get("user_id") or request.user_entity.id,
            absence_type=body.get("absence_type", "vacation"),
            start_time=body.get("start_time") or timezone.now().isoformat(),
            end_time=body.get("end_time"),
            reason=body.get("reason", ""),
            comment=body.get("comment", "")
        )
        use_case = container.get_create_day_status_use_case()
        res = use_case.execute(request.user_entity, dto)
        return JsonResponse(res, status=200)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
@login_required_domain
def offices_view(request):
    with container.get_uow() as uow:
        if request.method == "GET":
            offices = uow.offices.list_all()
            return JsonResponse({
                "offices": [
                    {
                        "id": o.id,
                        "name": o.name,
                        "address": o.address,
                        "latitude": o.latitude,
                        "longitude": o.longitude,
                        "radius_meters": o.radius_meters,
                        "ip_subnet": o.ip_subnet,
                        "is_ip_check_enabled": o.is_ip_check_enabled,
                    }
                    for o in offices
                ]
            }, status=200)

        elif request.method == "POST":
            if not request.user_entity.is_general_director:
                raise PermissionDeniedException("Только Генеральный директор может создавать офисы.")

            try:
                body = json.loads(request.body or "{}")
            except json.JSONDecodeError:
                return JsonResponse({"error": "Invalid JSON body"}, status=400)

            office = uow.offices.create(
                Office(
                    id=None,
                    name=body.get("name", "Новый офис"),
                    address=body.get("address", "ул. Мухаммеда Али Джиннаха, 15/1"),
                    latitude=float(body.get("latitude", 40.512143)),
                    longitude=float(body.get("longitude", 72.808202)),
                    radius_meters=int(body.get("radius_meters", 100)),
                    ip_subnet=body.get("ip_subnet", ""),
                    is_ip_check_enabled=bool(body.get("is_ip_check_enabled", False)),
                )
            )
            return JsonResponse({
                "id": office.id,
                "name": office.name,
                "address": office.address,
                "latitude": office.latitude,
                "longitude": office.longitude,
                "radius_meters": office.radius_meters,
                "ip_subnet": office.ip_subnet,
                "is_ip_check_enabled": office.is_ip_check_enabled,
            }, status=201)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
@login_required_domain
def office_detail_view(request, office_id: int):
    with container.get_uow() as uow:
        office = uow.offices.get_by_id(office_id)
        if not office:
            return JsonResponse({"error": "Офис не найден"}, status=404)

        if request.method == "PUT":
            if not request.user_entity.is_general_director:
                raise PermissionDeniedException("Только Генеральный директор может изменять офисы.")
            try:
                body = json.loads(request.body or "{}")
            except json.JSONDecodeError:
                return JsonResponse({"error": "Invalid JSON body"}, status=400)

            office.name = body.get("name", office.name)
            office.address = body.get("address", office.address)
            office.latitude = float(body.get("latitude", office.latitude))
            office.longitude = float(body.get("longitude", office.longitude))
            office.radius_meters = int(body.get("radius_meters", office.radius_meters))
            office.ip_subnet = body.get("ip_subnet", office.ip_subnet)
            office.is_ip_check_enabled = bool(body.get("is_ip_check_enabled", office.is_ip_check_enabled))

            updated = uow.offices.update(office)
            return JsonResponse({
                "id": updated.id,
                "name": updated.name,
                "address": updated.address,
                "latitude": updated.latitude,
                "longitude": updated.longitude,
                "radius_meters": updated.radius_meters,
                "ip_subnet": updated.ip_subnet,
                "is_ip_check_enabled": updated.is_ip_check_enabled,
            }, status=200)

        elif request.method == "DELETE":
            if not request.user_entity.is_general_director:
                raise PermissionDeniedException("Только Генеральный директор может удалять офисы.")
            uow.offices.delete(office_id)
            return JsonResponse({"success": True}, status=200)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
@login_required_domain
def work_schedules_view(request):
    with container.get_uow() as uow:
        if request.method == "GET":
            schedules = uow.work_schedules.list_all()
            return JsonResponse({
                "schedules": [
                    {
                        "id": s.id,
                        "name": s.name,
                        "user_id": s.user_id,
                        "user_full_name": s.user_full_name,
                        "department_id": s.department_id,
                        "department_name": s.department_name,
                        "start_time": s.start_time,
                        "end_time": s.end_time,
                        "break_duration_minutes": s.break_duration_minutes,
                        "timezone": s.timezone,
                        "is_active": s.is_active,
                    }
                    for s in schedules
                ]
            }, status=200)

        elif request.method == "POST":
            if not request.user_entity.is_general_director:
                raise PermissionDeniedException("Только Генеральный директор может управлять графиками работы.")

            try:
                body = json.loads(request.body or "{}")
            except json.JSONDecodeError:
                return JsonResponse({"error": "Invalid JSON body"}, status=400)

            sched = uow.work_schedules.create(
                WorkSchedule(
                    id=None,
                    name=body.get("name", "График"),
                    user_id=body.get("user_id"),
                    department_id=body.get("department_id"),
                    start_time=body.get("start_time", "09:00"),
                    end_time=body.get("end_time", "18:00"),
                    break_duration_minutes=int(body.get("break_duration_minutes", 60)),
                    timezone=body.get("timezone", "Asia/Bishkek"),
                    is_active=bool(body.get("is_active", True)),
                )
            )
            return JsonResponse({
                "id": sched.id,
                "name": sched.name,
                "start_time": sched.start_time,
                "end_time": sched.end_time,
                "break_duration_minutes": sched.break_duration_minutes,
            }, status=201)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
@login_required_domain
def attendance_timesheet_view(request):
    if request.method == "GET":
        now = timezone.localtime()
        year = int(request.GET.get("year", now.year))
        month = int(request.GET.get("month", now.month))
        dept_id = request.GET.get("department_id")
        dept_id = int(dept_id) if dept_id else None
        user_id = request.GET.get("user_id")
        user_id = int(user_id) if user_id else None

        use_case = container.get_monthly_timesheet_use_case()
        data = use_case.execute(
            current_user=request.user_entity,
            year=year,
            month=month,
            department_id=dept_id,
            user_id=user_id
        )
        return JsonResponse(data, status=200)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
@login_required_domain
def confirm_monthly_timesheet_view(request):
    if request.method != "POST": return JsonResponse({"error": "Method not allowed"}, status=405)
    denied = _require(request, "attendance.timesheet.confirm")
    if denied: return denied
    try:
        body = json.loads(request.body or "{}"); employee = EmployeeModel.objects.get(id=body["employee_id"], status="active")
        year, month = int(body["year"]), int(body["month"])
        if not 1 <= month <= 12: raise ValueError
    except (json.JSONDecodeError, KeyError, ValueError, EmployeeModel.DoesNotExist):
        return JsonResponse({"error": "valid active employee, year and month are required"}, status=400)
    if not employee.user_id: return JsonResponse({"error": "Employee has no active account"}, status=409)
    from datetime import date
    from django.db.models import Count
    from django.db import IntegrityError
    start = date(year, month, 1); end = date(year + (month == 12), (month % 12) + 1, 1)
    counts = AttendanceRecordModel.objects.filter(user_id=employee.user_id, timestamp__date__gte=start, timestamp__date__lt=end, verification_result__in=["verified", "manual_override"]).values("record_type").annotate(total=Count("id"))
    snapshot = {item["record_type"]: item["total"] for item in counts}
    try:
        sheet = MonthlyTimesheetModel.objects.create(employee=employee, year=year, month=month, snapshot=snapshot, confirmed_by_id=request.user_entity.id)
    except IntegrityError:
        return JsonResponse({"error": "Monthly timesheet is already confirmed"}, status=409)
    return JsonResponse({"id": sheet.id, "employee_id": employee.id, "year": year, "month": month, "snapshot": snapshot, "status": sheet.status}, status=201)


@csrf_exempt
@login_required_domain
def attendance_export_view(request):
    if request.method == "GET":
        fmt = request.GET.get("format", "xlsx")
        now = timezone.localtime()
        year = int(request.GET.get("year", now.year))
        month = int(request.GET.get("month", now.month))
        dept_id = request.GET.get("department_id")
        dept_id = int(dept_id) if dept_id else None
        user_id = request.GET.get("user_id")
        user_id = int(user_id) if user_id else None

        use_case = container.get_export_monthly_timesheet_use_case()
        file_bytes, content_type, filename = use_case.execute(
            current_user=request.user_entity,
            fmt=fmt,
            year=year,
            month=month,
            department_id=dept_id,
            user_id=user_id
        )

        response = HttpResponse(file_bytes, content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    return JsonResponse({"error": "Method not allowed"}, status=405)
