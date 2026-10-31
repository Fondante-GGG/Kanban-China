from backend.tests.payment_request_fixtures import approved_payment_fixture
"""Debt-only return corrections: exact money, authority and atomic append log."""
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from threading import Barrier
from unittest import skipUnless
from unittest.mock import patch
from uuid import uuid4

from django.db import connection, connections
from django.test import Client, TestCase, TransactionTestCase
from django.utils import timezone

from backend.tests import test_supplier_returns as return_tests
from backend.infrastructure.persistence.models import (
    FinanceAccountModel, FinancePayableModel, FinancePaymentModel, FinancePeriodModel,
    OperationLogModel, PurchaseOrderModel, SupplierModel, SupplierReturnCorrectionModel,
    SupplierReturnFinanceReviewModel, SupplierReturnModel, SystemPermissionModel,
)


class SupplierReturnCorrectionTests(TestCase):
    headers = return_tests.SupplierReturnTests.headers

    def setUp(self):
        return_tests.SupplierReturnTests.setUp(self)
        self.doc = SupplierReturnModel.objects.create(
            return_no="FIN-RETURN", receipt=self.receipt, warehouse=self.wh,
            reason_type="other", reason="Confirmed return", status="posted",
            created_by=self.sender, posted_by=self.director, posted_at=timezone.now())
        self.review = SupplierReturnFinanceReviewModel.objects.create(supplier_return=self.doc)
        self.path = f"/api/finance/supplier-returns/{self.review.id}/corrections"
        self.account = FinanceAccountModel.objects.create(name="Bank", currency="CNY", balance="1000")

    def payload(self, **changes):
        body = {"request_id": str(uuid4()), "payable_id": self.payable.id,
                "amount": "100.25", "currency": "CNY", "posting_date": date.today().isoformat(),
                "document_no": "CN-1", "reason": "Amount confirmed by accountant"}
        return {**body, **changes}

    def post(self, body=None, user=None, path=None):
        return self.client.post(path or self.path, json.dumps(body or self.payload()),
                                content_type="application/json", **self.headers(user or self.director))

    def test_append_only_multiple_corrections_leave_review_pending_and_sources_immutable(self):
        self.payable.outstanding_amount = Decimal("600.00")
        self.payable.status = "partially_paid"
        self.payable.save()
        payment = FinancePaymentModel.objects.create(payable=self.payable, account=self.account,
            amount="200", payment_date=date.today(), transaction_no="PAID-1", created_by=self.director)
        first = self.post(self.payload(amount="100.25"))
        self.assertEqual(first.status_code, 201, first.content)
        self.assertEqual(first.json()["outstanding_before"], "600.00")
        self.assertEqual(first.json()["outstanding_after"], "499.75")
        self.assertEqual(self.post(self.payload(amount="499.75")).status_code, 201)
        self.payable.refresh_from_db(); self.account.refresh_from_db(); payment.refresh_from_db()
        self.review.refresh_from_db(); self.source.refresh_from_db(); self.po_item.refresh_from_db()
        self.assertEqual(self.payable.outstanding_amount, Decimal("0.00"))
        self.assertEqual(self.payable.status, "settled_by_adjustment")
        self.assertEqual(self.payable.amount, Decimal("800.00"))
        self.assertEqual(self.account.balance, Decimal("1000.00"))
        self.assertEqual(payment.amount, Decimal("200.00"))
        self.assertEqual(self.review.status, "pending")
        self.assertEqual(self.source.qty, 10)
        self.assertEqual(self.po_item.received_qty, 10)
        self.assertEqual(SupplierReturnCorrectionModel.objects.count(), 2)
        self.assertEqual(OperationLogModel.objects.filter(action="finance.supplier_return_correction").count(), 2)
        correction = SupplierReturnCorrectionModel.objects.first()
        with self.assertRaises(RuntimeError):
            correction.save()
        with self.assertRaises(RuntimeError):
            correction.delete()
        with self.assertRaises(RuntimeError):
            SupplierReturnCorrectionModel.objects.filter(id=correction.id).update(reason="overwrite")
        with self.assertRaises(RuntimeError):
            SupplierReturnCorrectionModel.objects.filter(id=correction.id).delete()
        self.assertEqual(self.client.patch(self.path, "{}", content_type="application/json", **self.headers(self.director)).status_code, 405)
        self.assertEqual(self.client.delete(self.path, **self.headers(self.director)).status_code, 405)

    def test_idempotent_same_payload_even_after_debt_settled_and_period_closed(self):
        payload = self.payload(amount="800.00")
        first = self.post(payload)
        self.assertEqual(first.status_code, 201)
        FinancePeriodModel.objects.filter(year=date.today().year, month=date.today().month).update(is_closed=True)
        repeated = self.post(payload)
        self.assertEqual(repeated.status_code, 200, repeated.content)
        self.assertEqual(repeated.json(), first.json())
        self.assertEqual(self.post({**payload, "amount": "799.99"}).json()["code"], "idempotency_conflict")
        self.assertEqual(SupplierReturnCorrectionModel.objects.count(), 1)

    def test_nonbinary_cents_and_normalized_decimal_retry(self):
        self.payable.outstanding_amount = Decimal("0.30")
        self.payable.save(update_fields=["outstanding_amount"])
        payload = self.payload(amount="0.1")
        result = self.post(payload)
        self.assertEqual(result.status_code, 201, result.content)
        self.assertEqual(result.json()["outstanding_after"], "0.20")
        repeated = self.post({**payload, "amount": "0.10"})
        self.assertEqual(repeated.status_code, 200)
        self.assertEqual(repeated.json(), result.json())

    def test_payment_after_correction_keeps_mixed_settlement_distinct_from_paid(self):
        self.assertEqual(self.post().status_code, 201)
        payment_body = {"amount": "699.75", "account_id": self.account.id,
            "payment_date": date.today().isoformat(), "transaction_no": "AFTER-CORRECTION"}
        payment_body.update(approved_payment_fixture(self.payable,self.account,self.director,"699.75",date.today()))
        with patch("backend.application.payment_requests.PrivateMediaStorage.exists",return_value=True):
            result = self.client.post(f"/api/finance/payables/{self.payable.id}/payments",
            json.dumps(payment_body), content_type="application/json", **self.headers(self.director))
        self.assertEqual(result.status_code, 201, result.content)
        self.assertEqual(result.json()["payable"]["status"], "settled_by_adjustment")
        self.payable.refresh_from_db(); self.account.refresh_from_db()
        self.assertEqual(self.payable.amount, Decimal("800.00"))
        self.assertEqual(self.payable.outstanding_amount, Decimal("0.00"))
        self.assertEqual(self.account.balance, Decimal("300.25"))
        self.assertEqual(self.payable.payments.get().amount, Decimal("699.75"))
        # A payable settled entirely by money retains the existing paid status.
        pure = FinancePayableModel.objects.create(supplier=self.supplier, purchase_order=self.order,
            source_type="pure-payment", source_id=2, amount="10.00", outstanding_amount="10.00", currency="CNY")
        payment_body.update(approved_payment_fixture(pure,self.account,self.director,"10.00",date.today()))
        with patch("backend.application.payment_requests.PrivateMediaStorage.exists",return_value=True):
            result = self.client.post(f"/api/finance/payables/{pure.id}/payments",
            json.dumps({**payment_body, "amount": "10.00", "transaction_no": "PURE-PAYMENT"}),
            content_type="application/json", **self.headers(self.director))
        self.assertEqual(result.status_code, 201, result.content)
        self.assertEqual(result.json()["payable"]["status"], "paid")

    def test_global_uuid_cannot_be_reused_for_another_return(self):
        payload = self.payload()
        self.assertEqual(self.post(payload).status_code, 201)
        other = SupplierReturnModel.objects.create(return_no="FIN-OTHER", receipt=self.receipt,
            warehouse=self.wh, reason_type="other", reason="Other", status="posted", created_by=self.sender)
        review = SupplierReturnFinanceReviewModel.objects.create(supplier_return=other)
        result = self.post(payload, path=f"/api/finance/supplier-returns/{review.id}/corrections")
        self.assertEqual(result.status_code, 409)
        self.assertEqual(result.json()["code"], "idempotency_conflict")

    def test_closed_posting_period_blocks_but_closed_source_period_is_not_rewritten(self):
        FinancePeriodModel.objects.create(year=2001, month=1, is_closed=True)
        blocked = self.post(self.payload(posting_date="2001-01-20"))
        self.assertEqual(blocked.status_code, 409)
        self.assertEqual(blocked.json()["code"], "period_closed")
        self.doc.posted_at = timezone.datetime(2001, 1, 5, tzinfo=timezone.get_current_timezone())
        self.doc.save(update_fields=["posted_at"])
        self.assertEqual(self.post().status_code, 201)
        self.assertTrue(FinancePeriodModel.objects.get(year=2001, month=1).is_closed)

    def test_rollback_on_audit_failure_preserves_debt_and_no_document(self):
        with patch("backend.presentation.api.finance_return_views.OperationLogModel.objects.create", side_effect=RuntimeError("audit failed")):
            self.assertEqual(self.post().status_code, 500)
        self.payable.refresh_from_db()
        self.assertEqual(self.payable.outstanding_amount, Decimal("800.00"))
        self.assertFalse(SupplierReturnCorrectionModel.objects.exists())
        self.assertFalse(FinancePeriodModel.objects.exists())

    def test_strict_money_ids_dates_and_text_reject_without_side_effects(self):
        invalid = [{"amount": x} for x in ("NaN", "Infinity", "-1", "0", "1.001", "1e2", "100000000000000", 1.25, True, None)]
        invalid += [{"payable_id": x} for x in (True, "1", -1, 1.5, None, [], 2**64)]
        invalid += [{"posting_date": x} for x in ("20260101", "2026-02-30", "2026-W01-1", True)]
        invalid += [{"currency": "cny"}, {"reason": " "}, {"reason": "a" * 4001}, {"document_no": "x" * 129}, {"document_no": "bad\x00"}, {"request_id": "invalid"}, {"extra": 1}]
        for changes in invalid:
            with self.subTest(changes=changes):
                result = self.post(self.payload(**changes))
                self.assertEqual(result.status_code, 400, result.content)
                self.assertEqual(result.json()["code"], "invalid_input")
        for raw in ("{", "[]", '"text"'):
            self.assertEqual(self.client.post(self.path, raw, content_type="application/json", **self.headers(self.director)).status_code, 400)
        self.assertFalse(SupplierReturnCorrectionModel.objects.exists())
        self.payable.refresh_from_db(); self.assertEqual(self.payable.outstanding_amount, Decimal("800.00"))

    def test_matching_supplier_order_currency_and_outstanding_are_authoritative(self):
        self.assertEqual(self.post(self.payload(amount="800.01")).json()["code"], "insufficient_outstanding")
        self.assertEqual(self.post(self.payload(currency="KGS")).json()["code"], "currency_mismatch")
        supplier = SupplierModel.objects.create(name_ru="Other", created_by=self.director)
        order = PurchaseOrderModel.objects.create(po_no="OTHER-FIN", supplier=self.supplier,
            order_date=date.today(), created_by=self.director)
        for changes in ({"supplier": supplier}, {"purchase_order": order}, {"status": "paid"}, {"status": "cancelled"}):
            with self.subTest(changes=changes):
                wrong = FinancePayableModel.objects.create(supplier=changes.get("supplier", self.supplier),
                    purchase_order=changes.get("purchase_order", self.order), source_type="test-other",
                    source_id=FinancePayableModel.objects.count() + 1, amount="100", outstanding_amount="100",
                    currency="CNY", status=changes.get("status", "open"))
                self.assertEqual(self.post(self.payload(payable_id=wrong.id)).json()["code"], "invalid_payable")
        self.doc.status = "draft"; self.doc.save(update_fields=["status"])
        self.assertEqual(self.post().json()["code"], "invalid_return")

    def test_partial_correction_preserves_open_or_partially_paid(self):
        self.assertEqual(self.post().status_code, 201)
        self.payable.refresh_from_db(); self.assertEqual(self.payable.status, "open")
        self.payable.status = "partially_paid"; self.payable.save(update_fields=["status"])
        self.assertEqual(self.post().status_code, 201)
        self.payable.refresh_from_db(); self.assertEqual(self.payable.status, "partially_paid")

    def test_read_only_finance_permissions_and_pagination(self):
        self.assertEqual(self.client.get(self.path, **self.headers()).status_code, 403)
        self.assertEqual(self.post(user=self.sender).status_code, 403)
        read, _ = SystemPermissionModel.objects.get_or_create(code="finance.payable.read", defaults={"name": "Read finance"})
        self.role.permissions.add(read)
        read_result = self.client.get(self.path, **self.headers())
        self.assertEqual(read_result.status_code, 200)
        self.assertFalse(read_result.json()["can_confirm"])
        self.assertEqual(self.post(user=self.sender).status_code, 403)
        manage, _ = SystemPermissionModel.objects.get_or_create(code="finance.payable.manage", defaults={"name": "Manage finance"})
        self.role.permissions.add(manage)
        # Current finance permissions are sufficient; no warehouse grants used.
        self.assertEqual(self.post(user=self.sender).status_code, 201)
        data = self.client.get(self.path + "?limit=1&offset=0&payable_limit=1&payable_offset=1", **self.headers()).json()
        self.assertEqual(len(data["corrections"]), 1)
        self.assertEqual(data["payables"], [])
        self.assertEqual(data["correction_count"], 1)
        self.assertEqual(data["payable_count"], 1)
        self.assertEqual(data["review_status"], "pending")
        for query in ("limit=101", "offset=-1", "payable_limit=0", "payable_offset=1e2", "q=" + "a"*129):
            self.assertEqual(self.client.get(self.path + "?" + query, **self.headers()).status_code, 400)
        self.assertEqual(self.client.get("/api/finance/supplier-returns/999999/corrections", **self.headers(self.director)).status_code, 404)


