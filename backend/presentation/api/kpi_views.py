"""KPI workflow API.

New assessments require self -> manager -> independent director review -> confirmed.
Existing confirmed assessments remain valid. Employee acknowledgement and archival
are separate immutable facts. Formula values are metadata only: no code executes.
"""
from decimal import Decimal, InvalidOperation

from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from backend.domain.exceptions import ValidationException
from backend.infrastructure.persistence.models import (
    EmployeeModel, KpiTaskModel, KpiTemplateItemModel, KpiTemplateModel,
    OperationLogModel,
)
from backend.presentation.api.platform_views import _permissions
from backend.presentation.api.utils import parse_json_body
from backend.presentation.middlewares import login_required_domain


def _error(message, code="validation_error", status=400):
    return JsonResponse({"error": message, "code": code}, status=status)


def _body(request):
    try:
        return parse_json_body(request)
    except ValidationException:
        raise ValueError("A JSON object body is required")


def _text(value, maximum, required=False):
    if not isinstance(value, str) or len(value) > maximum or (required and not value.strip()):
        raise ValueError("Invalid text field")
    return value.strip()


def _number(value, maximum=100, positive=False):
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise ValueError("A valid decimal number is required")
    try:
        result = Decimal(str(value))
        if not result.is_finite() or not 0 <= result <= maximum or (positive and result == 0):
            raise ValueError("Number outside the permitted range")
        if result != result.quantize(Decimal("0.01")):
            raise ValueError("At most two decimal places are permitted")
        return result
    except InvalidOperation as exc:
        raise ValueError("A valid decimal number is required") from exc


def _integer(value, minimum, maximum):
    if isinstance(value, bool) or not str(value).isdigit():
        raise ValueError("A valid integer is required")
    result = int(value)
    if not minimum <= result <= maximum:
        raise ValueError("Integer outside the permitted range")
    return result


def _comments(body):
    return {lang: _text(body.get(f"comment_{lang}", ""), 4000) for lang in ("ru", "zh", "ky")}


def _scope(user, queryset, prefix=""):
    if user.role == "general_director":
        return queryset
    if user.role == "manager":
        # A manager with no department does not manage all unassigned employees.
        return queryset.filter(**{f"{prefix}department_id": user.department_id}) if user.department_id else queryset.none()
    return queryset.filter(**{f"{prefix}user_id": user.id})


def _can_manage(user, permissions, employee):
    return "kpi.manage" in permissions and (
        user.role == "general_director" or
        (user.role == "manager" and user.department_id is not None and employee.department_id == user.department_id)
    )


def _actions(user, permissions, task):
    if task.archived_at or not ({"kpi.read", "kpi.manage"} & permissions):
        return []
    actions = []
    if task.employee.user_id == user.id:
        if task.status == "self_review":
            actions.append("self_score")
        if task.status == "confirmed" and not task.acknowledged_at:
            actions.append("acknowledge")
    if _can_manage(user, permissions, task.employee):
        if task.status == "manager_review" and task.employee.user_id != user.id:
            actions.append("manager_score")
        if (task.status == "senior_review" and user.role == "general_director"
                and task.manager_scored_by_id != user.id and task.employee.user_id != user.id):
            actions.append("review")
        if task.status == "confirmed" and task.acknowledged_at:
            actions.append("archive")
    return actions


def _audit(request, task, action, old_data=None, new_data=None):
    OperationLogModel.objects.create(
        actor_id=request.user_entity.id, action=action, business_type="kpi_task",
        business_id=task.id, old_data=old_data or {}, new_data=new_data or {},
        ip_address=request.META.get("REMOTE_ADDR", ""),
    )


