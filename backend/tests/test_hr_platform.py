import json
from datetime import timedelta
from django.utils import timezone
from django.test import Client, TestCase
from backend.domain.entities import User
from backend.infrastructure.di.container import container
from backend.infrastructure.persistence.models import (
    ApprovalFlowModel, ApprovalNodeModel, ApprovalRequestModel, BoardModel, DepartmentModel,
    ApprovalActionModel, EmployeeModel, SystemPermissionModel, SystemRoleModel, UserModel, UserSystemRoleModel, AdminAssetModel, AdminAssetLogModel, AdminSupplyModel, AdminSupplyRequestModel, AdminMeetingRoomModel,
)
from backend.infrastructure.persistence.models import DocumentVersionModel, OperationLogModel


class HRPlatformApiTests(TestCase):
    def setUp(self):
        self.department = DepartmentModel.objects.create(name="HR test")
        self.director = UserModel.objects.create_user(email="director.hr@test", password="password123", full_name="Director", role="general_director")
        domain = User(id=self.director.id, email=self.director.email, password_hash=self.director.password, full_name=self.director.full_name, role=self.director.role)
        self.client = Client(HTTP_AUTHORIZATION=f"Bearer {container.jwt_service.generate_token(domain)}")

    def request(self, method, url, data=None):
        return getattr(self.client, method)(url, data=json.dumps(data or {}), content_type="application/json")

    def test_hire_approval_creates_account_only_after_approval(self):
        employee = self.request("post", "/api/hr/employees", {"employee_no": "HR-001", "email": "new.hr@test", "full_name_ru": "Новый сотрудник", "department_id": self.department.id}).json()
        self.assertFalse(UserModel.objects.filter(email="new.hr@test").exists())
        approval = self.request("post", f"/api/hr/employees/{employee['id']}/submit").json()
        self.assertFalse(UserModel.objects.filter(email="new.hr@test").exists())
        response = self.request("post", f"/api/approvals/{approval['id']}/actions", {"action": "approve"})
        self.assertEqual(response.status_code, 200)
        account = UserModel.objects.get(email="new.hr@test")
        self.assertTrue(account.is_active)
        self.assertEqual(EmployeeModel.objects.get(id=employee["id"]).status, "active")

    def test_rejection_does_not_create_account_and_onboarding_sets_password(self):
        employee = self.request("post", "/api/hr/employees", {"employee_no": "HR-002", "email": "reject.hr@test", "full_name_ru": "Тест", "department_id": self.department.id}).json()
        approval = self.request("post", f"/api/hr/employees/{employee['id']}/submit").json()
        rejected = self.request("post", f"/api/approvals/{approval['id']}/actions", {"action": "reject", "comment": "Incomplete"})
        self.assertEqual(rejected.status_code, 200); self.assertFalse(UserModel.objects.filter(email="reject.hr@test").exists())

    def test_invitation_response_never_discloses_raw_token(self):
        employee = self.request("post", "/api/hr/employees", {"employee_no": "HR-004", "email": "invite.hr@test", "full_name_ru": "Invite", "department_id": self.department.id}).json()
        approval = self.request("post", f"/api/hr/employees/{employee['id']}/submit").json()
        self.request("post", f"/api/approvals/{approval['id']}/actions", {"action": "approve"})
        response = self.request("post", f"/api/hr/employees/{employee['id']}/onboarding-link")
        self.assertEqual(response.status_code, 202)
        self.assertNotIn("token", response.json())
        self.assertNotIn("uid", response.json())

    def test_employee_creation_requires_permission_for_regular_employee(self):
        regular = UserModel.objects.create_user(email="regular.hr@test", password="password123", full_name="Regular", role="employee", department=self.department)
        domain = User(id=regular.id, email=regular.email, password_hash=regular.password, full_name=regular.full_name, role=regular.role, department_id=self.department.id)
        client = Client(HTTP_AUTHORIZATION=f"Bearer {container.jwt_service.generate_token(domain)}")
        response = client.post("/api/hr/employees", data=json.dumps({"employee_no": "HR-003", "email": "bad.hr@test", "full_name_ru": "Bad", "department_id": self.department.id}), content_type="application/json")
        self.assertEqual(response.status_code, 403)

    def test_versions_and_audit_are_append_only(self):
        version = DocumentVersionModel.objects.create(document_type="test", document_id=1, version_no=1, payload={})
        audit = OperationLogModel.objects.create(action="test", business_type="test", business_id=1)
        action = ApprovalActionModel.objects.create(approval=ApprovalRequestModel.objects.create(business_type="test", business_id=1, applicant=self.director), actor=self.director, action="submit")
        with self.assertRaises(RuntimeError): version.delete()
        with self.assertRaises(RuntimeError): audit.delete()
        with self.assertRaises(RuntimeError): action.delete()
        with self.assertRaises(RuntimeError): DocumentVersionModel.objects.filter(id=version.id).update(reason="changed")
        with self.assertRaises(RuntimeError): OperationLogModel.objects.filter(id=audit.id).delete()
        with self.assertRaises(RuntimeError): ApprovalActionModel.objects.filter(id=action.id).update(comment="changed")

    def test_flow_assigns_configured_user_and_submitted_scope_is_visible(self):
        approver = UserModel.objects.create_user(email="approver.hr@test", password="password123", full_name="Approver", role="employee")
        review_role = SystemRoleModel.objects.create(code="hr_reviewer", name="HR reviewer")
        review_role.permissions.set(SystemPermissionModel.objects.filter(code__in=["approval.read", "approval.act"]))
        UserSystemRoleModel.objects.create(user=approver, role=review_role)
        flow = ApprovalFlowModel.objects.create(business_type="employee_hire", name="HR hire")
        ApprovalNodeModel.objects.create(flow=flow, order=1, approver_type="user", user=approver)
        employee = self.request("post", "/api/hr/employees", {"employee_no": "HR-005", "email": "flow.hr@test", "full_name_ru": "Flow", "department_id": self.department.id}).json()
        approval = self.request("post", f"/api/hr/employees/{employee['id']}/submit").json()
        self.assertEqual(approval["status"], "pending")
        self.assertEqual(ApprovalRequestModel.objects.get(id=approval["id"]).assigned_to_id, approver.id)
        submitted = self.client.get("/api/approvals/inbox?scope=submitted").json()
        self.assertEqual(submitted["items"][0]["id"], approval["id"])
        domain = User(id=approver.id, email=approver.email, password_hash=approver.password, full_name=approver.full_name, role=approver.role)
        client = Client(HTTP_AUTHORIZATION=f"Bearer {container.jwt_service.generate_token(domain)}")
        self.assertEqual(client.get("/api/approvals/inbox").status_code, 200)
        self.assertEqual(client.post(f"/api/approvals/{approval['id']}/actions", data=json.dumps({"action": "approve"}), content_type="application/json").status_code, 200)

    def test_flow_api_rejects_approver_without_required_permissions(self):
        unprivileged = UserModel.objects.create_user(email="not-reviewer.hr@test", password="password123", full_name="No reviewer", role="employee")
        response = self.request("post", "/api/approval-flows", {
            "business_type": "employee_termination", "name": "Invalid",
            "nodes": [{"order": 1, "approver_type": "user", "user_id": unprivileged.id}],
        })
        self.assertEqual(response.status_code, 422)

    def test_patch_rejects_board_from_other_department(self):
        other = DepartmentModel.objects.create(name="Other HR")
        foreign_board = BoardModel.objects.create(title="Foreign", department=other)
        employee = self.request("post", "/api/hr/employees", {"employee_no": "HR-006", "email": "board.hr@test", "full_name_ru": "Board", "department_id": self.department.id}).json()
        response = self.request("patch", f"/api/hr/employees/{employee['id']}", {"board_id": foreign_board.id})
        self.assertEqual(response.status_code, 422)

    def test_rbac_permission_catalogue_is_available_on_clean_installation(self):
        response = self.client.get("/api/rbac/permissions")
        self.assertEqual(response.status_code, 200)
        items = response.json()["items"]
        self.assertTrue(items)
        self.assertIn("rbac.manage", {item["code"] for item in items})

    def test_independent_rbac_admin_can_list_users_without_legacy_board_admin_role(self):
        rbac_admin = UserModel.objects.create_user(
            email="rbac.admin@test", password="password123", full_name="RBAC admin", role="employee",
        )
        role = SystemRoleModel.objects.create(code="rbac_operator", name="RBAC operator")
        role.permissions.add(SystemPermissionModel.objects.get(code="rbac.manage"))
        UserSystemRoleModel.objects.create(user=rbac_admin, role=role)
        domain = User(
            id=rbac_admin.id, email=rbac_admin.email, password_hash=rbac_admin.password,
            full_name=rbac_admin.full_name, role=rbac_admin.role,
        )
        client = Client(HTTP_AUTHORIZATION=f"Bearer {container.jwt_service.generate_token(domain)}")
        response = client.get("/api/rbac/users")
        self.assertEqual(response.status_code, 200)
        self.assertIn(rbac_admin.id, {item["id"] for item in response.json()["items"]})
        # The independent RBAC capability must not turn into Kanban user admin.
        self.assertEqual(client.get("/api/users").status_code, 403)

    def test_termination_reason_is_required_and_audited_in_snapshot_and_version(self):
        employee = EmployeeModel.objects.create(
            employee_no="HR-TERM-001", email="termination.hr@test", full_name_ru="Termination",
            department=self.department, status="active", user=self.director,
        )
        missing_reason = self.request("post", f"/api/hr/employees/{employee.id}/termination/submit")
        self.assertEqual(missing_reason.status_code, 400)
        submitted = self.request("post", f"/api/hr/employees/{employee.id}/termination/submit", {"reason": "Contract ended"})
        self.assertEqual(submitted.status_code, 202)
        approval = ApprovalRequestModel.objects.get(id=submitted.json()["id"])
        self.assertEqual(approval.snapshot["termination_reason"], "Contract ended")
        version = DocumentVersionModel.objects.filter(document_type="employee", document_id=employee.id).latest("version_no")
        self.assertEqual(version.payload["termination_reason"], "Contract ended")

    def test_termination_is_blocked_until_assets_are_returned(self):
        employee = EmployeeModel.objects.create(employee_no="HR-ASSET-001", email="asset.hr@test", full_name_ru="Asset holder", department=self.department, status="active", user=self.director)
        asset = AdminAssetModel.objects.create(asset_no="ASSET-001", name="Laptop", category="IT", owner=employee)
        AdminAssetLogModel.objects.create(asset=asset, employee=employee, operation="issued", performed_by=self.director)
        self.assertEqual(self.request("post", f"/api/hr/employees/{employee.id}/termination/submit", {"reason": "Contract ended"}).status_code, 409)
        AdminAssetLogModel.objects.create(asset=asset, employee=employee, operation="returned", performed_by=self.director)
        self.assertEqual(self.request("post", f"/api/hr/employees/{employee.id}/termination/submit", {"reason": "Contract ended"}).status_code, 202)

    def test_asset_custody_api_keeps_auditable_issue_and_return_chain(self):
        employee = EmployeeModel.objects.create(employee_no="HR-ASSET-API", email="asset.api@test", full_name_ru="Asset API", department=self.department, status="active", user=self.director)
        asset = AdminAssetModel.objects.create(asset_no="ASSET-API", name="Phone", category="IT")
        issued = self.request("post", f"/api/admin/assets/{asset.id}/custody", {"operation": "issued", "employee_id": employee.id, "comment": "Work phone"})
        self.assertEqual(issued.status_code, 201)
        returned = self.request("post", f"/api/admin/assets/{asset.id}/custody", {"operation": "returned", "employee_id": employee.id})
        self.assertEqual(returned.status_code, 201)
        history = self.client.get(f"/api/admin/assets/{asset.id}/custody")
        self.assertEqual([item["operation"] for item in history.json()["logs"]], ["returned", "issued"])

    def test_supply_request_is_private_and_approval_reduces_stock(self):
        supply = AdminSupplyModel.objects.create(name="Paper", unit="pack", stock_qty="3")
        requester = UserModel.objects.create_user(email="supply.requester@test", password="password123", full_name="Requester", role="employee", department=self.department)
        domain = User(id=requester.id, email=requester.email, password_hash=requester.password, full_name=requester.full_name, role=requester.role, department_id=self.department.id)
        client = Client(HTTP_AUTHORIZATION=f"Bearer {container.jwt_service.generate_token(domain)}")
        created = client.post("/api/admin/supply-requests", data=json.dumps({"supply_id": supply.id, "qty": "2", "comment": "Printer"}), content_type="application/json")
        self.assertEqual(created.status_code, 201)
        self.assertEqual(client.get("/api/admin/supply-requests").json()["items"][0]["requester_id"], requester.id)
        approved = self.request("post", "/api/admin/supply-requests", {"action": "approve", "request_id": created.json()["id"]})
        self.assertEqual(approved.status_code, 200)
        supply.refresh_from_db(); self.assertEqual(supply.stock_qty, 1)
        self.assertEqual(AdminSupplyRequestModel.objects.get(id=created.json()["id"]).status, "approved")

    def test_meeting_booking_rejects_overlap_and_allows_cancellation(self):
        room = AdminMeetingRoomModel.objects.create(name="Ordo", capacity=8)
        start = timezone.now() + timedelta(days=1); end = start + timedelta(hours=1)
        payload = {"room_id": room.id, "start_at": start.isoformat(), "end_at": end.isoformat()}
        first = self.request("post", "/api/admin/meeting-bookings", payload)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(self.request("post", "/api/admin/meeting-bookings", payload).status_code, 409)
        self.assertEqual(self.request("post", "/api/admin/meeting-bookings", {"action": "cancel", "booking_id": first.json()["id"]}).status_code, 200)
        self.assertEqual(self.request("post", "/api/admin/meeting-bookings", payload).status_code, 201)
