from backend.tests.payment_request_fixtures import approved_payment_fixture
"""Period closure permissions, monotonicity, rollback and writer serialization."""
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from datetime import date, datetime, timezone as datetime_timezone
from decimal import Decimal
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory
from django.contrib import admin
from backend.infrastructure.persistence.models import ExpenseModel, ExpenseAttachmentModel, ExpenseActivityLogModel, ReimbursementPaymentModel, SupplierModel, PurchaseOrderModel, SupplierStatementModel, FinancePayableModel, FinanceAccountModel, FinancePaymentModel, EmployeeModel, MonthlyTimesheetModel, FinanceSalaryModel
from backend.infrastructure.persistence import admin as financial_admin
from backend.application.finance_periods import business_date
from unittest import skipUnless
from unittest.mock import patch

from django.db import connection, connections, transaction
from django.test import TestCase, TransactionTestCase

from backend.application.finance_periods import ClosedFinancePeriod, require_open_period
from backend.tests import test_finance_flow as fixtures
from backend.infrastructure.persistence.models import (
    FinancePeriodModel, OperationLogModel, SystemPermissionModel, SystemRoleModel, UserSystemRoleModel, UserModel,
)
from backend.infrastructure.di.container import container
from backend.domain.entities import User


class FinancePeriodTests(TestCase):
    def setUp(self):
        fixtures.FinanceFlowTests.setUp(self)
        self.reader = UserModel.objects.create_user(email="period-reader@test.local", password="password123",
            full_name="Period reader", role="employee", department=self.dept)
        self.role = SystemRoleModel.objects.create(code="period-reader", name="Period reader")
        UserSystemRoleModel.objects.create(user=self.reader, role=self.role)
        permission, _ = SystemPermissionModel.objects.get_or_create(code="finance.payable.read", defaults={"name": "Read payables"})
        self.role.permissions.add(permission)
        entity = User(id=self.reader.id,email=self.reader.email,password_hash=self.reader.password,full_name=self.reader.full_name,role=self.reader.role,department_id=self.dept.id)
        self.reader_headers = {"HTTP_AUTHORIZATION": "Bearer " + container.jwt_service.generate_token(entity)}

    def close(self, year=2026, month=1, reason="Month reviewed", headers=None):
        return self.client.post(f"/api/finance/periods/{year}/{month}/close", json.dumps({"reason": reason}),
            content_type="application/json", **(headers or self.headers))

    def test_year_virtual_months_no_writes_and_permissions(self):
        response = self.client.get("/api/finance/periods?year=2026", **self.reader_headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["items"]), 12)
        self.assertFalse(response.json()["can_close"])
        self.assertFalse(FinancePeriodModel.objects.exists())
        self.assertEqual(self.close(headers=self.reader_headers).status_code, 403)
        self.role.permissions.clear()
        self.assertEqual(self.client.get("/api/finance/periods?year=2026", **self.reader_headers).status_code, 403)
        self.assertEqual(self.client.get("/api/finance/periods?year=2026").status_code, 401)

    def test_explicit_close_permission_without_read_can_inspect_and_close(self):
        self.role.permissions.clear()
        permission, _ = SystemPermissionModel.objects.get_or_create(code="finance.period.close", defaults={"name":"Close period"})
        self.role.permissions.add(permission)
        response = self.client.get("/api/finance/periods?year=2026", **self.reader_headers)
        self.assertTrue(response.json()["can_close"])
        self.assertEqual(self.close(headers=self.reader_headers).status_code, 200)

    def test_close_is_monotonic_and_repeat_preserves_evidence(self):
        first = self.close()
        self.assertEqual(first.status_code, 200)
        self.assertTrue(first.json()["is_closed"])
        second = self.close(reason="Different attempt")
        self.assertEqual(second.json(), first.json())
        self.assertEqual(OperationLogModel.objects.filter(action="finance.period_closed").count(), 1)
        period = FinancePeriodModel.objects.get(year=2026,month=1)
        self.assertEqual(period.close_reason,"Month reviewed")
        self.assertEqual(period.closed_by_id,self.user.id)
        self.assertIn("no-store",first["Cache-Control"])
        with transaction.atomic(), self.assertRaises(ClosedFinancePeriod):
            require_open_period(2026,1)

    def test_invalid_dates_payloads_and_methods(self):
        for year in ("", "0", "0000", "20260", "True", "2026.0"):
            self.assertEqual(self.client.get("/api/finance/periods", {"year":year}, **self.headers).status_code,400)
        for year,month in ((0,1),(10000,1),(2026,0),(2026,13)):
            self.assertEqual(self.close(year,month).status_code,400)
        for reason in ("", "  ", True, 1, "x"*4001, "nul\x00"):
            self.assertEqual(self.close(reason=reason).status_code,400)
        self.assertEqual(self.client.post("/api/finance/periods", **self.headers).status_code,405)
        self.assertEqual(self.client.get("/api/finance/periods/2026/1/close", **self.headers).status_code,405)
        self.assertFalse(FinancePeriodModel.objects.exists())

    def test_audit_failure_rolls_back_new_and_existing_open_period(self):
        for existing in (False, True):
            if existing: FinancePeriodModel.objects.create(year=2026,month=1)
            with patch("backend.presentation.api.finance_period_views.OperationLogModel.objects.create",side_effect=RuntimeError("audit unavailable")):
                self.assertEqual(self.close().status_code,500)
            if existing: self.assertFalse(FinancePeriodModel.objects.get(year=2026,month=1).is_closed)
            else: self.assertFalse(FinancePeriodModel.objects.exists())
        self.assertFalse(OperationLogModel.objects.filter(action="finance.period_closed").exists())