def _task_data(task, user, permissions, history=()):
    return {
        "id": task.id, "employee_id": task.employee_id, "template_id": task.template_id,
        "employee_name_ru": task.employee.full_name_ru, "employee_name_zh": task.employee.full_name_zh,
        "employee_name_ky": task.employee.full_name_ky, "template_name": task.template.name,
        "position_code": task.template.position_code, "cycle": task.template.cycle,
        "year": task.year, "period": task.period, "status": task.status,
        **{field: str(getattr(task, field)) if getattr(task, field) is not None else None
           for field in ("self_score", "manager_score", "final_score")},
        **{field: getattr(task, field).isoformat() if getattr(task, field) else None
           for field in ("acknowledged_at", "reviewed_at", "archived_at")},
        "manager_scored_by_id": task.manager_scored_by_id, "reviewed_by_id": task.reviewed_by_id,
        "comments": task.comments, "allowed_actions": _actions(user, permissions, task),
        "history": [{"id": log.id, "action": log.action, "actor_name": log.actor.full_name if log.actor else "",
                     "created_at": log.created_at.isoformat(), "old_data": log.old_data, "new_data": log.new_data}
                    for log in history],
    }


@csrf_exempt
@login_required_domain
def kpi_templates_view(request):
    if request.method not in ("GET", "POST"):
        return _error("Method not allowed", "method_not_allowed", 405)
    permissions = _permissions(request.user_entity.id)
    if not ({"kpi.read", "kpi.manage"} & permissions) or (request.method == "POST" and "kpi.manage" not in permissions):
        return _error("Permission denied", "permission_denied", 403)
    if request.method == "GET":
        return JsonResponse({"items": [{
            "id": item.id, "name": item.name, "position_code": item.position_code,
            "cycle": item.cycle, "is_active": item.is_active,
            "items": [{"id": row.id, "name_ru": row.name_ru, "name_zh": row.name_zh,
                       "name_ky": row.name_ky, "weight": str(row.weight), "formula": row.formula}
                      for row in item.items.all()],
        } for item in KpiTemplateModel.objects.prefetch_related("items").order_by("id")]})
    try:
        body = _body(request)
        name = _text(body.get("name"), 255, required=True)
        position = _text(body.get("position_code"), 128, required=True)
        cycle = body.get("cycle")
        rows = body.get("items")
        if cycle not in ("month", "quarter", "year") or not isinstance(rows, list) or not 1 <= len(rows) <= 100:
            raise ValueError("A valid cycle and 1 to 100 KPI items are required")
        items = []
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("Each KPI item must be an object")
            formula = row.get("formula", "")
            if formula not in ("", "manual"):
                raise ValueError("Only manual indicators are supported")
            items.append({"name_ru": _text(row.get("name_ru"), 255, required=True),
                          "name_zh": _text(row.get("name_zh", ""), 255),
                          "name_ky": _text(row.get("name_ky", ""), 255),
                          "weight": _number(row.get("weight"), positive=True), "formula": formula})
        if sum(row["weight"] for row in items) != Decimal("100"):
            raise ValueError("KPI weights must total 100")
    except ValueError as exc:
        return _error(str(exc))
    with transaction.atomic():
        template = KpiTemplateModel.objects.create(name=name, position_code=position, cycle=cycle)
        KpiTemplateItemModel.objects.bulk_create([KpiTemplateItemModel(template=template, **row) for row in items])
        OperationLogModel.objects.create(
            actor_id=request.user_entity.id, action="kpi.template_created",
            business_type="kpi_template", business_id=template.id,
            new_data={"name": name, "position_code": position, "cycle": cycle,
                      "items": [{**row, "weight": str(row["weight"])} for row in items]},
            ip_address=request.META.get("REMOTE_ADDR", ""),
        )
    return JsonResponse({"id": template.id}, status=201)


@login_required_domain
def kpi_assignees_view(request):
    if request.method != "GET":
        return _error("Method not allowed", "method_not_allowed", 405)
    permissions = _permissions(request.user_entity.id)
    if "kpi.manage" not in permissions:
        return _error("Permission denied", "permission_denied", 403)
    qs = _scope(request.user_entity, EmployeeModel.objects.filter(status="active", user__is_active=True))
    return JsonResponse({"items": [{"id": employee.id, "full_name_ru": employee.full_name_ru,
                                   "full_name_zh": employee.full_name_zh, "full_name_ky": employee.full_name_ky,
                                   "position": employee.position, "department_id": employee.department_id}
                                  for employee in qs.order_by("full_name_ru", "id")]})


