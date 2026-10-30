import json
from decimal import Decimal

from django.test import TestCase, Client

from backend.domain.entities import User
from backend.infrastructure.di.container import container
from backend.infrastructure.persistence.models import DepartmentModel, UserModel, ExpenseModel


class ExpenseApiTest(TestCase):
    def setUp(self):
        self.department = DepartmentModel.objects.create(name="Finance test department")
        self.employee = UserModel.objects.create_user(email="employee.finance@test.local", password="password123", full_name="Employee", role="employee", department=self.department)
        self.accountant = UserModel.objects.create_user(email="accountant.finance@test.local", password="password123", full_name="Accountant", role="accountant", department=self.department)

    def client_for(self, model):
        user = User(id=model.id, email=model.email, password_hash=model.password, full_name=model.full_name, role=model.role, department_id=model.department_id, interface_language=model.interface_language)
        return Client(HTTP_AUTHORIZATION=f"Bearer {container.jwt_service.generate_token(user)}")

    def create_personal_expense(self):
        response = self.client_for(self.employee).post("/api/expenses", data=json.dumps({
            "purchase_date": "2026-10-30", "category": "Stationery", "amount": "150.00",
            "payment_source": "personal", "payment_method": "personal_card",
        }), content_type="application/json")
        self.assertEqual(response.status_code, 201)
        return response.json()["id"]

    def test_employee_to_accountant_reimbursement_flow(self):
        expense_id = self.create_personal_expense()
        employee_client = self.client_for(self.employee)
        accountant_client = self.client_for(self.accountant)

        self.assertEqual(employee_client.post(f"/api/expenses/{expense_id}/status", data=json.dumps({"status": "under_review"}), content_type="application/json").status_code, 200)
        self.assertEqual(accountant_client.post(f"/api/expenses/{expense_id}/status", data=json.dumps({"status": "approved"}), content_type="application/json").status_code, 200)
        response = accountant_client.post(f"/api/expenses/{expense_id}/payment", data=json.dumps({"amount": "150.00", "transaction_number": "BANK-001"}), content_type="application/json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "paid")
        self.assertEqual(ExpenseModel.objects.get(id=expense_id).amount, Decimal("150.00"))

    def test_employee_cannot_approve_own_expense_or_read_other_expenses(self):
        expense_id = self.create_personal_expense()
        employee_client = self.client_for(self.employee)
        self.assertEqual(employee_client.post(f"/api/expenses/{expense_id}/status", data=json.dumps({"status": "approved"}), content_type="application/json").status_code, 403)
        another = UserModel.objects.create_user(email="other.finance@test.local", password="password123", full_name="Other", role="employee", department=self.department)
        self.assertEqual(self.client_for(another).get(f"/api/expenses/{expense_id}").status_code, 403)

    def test_rejected_expense_requires_comment_and_analytics_is_restricted(self):
        expense_id = self.create_personal_expense()
        employee_client = self.client_for(self.employee)
        accountant_client = self.client_for(self.accountant)
        employee_client.post(f"/api/expenses/{expense_id}/status", data=json.dumps({"status": "under_review"}), content_type="application/json")
        self.assertEqual(accountant_client.post(f"/api/expenses/{expense_id}/status", data=json.dumps({"status": "rejected"}), content_type="application/json").status_code, 400)
        self.assertEqual(employee_client.get("/api/expenses/analytics").status_code, 403)
        self.assertEqual(accountant_client.get("/api/expenses/analytics").status_code, 200)

    def test_accountant_can_export_finance_report_in_all_required_formats(self):
        self.create_personal_expense()
        client = self.client_for(self.accountant)
        expected_content_types = {
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "pdf": "application/pdf",
        }
        for fmt, content_type in expected_content_types.items():
            response = client.get(f"/api/expenses/export?format={fmt}")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Content-Type"], content_type)
            self.assertGreater(len(response.content), 100)

    def test_invalid_finance_filters_return_validation_error_not_server_error(self):
        client = self.client_for(self.accountant)
        self.assertEqual(client.get("/api/expenses?start_date=not-a-date").status_code, 400)
        self.assertEqual(client.get("/api/expenses/analytics?department_id=not-a-number").status_code, 400)