class FinancePeriodWriterTests(FinancePeriodTests):
    # Inherit setup only, not the API test methods to avoid duplicate coverage.
    test_year_virtual_months_no_writes_and_permissions = None
    test_explicit_close_permission_without_read_can_inspect_and_close = None
    test_close_is_monotonic_and_repeat_preserves_evidence = None
    test_invalid_dates_payloads_and_methods = None
    test_audit_failure_rolls_back_new_and_existing_open_period = None

    def post(self, path, body):
        return self.client.post(path,json.dumps(body),content_type="application/json",**self.headers)

    def expense(self, status="draft"):
        return ExpenseModel.objects.create(purchase_date=date(2026,1,15),department=self.dept,category="Expense",
            amount="100.00",currency="KGS",payment_source="personal",payment_method="personal_card",status=status,created_by=self.user)

    def order(self):
        supplier=SupplierModel.objects.create(name_ru="Supplier",status="approved",created_by=self.user)
        return PurchaseOrderModel.objects.create(po_no="PERIOD-PO",supplier=supplier,order_date=date(2026,1,15),status="received",currency="KGS",created_by=self.user)

    def assert_closed(self,response):
        self.assertEqual(response.status_code,409,response.content)
        self.assertEqual(response.json()["code"],"period_closed")

    def test_closed_expense_create_edit_submit_and_attachment_are_blocked(self):
        expense=self.expense()
        self.close()
        payload={"purchase_date":"2026-01-16","category":"Blocked","amount":"10.00","payment_source":"personal","payment_method":"personal_card"}
        self.assert_closed(self.post("/api/expenses",payload))
        self.assertEqual(ExpenseModel.objects.count(),1)
        self.assert_closed(self.client.put(f"/api/expenses/{expense.id}",json.dumps({"amount":"200.00"}),content_type="application/json",**self.headers))
        self.assert_closed(self.post(f"/api/expenses/{expense.id}/status",{"status":"under_review"}))
        upload=SimpleUploadedFile("blocked.pdf",b"%PDF-test",content_type="application/pdf")
        self.assert_closed(self.client.post(f"/api/expenses/{expense.id}/attachments",{"file":upload},**self.headers))
        expense.refresh_from_db()
        self.assertEqual(expense.amount,Decimal("100.00"))
        self.assertEqual(expense.status,"draft")
        self.assertFalse(ExpenseAttachmentModel.objects.exists())
        self.assertFalse(ExpenseActivityLogModel.objects.exists())
        self.assertEqual(self.client.get(f"/api/expenses/{expense.id}",**self.headers).status_code,200)
        attachment=ExpenseAttachmentModel.objects.create(expense=expense,document_type="invoice",
            file="read-only-history.pdf",original_name="history.pdf",file_size=9,uploaded_by=self.user)
        from io import BytesIO
        storage=ExpenseAttachmentModel._meta.get_field("file").storage
        with patch.object(storage,"open",return_value=BytesIO(b"%PDF-test")):
            download=self.client.get(f"/api/expense-attachments/{attachment.id}/download",**self.headers)
            self.assertEqual(download.status_code,200)
            self.assertEqual(b"".join(download.streaming_content),b"%PDF-test")
            download.close()

    def test_current_reimbursement_can_pay_closed_source_but_closed_payment_date_cannot(self):
        expense=self.expense("approved")
        self.close()
        timestamp=datetime(2026,1,31,18,30,tzinfo=datetime_timezone.utc) # Feb1 Bishkek
        with patch("backend.presentation.api.expense_views.timezone.now",return_value=timestamp):
            self.assertEqual(self.post(f"/api/expenses/{expense.id}/payment",{"amount":"40.00"}).status_code,201)
            self.close(2026,2)
            self.assert_closed(self.post(f"/api/expenses/{expense.id}/payment",{"amount":"60.00"}))
        self.assertEqual(ReimbursementPaymentModel.objects.count(),1)
        self.assertEqual(ReimbursementPaymentModel.objects.get().paid_at,timestamp)
        expense.refresh_from_db()
        self.assertEqual(expense.amount,Decimal("100.00"))
        self.assertEqual(expense.purchase_date,date(2026,1,15))
        self.assertEqual(expense.status,"approved")
        self.assertEqual(business_date(timestamp),date(2026,2,1))
        self.assertEqual(business_date(datetime(2026,1,31,17,59,tzinfo=datetime_timezone.utc)),date(2026,1,31))

    def test_statement_uses_end_month_only_for_create_and_confirm(self):
        order=self.order()
        self.close()
        payload={"statement_no":"S-END","supplier_id":order.supplier_id,"purchase_order_id":order.id,
            "period_start":"2026-01-01","period_end":"2026-02-10","total_amount":"100.00","currency":"KGS"}
        created=self.post("/api/finance/supplier-statements",payload)
        self.assertEqual(created.status_code,201,created.content)
        self.close(2026,2)
        self.assert_closed(self.post(f"/api/finance/supplier-statements/{created.json()['id']}/confirm",{}))
        payload.update(statement_no="S-BLOCKED",period_start="2026-02-01",period_end="2026-02-11")
        self.assert_closed(self.post("/api/finance/supplier-statements",payload))
        self.assertEqual(SupplierStatementModel.objects.count(),1)
        self.assertFalse(FinancePayableModel.objects.exists())
        self.assertEqual(SupplierStatementModel.objects.get().status,"draft")

    def test_supplier_payment_open_date_can_settle_old_debt(self):
        order=self.order()
        payable=FinancePayableModel.objects.create(supplier=order.supplier,purchase_order=order,source_type="test",source_id=1,amount="100.00",outstanding_amount="100.00",currency="KGS")
        account=FinanceAccountModel.objects.create(name="Bank",currency="KGS",balance="1000.00")
        self.close()
        payload={"account_id":account.id,"amount":"10.00","payment_date":"2026-01-20","transaction_no":"P-BLOCK"}
        payload.update(approved_payment_fixture(payable,account,self.user,"10.00",date(2026,1,20)))
        with patch("backend.application.payment_requests.PrivateMediaStorage.exists",return_value=True):
            self.assert_closed(self.post(f"/api/finance/payables/{payable.id}/payments",payload))
        account.refresh_from_db();payable.refresh_from_db()
        self.assertEqual(account.balance,Decimal("1000.00"));self.assertEqual(payable.outstanding_amount,Decimal("100.00"))
        self.assertFalse(FinancePaymentModel.objects.exists())
        payload.update(payment_date="2026-02-01",transaction_no="P-OPEN")
        payload.update(approved_payment_fixture(payable,account,self.user,"10.00",date(2026,2,1)))
        with patch("backend.application.payment_requests.PrivateMediaStorage.exists",return_value=True):
            self.assertEqual(self.post(f"/api/finance/payables/{payable.id}/payments",payload).status_code,201)
        payable.refresh_from_db();self.assertEqual(payable.amount,Decimal("100.00"));self.assertEqual(payable.outstanding_amount,Decimal("90.00"))

    def test_closed_salary_calculation_month_is_blocked(self):
        employee=EmployeeModel.objects.create(employee_no="PERIOD-EMP",email=self.user.email,full_name_ru="Employee",department=self.dept,status="active",user=self.user)
        response=self.post("/api/attendance/timesheets/confirm",{"employee_id":employee.id,"year":2026,"month":1})
        self.assertEqual(response.status_code,201)
        self.close()
        self.assert_closed(self.post("/api/finance/salaries",{"employee_id":employee.id,"year":2026,"month":1,"base_salary":"1000"}))
        self.assertFalse(FinanceSalaryModel.objects.exists())

    def test_admin_cannot_bypass_guard_for_money_or_attachments(self):
        request=RequestFactory().get("/admin/")
        request.user=self.user
        for model in (ExpenseModel,ReimbursementPaymentModel,ExpenseActivityLogModel):
            model_admin=admin.site._registry[model]
            self.assertFalse(model_admin.has_add_permission(request))
            self.assertFalse(model_admin.has_change_permission(request))
            self.assertFalse(model_admin.has_delete_permission(request))
        inline=financial_admin.ExpenseAttachmentInline(ExpenseModel,admin.site)
        self.assertFalse(inline.has_add_permission(request))
        self.assertFalse(inline.has_change_permission(request))
        self.assertFalse(inline.has_delete_permission(request))

    def test_expense_log_failure_rolls_back_document_and_period(self):
        payload={"purchase_date":"2026-04-01","category":"Atomic","amount":"10.00","payment_source":"personal","payment_method":"personal_card"}
        with patch("backend.presentation.api.expense_views._log",side_effect=RuntimeError("audit unavailable")):
            self.assertEqual(self.post("/api/expenses",payload).status_code,500)
        self.assertFalse(ExpenseModel.objects.exists())
        self.assertFalse(FinancePeriodModel.objects.exists())