@csrf_exempt
@login_required_domain
def kpi_tasks_view(request):
    if request.method not in ("GET", "POST"):
        return _error("Method not allowed", "method_not_allowed", 405)
    user = request.user_entity
    permissions = _permissions(user.id)
    if not ({"kpi.read", "kpi.manage"} & permissions):
        return _error("Permission denied", "permission_denied", 403)
    if request.method == "GET":
        qs = _scope(user, KpiTaskModel.objects.select_related("employee", "template"), "employee__")
        try:
            archived = request.GET.get("archived", "false")
            if archived not in ("true", "false"):
                raise ValueError("archived must be true or false")
            qs = qs.filter(archived_at__isnull=archived == "false")
            if "status" in request.GET:
                if request.GET["status"] not in dict(KpiTaskModel.STATUS):
                    raise ValueError("Unknown KPI status")
                qs = qs.filter(status=request.GET["status"])
            if "year" in request.GET:
                qs = qs.filter(year=_integer(request.GET["year"], 2000, 9999))
            limit = _integer(request.GET.get("limit", "100"), 1, 100)
            offset = _integer(request.GET.get("offset", "0"), 0, 1000000)
        except ValueError as exc:
            return _error(str(exc))
        count = qs.count()
        tasks = list(qs.order_by("-year", "-id")[offset:offset + limit])
        history = {}
        logs = OperationLogModel.objects.filter(business_type="kpi_task", business_id__in=[task.id for task in tasks]).select_related("actor").order_by("created_at", "id")
        for log in logs:
            history.setdefault(log.business_id, []).append(log)
        return JsonResponse({"items": [_task_data(task, user, permissions, history.get(task.id, ())) for task in tasks], "count": count})
    if "kpi.manage" not in permissions:
        return _error("Permission denied", "permission_denied", 403)
    try:
        body = _body(request)
        template_id = _integer(body.get("template_id"), 1, 2**63 - 1)
        employee_id = _integer(body.get("employee_id"), 1, 2**63 - 1)
        year = _integer(body.get("year"), 2000, 9999)
        period = _text(body.get("period"), 16, required=True)
    except ValueError as exc:
        return _error(str(exc))
    employee = _scope(user, EmployeeModel.objects.filter(status="active", user__is_active=True)).filter(id=employee_id).first()
    if employee is None or not _can_manage(user, permissions, employee):
        return _error("Permission denied", "permission_denied", 403)
    template = KpiTemplateModel.objects.filter(id=template_id, is_active=True).first()
    if template is None:
        return _error("Active KPI template not found", "not_found", 404)
    valid_periods = {"month": {f"{month:02}" for month in range(1, 13)}, "quarter": {str(q) for q in range(1, 5)}, "year": {"year"}}
    if period not in valid_periods.get(template.cycle, set()):
        return _error("Period does not match the template cycle")
    try:
        with transaction.atomic():
            task = KpiTaskModel.objects.create(template=template, employee=employee, year=year, period=period)
            _audit(request, task, "kpi.assigned", new_data={"template_id": template.id, "employee_id": employee.id, "year": year, "period": period})
    except IntegrityError:
        return _error("An assessment already exists for this period", "duplicate_task", 409)
    return JsonResponse({"id": task.id, "status": task.status}, status=201)


@csrf_exempt
@login_required_domain
def kpi_task_score_view(request, task_id):
    if request.method != "POST":
        return _error("Method not allowed", "method_not_allowed", 405)
    try:
        body = _body(request)
        score = _number(body.get("score"))
        comments = _comments(body)
        stage = body.get("stage")
        if stage not in ("self", "manager"):
            raise ValueError("stage must be self or manager")
    except ValueError as exc:
        return _error(str(exc))
    user = request.user_entity
    permissions = _permissions(user.id)
    with transaction.atomic():
        task = KpiTaskModel.objects.select_for_update().filter(id=task_id).first()
        if task is None:
            return _error("KPI task not found", "not_found", 404)
        action = "self_score" if stage == "self" else "manager_score"
        if action not in _actions(user, permissions, task):
            return _error("Invalid KPI score transition or permission", "permission_denied", 403)
        old_status = task.status
        if stage == "self":
            task.self_score = score
            task.status = "manager_review"
            changed_fields = ["self_score", "status", "comments"]
        else:
            task.manager_score = score
            task.manager_scored_by_id = user.id
            task.status = "senior_review"
            changed_fields = ["manager_score", "manager_scored_by", "status", "comments"]
        task.comments = {**task.comments, stage: comments}
        task.save(update_fields=changed_fields)
        _audit(request, task, f"kpi.{stage}_scored", old_data={"status": old_status},
               new_data={"status": task.status, "score": str(score), "comments": comments})
        return JsonResponse({"id": task.id, "status": task.status})


