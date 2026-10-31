from backend.application.finance_periods import finance_transaction, require_open_date
"""Explicit same-currency debt corrections for posted supplier returns.

The posted correction is append-only. Neither historical payments nor source
documents change, and a correction never closes the unresolved finance review.
"""
import re
from datetime import date
from decimal import Decimal
from uuid import UUID

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from backend.domain.exceptions import ValidationException
from backend.infrastructure.persistence.models import (
    FinancePayableModel, FinancePeriodModel, OperationLogModel,
    SupplierReturnCorrectionModel, SupplierReturnFinanceReviewModel,
    SupplierStatementModel,
)
from backend.presentation.api.platform_views import _permissions
from backend.presentation.api.utils import parse_json_body
from backend.presentation.middlewares import login_required_domain


class CorrectionError(Exception):
    def __init__(self, message: str, code: str = "invalid_input", status: int = 400) -> None:
        self.message, self.code, self.status = message, code, status


def error(message: str, code: str = "invalid_input", status: int = 400) -> JsonResponse:
    return JsonResponse({"error": message, "code": code}, status=status)


def positive_id(value: object) -> int:
    if type(value) is not int or not 0 < value <= 9223372036854775807:
        raise CorrectionError("A positive integer payable_id is required")
    return value


def page_value(request: HttpRequest, key: str, default: int, maximum: int) -> int:
    value = request.GET.get(key, str(default))
    if not re.fullmatch(r"[0-9]{1,10}", value):
        raise CorrectionError(f"Invalid {key}")
    result = int(value)
    if result > maximum or (key.endswith("limit") and result == 0):
        raise CorrectionError(f"Invalid {key}")
    return result


