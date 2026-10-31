"""Permissioned, monotonic financial-month closure and year inspection."""
import re

from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from backend.application.finance_periods import lock_finance_period
from backend.infrastructure.persistence.models import FinancePeriodModel, OperationLogModel
from backend.presentation.api.platform_views import _permissions
from backend.presentation.api.utils import parse_json_body
from backend.presentation.middlewares import login_required_domain


def _error(message: str, code: str, status: int) -> JsonResponse:
    return JsonResponse({"error": message, "code": code}, status=status)


def _period_data(year: int, month: int, period: FinancePeriodModel | None = None) -> dict:
    return {"year": year, "month": month, "is_closed": bool(period and period.is_closed),
            "closed_by_name": period.closed_by.full_name if period and period.closed_by_id else None,
            "closed_at": period.closed_at.isoformat() if period and period.closed_at else None,
            "close_reason": period.close_reason if period else ""}


@login_required_domain
def finance_periods_view(request):
    if request.method != "GET":
        return _error("Method not allowed", "method_not_allowed", 405)
    permissions = _permissions(request.user_entity.id)
    if not {"finance.payable.read", "finance.period.close"}.intersection(permissions):
        return _error("Permission denied", "permission_denied", 403)
    year = request.GET.get("year", "")
    if not re.fullmatch(r"[0-9]{4}", year) or not 1 <= int(year) <= 9999:
        return _error("year must be four digits between 0001 and 9999", "invalid_input", 400)
    year = int(year)
    periods = {p.month: p for p in FinancePeriodModel.objects.select_related("closed_by").filter(year=year)}
    response = JsonResponse({"year": year, "items": [_period_data(year, month, periods.get(month)) for month in range(1, 13)],
                             "can_close": "finance.period.close" in permissions})
    response["Cache-Control"] = "private, no-store"
    return response


@csrf_exempt
@login_required_domain
def close_finance_period_view(request, year: int, month: int):
    if request.method != "POST":
        return _error("Method not allowed", "method_not_allowed", 405)
    if "finance.period.close" not in _permissions(request.user_entity.id):
        return _error("Permission denied", "permission_denied", 403)
    if not 1 <= year <= 9999 or not 1 <= month <= 12:
        return _error("Invalid year/month", "invalid_input", 400)
    body = parse_json_body(request)
    reason = body.get("reason")
    if set(body) != {"reason"} or not isinstance(reason, str) or not reason.strip() or len(reason) > 4000 or "\x00" in reason:
        return _error("A nonempty reason of at most 4000 characters is required", "invalid_input", 400)
    with transaction.atomic():
        period = lock_finance_period(year, month)
        if not period.is_closed:
            period.is_closed = True
            period.closed_by_id = request.user_entity.id
            period.closed_at = timezone.now()
            period.close_reason = reason.strip()
            period.save(update_fields=["is_closed", "closed_by", "closed_at", "close_reason"])
            OperationLogModel.objects.create(actor_id=request.user_entity.id, action="finance.period_closed",
                business_type="finance_period", business_id=period.id,
                old_data={"year": year, "month": month, "is_closed": False},
                new_data={"year": year, "month": month, "is_closed": True, "close_reason": period.close_reason},
                ip_address=request.META.get("REMOTE_ADDR", ""))
        response = JsonResponse(_period_data(year, month, period))
    response["Cache-Control"] = "private, no-store"
    return response