@csrf_exempt
@login_required_domain
def kpi_task_review_view(request, task_id):
    if request.method != "POST":
        return _error("Method not allowed", "method_not_allowed", 405)
    try:
        body = _body(request)
        decision = body.get("decision")
        if decision not in ("approve", "return"):
            raise ValueError("decision must be approve or return")
        comments = _comments(body)
        if decision == "return" and not any(comments.values()):
            raise ValueError("A return reason is required")
    except ValueError as exc:
        return _error(str(exc))
    user = request.user_entity
    with transaction.atomic():
        task = KpiTaskModel.objects.select_for_update().filter(id=task_id).first()
        if task is None:
            return _error("KPI task not found", "not_found", 404)
        if "review" not in _actions(user, _permissions(user.id), task):
            return _error("Independent senior review is required", "permission_denied", 403)
        task.comments = {**task.comments, "review": comments}
        task.status = "confirmed" if decision == "approve" else "manager_review"
        task.final_score = task.manager_score if decision == "approve" else None
        task.reviewed_by_id = user.id if decision == "approve" else None
        task.reviewed_at = timezone.now() if decision == "approve" else None
        task.save(update_fields=["comments", "status", "final_score", "reviewed_by", "reviewed_at"])
        _audit(request, task, f"kpi.review_{decision}", old_data={"status": "senior_review"},
               new_data={"status": task.status, "comments": comments})
        return JsonResponse({"id": task.id, "status": task.status})


@csrf_exempt
@login_required_domain
def kpi_task_acknowledge_view(request, task_id):
    """Owner-only POST; retries keep the original timestamp and single audit event."""
    if request.method != "POST":
        return _error("Method not allowed", "method_not_allowed", 405)
    if not ({"kpi.read", "kpi.manage"} & _permissions(request.user_entity.id)):
        return _error("Permission denied", "permission_denied", 403)
    with transaction.atomic():
        task = KpiTaskModel.objects.select_for_update().filter(id=task_id).first()
        if task is None:
            return _error("KPI task not found", "not_found", 404)
        if task.employee.user_id != request.user_entity.id:
            return _error("Only the assessed employee may acknowledge the result", "permission_denied", 403)
        if task.status != "confirmed":
            return _error("Only confirmed KPI results may be acknowledged", "invalid_transition", 409)
        if task.acknowledged_at is None:
            task.acknowledged_at = timezone.now()
            task.save(update_fields=["acknowledged_at"])
            _audit(request, task, "kpi.acknowledged", old_data={"acknowledged_at": None},
                   new_data={"acknowledged_at": task.acknowledged_at.isoformat(), "final_score": str(task.final_score)})
        return JsonResponse({"id": task.id, "status": task.status, "acknowledged_at": task.acknowledged_at.isoformat()})


@csrf_exempt
@login_required_domain
def kpi_task_archive_view(request, task_id):
    if request.method != "POST":
        return _error("Method not allowed", "method_not_allowed", 405)
    user = request.user_entity
    with transaction.atomic():
        task = KpiTaskModel.objects.select_for_update().filter(id=task_id).first()
        if task is None:
            return _error("KPI task not found", "not_found", 404)
        if not _can_manage(user, _permissions(user.id), task.employee):
            return _error("Permission denied", "permission_denied", 403)
        if task.status != "confirmed" or task.acknowledged_at is None:
            return _error("Only acknowledged results may be archived", "invalid_transition", 409)
        if task.archived_at is None:
            task.archived_at = timezone.now()
            task.save(update_fields=["archived_at"])
            _audit(request, task, "kpi.archived", new_data={"archived_at": task.archived_at.isoformat()})
        return JsonResponse({"id": task.id, "status": task.status, "archived_at": task.archived_at.isoformat()})
