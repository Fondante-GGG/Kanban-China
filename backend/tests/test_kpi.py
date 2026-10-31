import json
from django.test import TestCase, Client
from backend.infrastructure.persistence.models import DepartmentModel, UserModel, EmployeeModel, KpiTemplateModel, KpiTaskModel, SystemPermissionModel, SystemRoleModel, UserSystemRoleModel
from backend.infrastructure.di.container import container
from backend.domain.entities import User

class KpiFlowTests(TestCase):
 def setUp(self):
  self.client=Client(); self.dept=DepartmentModel.objects.create(name="KPI")
  self.director=UserModel.objects.create_user(email="kpi.director@test",password="password123",full_name="D",role="general_director",department=self.dept)
  self.worker=UserModel.objects.create_user(email="kpi.worker@test",password="password123",full_name="W",role="employee",department=self.dept)
  self.employee=EmployeeModel.objects.create(employee_no="E-KPI",email=self.worker.email,full_name_ru="W",department=self.dept,status="active",user=self.worker)
  permission,_=SystemPermissionModel.objects.get_or_create(code="kpi.read",defaults={"name":"Read KPI"})
  read_role=SystemRoleModel.objects.create(code="kpi_worker_read",name="Read KPI")
  read_role.permissions.add(permission);UserSystemRoleModel.objects.create(user=self.worker,role=read_role)
  self.template=KpiTemplateModel.objects.create(name="Template",position_code="dev",cycle="month")
  self.task=KpiTaskModel.objects.create(template=self.template,employee=self.employee,year=2026,period="10")
 def headers(self,user):
  u=User(id=user.id,email=user.email,password_hash=user.password,full_name=user.full_name,role=user.role,department_id=user.department_id)
  return {"HTTP_AUTHORIZATION":f"Bearer {container.jwt_service.generate_token(u)}"}
 def test_employee_self_review_then_director_confirms(self):
  self.assertEqual(self.client.post(f"/api/kpi/tasks/{self.task.id}/score",data=json.dumps({"stage":"self","score":"80"}),content_type="application/json",**self.headers(self.worker)).status_code,200)
  self.assertEqual(self.client.post(f"/api/kpi/tasks/{self.task.id}/score",data=json.dumps({"stage":"manager","score":"90"}),content_type="application/json",**self.headers(self.director)).status_code,200)
  self.task.refresh_from_db();self.assertEqual(self.task.status,"senior_review")
  reviewer=UserModel.objects.create_user(email="kpi.reviewer@test",password="password123",full_name="R",role="general_director",department=self.dept)
  self.assertEqual(self.client.post(f"/api/kpi/tasks/{self.task.id}/review",data=json.dumps({"decision":"approve"}),content_type="application/json",**self.headers(reviewer)).status_code,200)
  self.task.refresh_from_db();self.assertEqual(self.task.status,"confirmed")

 def test_manager_cannot_score_another_department(self):
  other=DepartmentModel.objects.create(name="Other KPI")
  manager=UserModel.objects.create_user(email="kpi.manager@test",password="password123",full_name="M",role="manager",department=self.dept)
  permission,_=SystemPermissionModel.objects.get_or_create(code="kpi.manage",defaults={"name":"Manage KPI"})
  role=SystemRoleModel.objects.create(code="kpi_manager_test",name="KPI manager")
  role.permissions.add(permission);UserSystemRoleModel.objects.create(user=manager,role=role)
  foreign_user=UserModel.objects.create_user(email="kpi.foreign@test",password="password123",full_name="F",role="employee",department=other)
  foreign_employee=EmployeeModel.objects.create(employee_no="E-KPI-FOREIGN",email=foreign_user.email,full_name_ru="F",department=other,status="active",user=foreign_user)
  foreign_task=KpiTaskModel.objects.create(template=self.template,employee=foreign_employee,year=2026,period="11",status="manager_review",self_score="75")
  response=self.client.post(f"/api/kpi/tasks/{foreign_task.id}/score",data=json.dumps({"stage":"manager","score":"90"}),content_type="application/json",**self.headers(manager))
  self.assertEqual(response.status_code,403)

 def test_acknowledgement_is_owner_only_idempotent_and_audited(self):
  from backend.infrastructure.persistence.models import OperationLogModel
  self.task.status="confirmed"; self.task.final_score="90"; self.task.save()
  url=f"/api/kpi/tasks/{self.task.id}/acknowledge"
  self.assertEqual(self.client.post(url,**self.headers(self.director)).status_code,403)
  response=self.client.post(url,**self.headers(self.worker))
  self.assertEqual(response.status_code,200)
  self.assertEqual(response.json()["status"],"confirmed")
  acknowledged_at=response.json()["acknowledged_at"]
  self.assertIsNotNone(acknowledged_at)
  self.assertEqual(self.client.post(url,**self.headers(self.worker)).json()["acknowledged_at"],acknowledged_at)
  self.task.refresh_from_db()
  self.assertEqual(str(self.task.final_score),"90.00")
  logs=OperationLogModel.objects.filter(action="kpi.acknowledged",business_id=self.task.id)
  self.assertEqual(logs.count(),1)
  self.assertEqual(logs.get().actor_id,self.worker.id)
  self.assertEqual(logs.get().new_data["acknowledged_at"],acknowledged_at)
  score_url=f"/api/kpi/tasks/{self.task.id}/score"
  self.assertEqual(self.client.post(score_url,data=json.dumps({"stage":"manager","score":"95"}),content_type="application/json",**self.headers(self.director)).status_code,403)

 def test_acknowledgement_rejects_unconfirmed_results(self):
  from backend.infrastructure.persistence.models import OperationLogModel
  for status in ("self_review","manager_review","senior_review"):
   self.task.status=status;self.task.save()
   response=self.client.post(f"/api/kpi/tasks/{self.task.id}/acknowledge",**self.headers(self.worker))
   self.assertEqual(response.status_code,409)
  self.task.refresh_from_db();self.assertIsNone(self.task.acknowledged_at)
  self.assertFalse(OperationLogModel.objects.filter(action="kpi.acknowledged").exists())

 def test_acknowledgement_requires_auth_and_post_and_existing_task(self):
  url=f"/api/kpi/tasks/{self.task.id}/acknowledge"
  self.assertEqual(self.client.post(url).status_code,401)
  self.assertEqual(self.client.get(url,**self.headers(self.worker)).status_code,405)
  self.assertEqual(self.client.post("/api/kpi/tasks/999999/acknowledge",**self.headers(self.worker)).status_code,404)

 def test_task_list_includes_acknowledgement(self):
  self.task.status="confirmed";self.task.save()
  result=self.client.post(f"/api/kpi/tasks/{self.task.id}/acknowledge",**self.headers(self.worker)).json()
  response=self.client.get("/api/kpi/tasks",**self.headers(self.director))
  self.assertEqual(response.status_code,200)
  self.assertEqual(response.json()["items"][0]["acknowledged_at"],result["acknowledged_at"])


 def test_failed_audit_rolls_back_acknowledgement(self):
  from unittest.mock import patch
  from backend.infrastructure.persistence.models import OperationLogModel
  self.task.status="confirmed";self.task.final_score="90";self.task.save()
  with patch.object(OperationLogModel.objects,"create",side_effect=RuntimeError("audit unavailable")):
   response=self.client.post(f"/api/kpi/tasks/{self.task.id}/acknowledge",**self.headers(self.worker))
   self.assertEqual(response.status_code,500)
  self.task.refresh_from_db()
  self.assertIsNone(self.task.acknowledged_at)
  self.assertFalse(OperationLogModel.objects.filter(action="kpi.acknowledged").exists())


