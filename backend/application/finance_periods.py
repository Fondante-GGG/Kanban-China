"""Shared transaction-scoped finance month lock for all monetary writers.

Callers must keep the transaction open until their document/audit writes commit.
The same row is acquired by period closure, so a successful close cannot race
with an unguarded in-flight writer. Missing rows are implicit open periods.
"""
from datetime import date, datetime
from zoneinfo import ZoneInfo
from functools import wraps

from django.db import connection
from django.utils import timezone

from backend.infrastructure.persistence.models import FinancePeriodModel


class ClosedFinancePeriod(Exception):
    """A guarded monetary operation targets an already closed month."""


def business_today() -> date:
    """Kyrgyz business date; keep stored timestamps and global settings unchanged."""
    return business_date(timezone.now())


def lock_finance_period(year: int, month: int) -> FinancePeriodModel:
    if not connection.in_atomic_block:
        raise RuntimeError("Finance period locks require an active transaction")
    if type(year) is not int or type(month) is not int or not 1 <= year <= 9999 or not 1 <= month <= 12:
        raise ValueError("Invalid finance year/month")
    period, _ = FinancePeriodModel.objects.select_for_update().get_or_create(year=year, month=month)
    return period


def require_open_period(year: int, month: int) -> FinancePeriodModel:
    period = lock_finance_period(year, month)
    if period.is_closed:
        raise ClosedFinancePeriod("Financial period is closed")
    return period


def require_open_date(value: date) -> FinancePeriodModel:
    return require_open_period(value.year, value.month)


def business_date(timestamp: datetime) -> date:
    return timezone.localtime(timestamp, ZoneInfo("Asia/Bishkek")).date()


def finance_transaction(view):
    """Rollback the complete write on a closed month and return the API conflict.

    Kept here to share transaction semantics; response import is lazy so plain
    locking helpers remain usable by application code without HTTP imports.
    """
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return view(request, *args, **kwargs)
        from django.db import transaction
        from django.http import JsonResponse
        try:
            with transaction.atomic():
                return view(request, *args, **kwargs)
        except ClosedFinancePeriod:
            return JsonResponse({"error": "Financial period is closed", "code": "period_closed"}, status=409)
    return wrapped