def correction_payload(request: HttpRequest) -> dict:
    body = parse_json_body(request)
    fields = {"request_id", "payable_id", "amount", "currency", "posting_date", "document_no", "reason"}
    if set(body) != fields:
        raise CorrectionError("Exactly request_id, payable_id, amount, currency, posting_date, document_no and reason are required")
    positive_id(body["payable_id"])
    if not isinstance(body["request_id"], str):
        raise CorrectionError("A UUID request_id is required")
    try:
        request_id = UUID(body["request_id"])
    except ValueError:
        raise CorrectionError("A UUID request_id is required") from None
    # Decimal strings forbid floats, nonfinite values, exponents, rounding and
    # database overflow. Positivity is checked separately after exact parsing.
    if not isinstance(body["amount"], str) or not re.fullmatch(r"[0-9]{1,14}(?:\.[0-9]{1,2})?", body["amount"]):
        raise CorrectionError("amount must be a positive decimal string with at most two decimal places")
    amount = Decimal(body["amount"])
    if amount <= 0:
        raise CorrectionError("amount must be positive")
    if not isinstance(body["currency"], str) or not re.fullmatch(r"[A-Z]{3}", body["currency"]):
        raise CorrectionError("An uppercase three-letter currency is required")
    if not isinstance(body["posting_date"], str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", body["posting_date"]):
        raise CorrectionError("posting_date must be YYYY-MM-DD")
    try:
        posting_date = date.fromisoformat(body["posting_date"])
    except ValueError:
        raise CorrectionError("Invalid posting_date") from None
    for key, maximum in (("document_no", 128), ("reason", 4000)):
        value = body[key]
        if not isinstance(value, str) or not value.strip() or len(value) > maximum or "\x00" in value:
            raise CorrectionError(f"A nonempty {key} of at most {maximum} characters is required")
    return {**body, "request_id": request_id, "amount": amount, "posting_date": posting_date,
            "document_no": body["document_no"].strip(), "reason": body["reason"].strip()}


def serialize_correction(correction: SupplierReturnCorrectionModel) -> dict:
    return {
        "id": correction.id, "review_id": correction.review_id,
        "return_id": correction.review.supplier_return_id,
        "payable_id": correction.payable_id, "request_id": str(correction.request_id),
        "amount": format(correction.amount, ".2f"), "currency": correction.currency,
        "posting_date": correction.posting_date.isoformat(),
        "document_no": correction.document_no, "reason": correction.reason,
        "outstanding_before": format(correction.outstanding_before, ".2f"),
        "outstanding_after": format(correction.outstanding_after, ".2f"),
        "confirmed_by_name": correction.confirmed_by.full_name,
        "confirmed_at": correction.confirmed_at.isoformat(),
    }


def eligible_payables(review: SupplierReturnFinanceReviewModel):
    order = review.supplier_return.receipt.purchase_order
    return FinancePayableModel.objects.filter(
        supplier_id=order.supplier_id, purchase_order_id=order.id,
        status__in=("open", "partially_paid"), outstanding_amount__gt=0,
    ).order_by("id")


def list_corrections(request: HttpRequest, review: SupplierReturnFinanceReviewModel, permissions: set[str]) -> JsonResponse:
    limit = page_value(request, "limit", 20, 100)
    offset = page_value(request, "offset", 0, 1000000000)
    payable_limit = page_value(request, "payable_limit", 20, 100)
    payable_offset = page_value(request, "payable_offset", 0, 1000000000)
    payables = eligible_payables(review)
    query = request.GET.get("q", "").strip()
    if len(query) > 128:
        raise CorrectionError("q must be at most 128 characters")
    if query:
        matching_statements = SupplierStatementModel.objects.filter(statement_no__icontains=query).values("id")
        condition = Q(source_type="supplier_statement", source_id__in=matching_statements)
        if re.fullmatch(r"[0-9]{1,18}", query):
            condition |= Q(id=int(query))
        payables = payables.filter(condition)
    corrections = review.corrections.select_related("review", "confirmed_by").order_by("-id")
    return JsonResponse({
        "review_id": review.id, "review_status": review.status,
        "corrections": [serialize_correction(x) for x in corrections[offset:offset + limit]],
        "correction_count": corrections.count(),
        "payables": [{
            "id": p.id, "supplier_id": p.supplier_id, "purchase_order_id": p.purchase_order_id,
            "source_type": p.source_type, "source_id": p.source_id,
            "amount": format(p.amount, ".2f"), "outstanding_amount": format(p.outstanding_amount, ".2f"),
            "currency": p.currency, "status": p.status,
        } for p in payables[payable_offset:payable_offset + payable_limit]],
        "payable_count": payables.count(), "limit": limit, "offset": offset,
        "payable_limit": payable_limit, "payable_offset": payable_offset,
        "can_confirm": "finance.payable.manage" in permissions,
    })


def existing_request(payload: dict, review_id: int) -> JsonResponse | None:
    existing = SupplierReturnCorrectionModel.objects.select_related("review", "confirmed_by").filter(
        request_id=payload["request_id"]).first()
    if existing is not None:
        if existing.review_id != review_id or any(getattr(existing, key) != value for key, value in payload.items()):
            raise CorrectionError("request_id was already used with different correction data", "idempotency_conflict", 409)
        return JsonResponse(serialize_correction(existing))
    return None


def confirm_correction(request: HttpRequest, review_id: int) -> JsonResponse:
    payload = correction_payload(request)
    with transaction.atomic():
        review = SupplierReturnFinanceReviewModel.objects.select_for_update().filter(id=review_id).first()
        if review is None:
            raise CorrectionError("Finance review not found", "not_found", 404)
        if review.supplier_return.status != "posted":
            raise CorrectionError("A posted supplier return is required", "invalid_return", 409)
        repeated = existing_request(payload, review.id)
        if repeated is not None:
            return repeated
        order = review.supplier_return.receipt.purchase_order
        payable = FinancePayableModel.objects.select_for_update().filter(id=payload["payable_id"]).first()
        if (payable is None or payable.supplier_id != order.supplier_id or payable.purchase_order_id != order.id
                or payable.status not in ("open", "partially_paid")):
            raise CorrectionError("An open payable for the same supplier and purchase order is required", "invalid_payable", 409)
        if payable.currency != payload["currency"]:
            raise CorrectionError("Correction currency must match payable currency", "currency_mismatch", 409)
        if payload["amount"] > payable.outstanding_amount:
            raise CorrectionError("Correction exceeds current outstanding debt", "insufficient_outstanding", 409)
        posted_on = payload["posting_date"]
        require_open_date(posted_on)
        before = payable.outstanding_amount
        after = before - payload["amount"]
        correction = SupplierReturnCorrectionModel.objects.create(
            review=review, outstanding_before=before, outstanding_after=after,
            confirmed_by_id=request.user_entity.id, **payload)
        payable.outstanding_amount = after
        if after == 0:
            payable.status = "settled_by_adjustment"
        payable.save(update_fields=["outstanding_amount", "status"])
        OperationLogModel.objects.create(
            actor_id=request.user_entity.id, action="finance.supplier_return_correction",
            business_type="supplier_return_correction", business_id=correction.id,
            old_data={"payable_id": payable.id, "outstanding_amount": format(before, ".2f")},
            new_data=serialize_correction(correction), ip_address=request.META.get("REMOTE_ADDR", ""),
        )
    return JsonResponse(serialize_correction(correction), status=201)


@csrf_exempt
@login_required_domain
@finance_transaction
def supplier_return_corrections_view(request: HttpRequest, review_id: int) -> JsonResponse:
    """List evidence or atomically confirm one immutable manual correction."""
    if request.method not in ("GET", "POST"):
        return error("Method not allowed", "method_not_allowed", 405)
    permissions = _permissions(request.user_entity.id)
    required = "finance.payable.read" if request.method == "GET" else "finance.payable.manage"
    if required not in permissions:
        return error("Permission denied", "permission_denied", 403)
    try:
        if request.method == "POST":
            try:
                response = confirm_correction(request, review_id)
            except IntegrityError:
                # The unique UUID is global. Two different reviews may race for
                # it without sharing a review lock. Re-read after atomic rollback.
                response = existing_request(correction_payload(request), review_id)
                if response is None:
                    raise
        else:
            review = SupplierReturnFinanceReviewModel.objects.select_related(
                "supplier_return__receipt__purchase_order").filter(id=review_id, supplier_return__status="posted").first()
            if review is None:
                raise CorrectionError("Finance review not found", "not_found", 404)
            response = list_corrections(request, review, permissions)
    except CorrectionError as exc:
        return error(exc.message, exc.code, exc.status)
    except ValidationException as exc:
        return error(exc.message)
    response["Cache-Control"] = "private, no-store"
    return response