from django.test import TransactionTestCase, skipUnlessDBFeature


class KpiConcurrentScoreTests(TransactionTestCase):
    setUp = KpiFlowTests.setUp
    headers = KpiFlowTests.headers

    @skipUnlessDBFeature("has_select_for_update")
    def test_waiting_manager_cannot_overwrite_confirmed_result(self):
        """Exercise real row-lock contention on PostgreSQL; SQLite cannot do this."""
        from concurrent.futures import ThreadPoolExecutor
        from threading import Event
        from unittest.mock import patch
        from django.db import close_old_connections, connection

        self.task.status = "manager_review"
        self.task.save()
        first_saved = Event()
        second_reading = Event()
        release_first = Event()
        original_save = KpiTaskModel.save
        headers = self.headers(self.director)
        task_id = self.task.id

        def pause_first_save(instance, *args, **kwargs):
            result = original_save(instance, *args, **kwargs)
            if str(instance.manager_score) == "90":
                first_saved.set()
                if not release_first.wait(10):
                    raise TimeoutError("Second scorer did not attempt its read")
            return result

        def score(value, observe=False):
            close_old_connections()
            def observe_read(execute, sql, params, many, context):
                if 'FROM "kpi_tasks"' in sql and sql.lstrip().upper().startswith("SELECT"):
                    second_reading.set()
                return execute(sql, params, many, context)
            try:
                with connection.execute_wrapper(observe_read if observe else lambda execute, sql, params, many, context: execute(sql, params, many, context)):
                    return Client().post(
                        f"/api/kpi/tasks/{task_id}/score",
                        data=json.dumps({"stage": "manager", "score": value}),
                        content_type="application/json", **headers,
                    ).status_code
            finally:
                close_old_connections()

        with patch.object(KpiTaskModel, "save", pause_first_save):
            with ThreadPoolExecutor(max_workers=2) as pool:
                first = pool.submit(score, "90")
                try:
                    self.assertTrue(first_saved.wait(10))
                    second = pool.submit(score, "95", True)
                    self.assertTrue(second_reading.wait(10))
                finally:
                    release_first.set()
                self.assertEqual(first.result(timeout=10), 200)
                self.assertEqual(second.result(timeout=10), 403)
        self.task.refresh_from_db()
        self.assertEqual(str(self.task.manager_score), "90.00")
        self.assertIsNone(self.task.final_score)
        self.assertEqual(self.task.status, "senior_review")
        self.assertEqual(self.client.post(f"/api/kpi/tasks/{task_id}/acknowledge", **self.headers(self.worker)).status_code, 409)


