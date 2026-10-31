from datetime import date
from django.test import TestCase, Client
from backend.infrastructure.di.container import container
from backend.domain.entities import User
from backend.infrastructure.persistence.models import DepartmentModel, UserModel, EmployeeModel, SupplierModel, PurchaseOrderModel, SupplierStatementModel, FinancePayableModel

class FinanceFlowTests(TestCase):
 def setUp(self):
  self.client=Client();self.dept=DepartmentModel.objects.create(name="Finance flow")
  self.user=UserModel.objects.create_user(email="finance.flow@test.local",password="password123",full_name="Director",role="general_director",department=self.dept)
  d=User(id=self.user.id,email=self.user.email,password_hash=self.user.password,full_name=self.user.full_name,role=self.user.role,department_id=self.dept.id)
  self.headers={"HTTP_AUTHORIZATION":f"Bearer {container.jwt_service.generate_token(d)}"}
 def test_payable_needs_receiving_before_confirmed_statement(self):
  supplier=SupplierModel.objects.create(name_ru="S",status="active",created_by=self.user)
  order=PurchaseOrderModel.objects.create(po_no="FIN-PO",supplier=supplier,order_date=date.today(),status="approved",created_by=self.user)
  statement=SupplierStatementModel.objects.create(statement_no="ST-1",supplier=supplier,purchase_order=order,period_start=date.today(),period_end=date.today(),total_amount="100",currency="KGS",created_by=self.user)
  self.assertEqual(self.client.post(f"/api/finance/supplier-statements/{statement.id}/confirm",**self.headers).status_code,400)
  order.status="received";order.save()
  self.assertEqual(self.client.post(f"/api/finance/supplier-statements/{statement.id}/confirm",**self.headers).status_code,201)
  self.assertEqual(FinancePayableModel.objects.count(),1)

 def test_statement_is_created_through_api_before_confirmation(self):
  supplier=SupplierModel.objects.create(name_ru="API supplier",status="active",created_by=self.user)
  order=PurchaseOrderModel.objects.create(po_no="FIN-API",supplier=supplier,order_date=date.today(),status="received",currency="KGS",created_by=self.user)
  response=self.client.post("/api/finance/supplier-statements",data='{"statement_no":"ST-API","supplier_id":%d,"purchase_order_id":%d,"period_start":"%s","period_end":"%s","total_amount":"75","currency":"KGS"}'%(supplier.id,order.id,date.today().isoformat(),date.today().isoformat()),content_type="application/json",**self.headers)
  self.assertEqual(response.status_code,201)
  self.assertEqual(self.client.post(f"/api/finance/supplier-statements/{response.json()['id']}/confirm",**self.headers).status_code,201)

 def test_salary_requires_confirmed_timesheet_for_same_period(self):
  employee=EmployeeModel.objects.create(employee_no="FIN-SALARY",email=self.user.email,full_name_ru="Director",department=self.dept,status="active",user=self.user)
  payload={"employee_id":employee.id,"year":2026,"month":10,"base_salary":"1000"}
  self.assertEqual(self.client.post("/api/finance/salaries",data=__import__("json").dumps(payload),content_type="application/json",**self.headers).status_code,409)
  confirmed=self.client.post("/api/attendance/timesheets/confirm",data=__import__("json").dumps({"employee_id":employee.id,"year":2026,"month":10}),content_type="application/json",**self.headers)
  self.assertEqual(confirmed.status_code,201)
  self.assertEqual(self.client.post("/api/finance/salaries",data=__import__("json").dumps(payload),content_type="application/json",**self.headers).status_code,201)