@skipUnless(connection.vendor == "postgresql", "Real row-lock contention requires PostgreSQL")
class FinancePeriodConcurrencyTests(TransactionTestCase):
    def setUp(self):
        fixtures.FinanceFlowTests.setUp(self)

    def test_close_waits_for_guarded_writer_then_blocks_next_writer(self):
        entered, release, close_started = Event(), Event(), Event()
        def writer():
            connections.close_all()
            try:
                with transaction.atomic():
                    require_open_period(2026,1)
                    entered.set()
                    if not release.wait(10): raise AssertionError("writer release timed out")
                return "committed"
            finally: connections.close_all()
        def closer():
            from django.test import Client
            connections.close_all()
            try:
                close_started.set()
                return Client().post("/api/finance/periods/2026/1/close",json.dumps({"reason":"Close after writer"}),content_type="application/json",**self.headers).status_code
            finally: connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            pending = pool.submit(writer)
            self.assertTrue(entered.wait(10))
            closure = pool.submit(closer)
            self.assertTrue(close_started.wait(10))
            self.assertFalse(closure.done())
            release.set()
            self.assertEqual(pending.result(10),"committed")
            self.assertEqual(closure.result(10),200)
        with transaction.atomic(), self.assertRaises(ClosedFinancePeriod): require_open_period(2026,1)