class KpiWorkflowTests(TestCase):
    """Independent review, assignment scope and template validation regressions."""

    setUp = KpiFlowTests.setUp
    headers = KpiFlowTests.headers

    def post(self, path, body, user=None):
        return self.client.post(path, data=json.dumps(body), content_type="application/json", **self.headers(user or self.director))

    def manager(self):
        user = UserModel.objects.create_user(email="manager.workflow@test", password="password123", full_name="Manager", role="manager", department=self.dept)
        role = SystemRoleModel.objects.create(code="kpi_workflow_manager", name="KPI manager")
        for code in ("kpi.read", "kpi.manage"):
            permission, _ = SystemPermissionModel.objects.get_or_create(code=code, defaults={"name": code})
            role.permissions.add(permission)
        UserSystemRoleModel.objects.create(user=user, role=role)
        return user

    def test_full_independent_review_return_acknowledge_and_archive(self):
        manager = self.manager()
        score_url = f"/api/kpi/tasks/{self.task.id}/score"
        review_url = f"/api/kpi/tasks/{self.task.id}/review"
        self.assertEqual(self.post(score_url, {"stage": "self", "score": "80", "comment_ky": "Өзүм"}, self.worker).status_code, 200)
        self.assertEqual(self.post(score_url, {"stage": "manager", "score": "90", "comment_ru": "Хорошо"}, manager).status_code, 200)
        self.assertEqual(self.client.post(f"/api/kpi/tasks/{self.task.id}/acknowledge", **self.headers(self.worker)).status_code, 409)
        self.assertEqual(self.post(review_url, {"decision": "approve"}, manager).status_code, 403)
        self.assertEqual(self.post(review_url, {"decision": "return"}).status_code, 400)
        self.assertEqual(self.post(review_url, {"decision": "return", "comment_zh": "请修改"}).status_code, 200)
        self.assertEqual(self.post(score_url, {"stage": "manager", "score": "85"}, manager).status_code, 200)
        self.assertEqual(self.post(review_url, {"decision": "approve", "comment_ru": "Утверждено"}).status_code, 200)
        self.assertEqual(self.client.post(f"/api/kpi/tasks/{self.task.id}/archive", **self.headers(self.director)).status_code, 409)
        self.assertEqual(self.client.post(f"/api/kpi/tasks/{self.task.id}/acknowledge", **self.headers(self.worker)).status_code, 200)
        archive_url = f"/api/kpi/tasks/{self.task.id}/archive"
        self.assertEqual(self.client.post(archive_url, **self.headers(self.worker)).status_code, 403)
        first = self.client.post(archive_url, **self.headers(manager))
        self.assertEqual(first.status_code, 200)
        self.assertEqual(self.client.post(archive_url, **self.headers(manager)).json()["archived_at"], first.json()["archived_at"])
        self.assertEqual(self.client.get("/api/kpi/tasks", **self.headers(self.director)).json()["items"], [])
        archived = self.client.get("/api/kpi/tasks?archived=true", **self.headers(self.director)).json()["items"][0]
        self.assertEqual(archived["allowed_actions"], [])
        self.assertEqual(archived["final_score"], "85.00")
        self.assertEqual(archived["comments"]["self"]["ky"], "Өзүм")
        self.assertEqual(archived["employee_name_ru"], self.employee.full_name_ru)
        self.assertIn("kpi.review_return", [item["action"] for item in archived["history"]])

    def test_director_cannot_review_own_manager_score(self):
        self.task.status = "manager_review"
        self.task.save()
        self.assertEqual(self.post(f"/api/kpi/tasks/{self.task.id}/score", {"stage": "manager", "score": "90"}).status_code, 200)
        self.assertEqual(self.post(f"/api/kpi/tasks/{self.task.id}/review", {"decision": "approve"}).status_code, 403)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "senior_review")
        self.assertIsNone(self.task.final_score)

    def test_invalid_scores_do_not_change_task(self):
        for score in ("NaN", "Infinity", "-Infinity", "1.001", "101", "-1", None, True, [], "1e999999"):
            response = self.post(f"/api/kpi/tasks/{self.task.id}/score", {"stage": "self", "score": score}, self.worker)
            self.assertEqual(response.status_code, 400, score)
            self.assertEqual(response.json()["code"], "validation_error")
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "self_review")

    def test_templates_are_atomic_and_year_cycle_is_available(self):
        path = "/api/kpi/templates"
        base = {"name": "Yearly", "position_code": "dev", "cycle": "year", "items": [{"name_ru": "Quality", "name_zh": "质量", "name_ky": "Сапат", "weight": "100", "formula": "manual"}]}
        before = KpiTemplateModel.objects.count()
        for invalid in ([{"name_ru": "Valid", "weight": "100"}, {"weight": "0"}], ["bad"], [{"name_ru": "X", "weight": "NaN"}], [{"name_ru": "X", "weight": "90"}], [{"name_ru": "X", "weight": "100", "formula": "__import__('os')"}]):
            self.assertEqual(self.post(path, {**base, "items": invalid}).status_code, 400)
            self.assertEqual(KpiTemplateModel.objects.count(), before)
        response = self.post(path, base)
        self.assertEqual(response.status_code, 201)
        template_id = response.json()["id"]
        assigned = self.post("/api/kpi/tasks", {"template_id": template_id, "employee_id": self.employee.id, "year": 2026, "period": "year"})
        self.assertEqual(assigned.status_code, 201)
        self.assertEqual(self.post("/api/kpi/tasks", {"template_id": template_id, "employee_id": self.employee.id, "year": 2026, "period": "year"}).status_code, 409)
        self.assertEqual(self.post("/api/kpi/tasks", {"template_id": template_id, "employee_id": self.employee.id, "year": 2027, "period": "01"}).status_code, 400)

    def test_assignment_and_candidates_are_department_scoped(self):
        manager = self.manager()
        other_department = DepartmentModel.objects.create(name="Private")
        other_user = UserModel.objects.create_user(email="private.workflow@test", password="password123", full_name="Private", role="employee", department=other_department)
        other_employee = EmployeeModel.objects.create(employee_no="PRIVATE-WORKFLOW", email=other_user.email, full_name_ru="Private", department=other_department, status="active", user=other_user)
        body = {"template_id": self.template.id, "employee_id": other_employee.id, "year": 2026, "period": "11"}
        self.assertEqual(self.post("/api/kpi/tasks", body, manager).status_code, 403)
        candidates = self.client.get("/api/kpi/assignees", **self.headers(manager)).json()["items"]
        self.assertEqual([item["id"] for item in candidates], [self.employee.id])
        self.assertEqual(self.client.get("/api/kpi/assignees", **self.headers(self.worker)).status_code, 403)
        own_body = {**body, "employee_id": self.employee.id}
        self.assertEqual(self.post("/api/kpi/tasks", own_body, manager).status_code, 201)
        self.assertEqual(self.client.put("/api/kpi/tasks", **self.headers(manager)).status_code, 405)
        own_data = self.client.get("/api/kpi/tasks", **self.headers(manager)).json()["items"]
        self.assertEqual(len(own_data), 2)
        self.assertTrue(all(row["employee_id"] == self.employee.id for row in own_data))

    def test_employee_manage_permission_does_not_grant_department_writes(self):
        role = SystemRoleModel.objects.create(code="kpi_employee_manage", name="Manage")
        permission, _ = SystemPermissionModel.objects.get_or_create(code="kpi.manage", defaults={"name": "Manage"})
        role.permissions.add(permission)
        UserSystemRoleModel.objects.create(user=self.worker, role=role)
        self.assertEqual(self.post("/api/kpi/tasks", {"template_id": self.template.id, "employee_id": self.employee.id, "year": 2027, "period": "01"}, self.worker).status_code, 403)

    def test_task_list_pagination_filters_and_allowed_actions(self):
        role = SystemRoleModel.objects.create(code="kpi_employee_read", name="Read")
        permission, _ = SystemPermissionModel.objects.get_or_create(code="kpi.read", defaults={"name": "Read"})
        role.permissions.add(permission)
        UserSystemRoleModel.objects.create(user=self.worker, role=role)
        data = self.client.get("/api/kpi/tasks?year=2026&status=self_review&limit=1", **self.headers(self.worker)).json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["items"][0]["allowed_actions"], ["self_score"])
        for query in ("year=NaN", "status=bad", "limit=0", "archived=no", "offset=-1"):
            self.assertEqual(self.client.get(f"/api/kpi/tasks?{query}", **self.headers(self.worker)).status_code, 400)


    def test_revoked_module_permission_blocks_owner_writes(self):
        UserSystemRoleModel.objects.filter(user=self.worker).delete()
        score_url = f"/api/kpi/tasks/{self.task.id}/score"
        self.assertEqual(self.post(score_url, {"stage": "self", "score": "80"}, self.worker).status_code, 403)
        self.task.status = "confirmed"
        self.task.final_score = "90"
        self.task.save()
        self.assertEqual(self.client.post(f"/api/kpi/tasks/{self.task.id}/acknowledge", **self.headers(self.worker)).status_code, 403)
        self.assertEqual(self.client.get("/api/kpi/tasks", **self.headers(self.worker)).status_code, 403)
        self.task.refresh_from_db()
        self.assertIsNone(self.task.acknowledged_at)

    def test_template_creation_is_audited_and_audit_failure_rolls_back(self):
        from unittest.mock import patch
        from backend.infrastructure.persistence.models import KpiTemplateItemModel, OperationLogModel

        body = {"name": "Audited", "position_code": "dev", "cycle": "month", "items": [{"name_ru": "Quality", "weight": "100"}]}
        response = self.post("/api/kpi/templates", body)
        self.assertEqual(response.status_code, 201)
        template_id = response.json()["id"]
        log = OperationLogModel.objects.get(action="kpi.template_created", business_type="kpi_template", business_id=template_id)
        self.assertEqual(log.actor_id, self.director.id)
        self.assertEqual(log.ip_address, "127.0.0.1")
        self.assertEqual(log.new_data["items"][0]["weight"], "100")
        before_templates = KpiTemplateModel.objects.count()
        before_items = KpiTemplateItemModel.objects.count()
        with patch.object(OperationLogModel.objects, "create", side_effect=RuntimeError("audit unavailable")):
            failed = self.post("/api/kpi/templates", {**body, "name": "Must roll back"})
            self.assertEqual(failed.status_code, 500)
        self.assertEqual(KpiTemplateModel.objects.count(), before_templates)
        self.assertEqual(KpiTemplateItemModel.objects.count(), before_items)
        self.assertFalse(KpiTemplateModel.objects.filter(name="Must roll back").exists())