@skipUnless(connection.vendor == "postgresql", "Requires real PostgreSQL row locks")
class SupplierReturnCorrectionConcurrencyTests(TransactionTestCase):
    headers = return_tests.SupplierReturnTests.headers
    payload = SupplierReturnCorrectionTests.payload

    def setUp(self):
        SupplierReturnCorrectionTests.setUp(self)

    def run_parallel(self, calls):
        barrier = Barrier(len(calls))
        headers = self.headers(self.director)
        def worker(call):
            connections.close_all()
            try:
                barrier.wait(timeout=15)
                path, body = call
                return Client().post(path, json.dumps(body), content_type="application/json", **headers).status_code
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=len(calls)) as pool:
            return list(pool.map(worker, calls))

    def test_parallel_corrections_cannot_overdraw_debt(self):
        results = self.run_parallel([(self.path, self.payload(amount="500.00")), (self.path, self.payload(amount="500.00"))])
        self.assertCountEqual(results, [201, 409])
        self.payable.refresh_from_db()
        self.assertEqual(self.payable.outstanding_amount, Decimal("300.00"))
        self.assertEqual(SupplierReturnCorrectionModel.objects.count(), 1)

    def test_payment_and_correction_share_payable_lock(self):
        payment = {"amount": "500.00", "account_id": self.account.id,
                   "payment_date": date.today().isoformat(), "transaction_no": "CONCURRENT"}
        payment.update(approved_payment_fixture(self.payable,self.account,self.director,"500.00",date.today()))
        with patch("backend.application.payment_requests.PrivateMediaStorage.exists",return_value=True):
            results = self.run_parallel([(self.path, self.payload(amount="500.00")),
                (f"/api/finance/payables/{self.payable.id}/payments", payment)])
        self.assertEqual(results.count(201), 1)
        self.assertIn(409 if results[0] == 409 else 400, results)
        self.payable.refresh_from_db()
        self.assertEqual(self.payable.outstanding_amount, Decimal("300.00"))
        self.assertEqual(SupplierReturnCorrectionModel.objects.count() + FinancePaymentModel.objects.count(), 1)
