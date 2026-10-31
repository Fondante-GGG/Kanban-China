import os
import sys
from pathlib import Path
import unittest

project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.config.settings")

import django
django.setup()

from backend.domain.entities import User
from backend.domain.value_objects import RoleType
from backend.domain.services import AccessPolicyService
from backend.domain.exceptions import PermissionDeniedException
from backend.infrastructure.di.container import container
from backend.application.dtos import (
    LoginInputDTO, CardMoveDTO, CommentCreateDTO, ReportFilterDTO
)


class TestKanbanDomainAndPolicies(unittest.TestCase):
    def setUp(self):
        self.director = User(id=1, email="dir@co.com", password_hash="", full_name="Director", role=RoleType.GENERAL_DIRECTOR.value)
        self.manager = User(id=2, email="mgr@co.com", password_hash="", full_name="Manager", role=RoleType.MANAGER.value)
        self.employee = User(id=3, email="emp@co.com", password_hash="", full_name="Employee", role=RoleType.EMPLOYEE.value)

    def test_director_can_access_any_board(self):
        # Should not raise exception
        AccessPolicyService.ensure_can_view_board(self.director, board_id=99, user_assigned_board_id=None)
        AccessPolicyService.ensure_can_manage_board_structure(self.director, board_id=99, user_assigned_board_id=None)
        AccessPolicyService.ensure_can_manage_cards(self.director, board_id=99, user_assigned_board_id=None)
        AccessPolicyService.ensure_can_view_reports(self.director)

    def test_manager_access_restrictions(self):
        assigned_board = 10
        # Can manage own board
        AccessPolicyService.ensure_can_view_board(self.manager, board_id=10, user_assigned_board_id=assigned_board)
        AccessPolicyService.ensure_can_manage_board_structure(self.manager, board_id=10, user_assigned_board_id=assigned_board)
        AccessPolicyService.ensure_can_manage_cards(self.manager, board_id=10, user_assigned_board_id=assigned_board)

        # Cannot access another board (raises PermissionDeniedException)
        with self.assertRaises(PermissionDeniedException):
            AccessPolicyService.ensure_can_view_board(self.manager, board_id=20, user_assigned_board_id=assigned_board)

        with self.assertRaises(PermissionDeniedException):
            AccessPolicyService.ensure_can_manage_board_structure(self.manager, board_id=20, user_assigned_board_id=assigned_board)

        # Manager cannot view executive reports
        with self.assertRaises(PermissionDeniedException):
            AccessPolicyService.ensure_can_view_reports(self.manager)

    def test_employee_access_restrictions(self):
        assigned_board = 10
        # Can view own board and move cards and comment
        AccessPolicyService.ensure_can_view_board(self.employee, board_id=10, user_assigned_board_id=assigned_board)
        AccessPolicyService.ensure_can_move_card(self.employee, board_id=10, user_assigned_board_id=assigned_board)
        AccessPolicyService.ensure_can_comment(self.employee, board_id=10, user_assigned_board_id=assigned_board)

        # Employee CANNOT manage columns or cards
        with self.assertRaises(PermissionDeniedException):
            AccessPolicyService.ensure_can_manage_board_structure(self.employee, board_id=10, user_assigned_board_id=assigned_board)

        with self.assertRaises(PermissionDeniedException):
            AccessPolicyService.ensure_can_manage_cards(self.employee, board_id=10, user_assigned_board_id=assigned_board)

        with self.assertRaises(PermissionDeniedException):
            AccessPolicyService.ensure_can_view_reports(self.employee)


from django.test import TestCase
from django.contrib.auth.hashers import make_password


class TestServicesAndReports(TestCase):
    def setUp(self):
        with container.get_uow() as uow:
            from backend.domain.entities import User
            hashed = make_password("password123")
            dir_user = User(
                id=None,
                email="director@company.com",
                password_hash=hashed,
                full_name="Генеральный Директор",
                role="general_director",
                department_id=None,
                is_active=True,
                interface_language="ru"
            )
            uow.users.create(dir_user)
            uow.commit()
    def test_login_and_auth_token(self):
        login_uc = container.get_login_use_case()
        res = login_uc.execute(LoginInputDTO(email="director@company.com", password="password123"))
        self.assertIn("access_token", res)
        self.assertEqual(res["user"]["role"], "general_director")

        # Verify token
        payload = container.jwt_service.verify_token(res["access_token"])
        self.assertEqual(payload["email"], "director@company.com")

    def test_authenticated_user_can_update_only_own_interface_language(self):
        from django.test import Client
        import json
        login_uc = container.get_login_use_case()
        token = login_uc.execute(LoginInputDTO(email="director@company.com", password="password123"))["access_token"]
        client = Client(HTTP_AUTHORIZATION=f"Bearer {token}")
        response = client.put(
            "/api/profile/language",
            data=json.dumps({"interface_language": "zh-Hant"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["interface_language"], "zh-Hant")
        self.assertEqual(client.put("/api/profile/language", data=json.dumps({"interface_language": "en"}), content_type="application/json").status_code, 400)

    def test_chinese_conversion(self):
        s2t = container.translation_service.convert_chinese("软件开发与任务管理", "zh-Hant")
        self.assertIn("軟件", s2t)

        t2s = container.translation_service.convert_chinese("軟件開發", "zh-Hans")
        self.assertIn("软件", t2s)

    def test_reports_and_exports(self):
        with container.get_uow() as uow:
            dir_user = uow.users.get_by_email("director@company.com")

        analytics_uc = container.get_analytics_report_use_case()
        filter_dto = ReportFilterDTO(period="month")
        report_data = analytics_uc.execute(dir_user, filter_dto)

        self.assertIn("summary", report_data)
        self.assertIn("departments", report_data)
        self.assertIn("employees", report_data)
        self.assertGreaterEqual(report_data["summary"]["total_tasks"], 0)

        export_uc = container.get_export_report_use_case()

        # Excel export
        xlsx_bytes, mime_xlsx, fname_xlsx = export_uc.execute(dir_user, "xlsx", filter_dto)
        self.assertGreater(len(xlsx_bytes), 1000)
        self.assertTrue(fname_xlsx.endswith(".xlsx"))

        # Word export
        docx_bytes, mime_docx, fname_docx = export_uc.execute(dir_user, "docx", filter_dto)
        self.assertGreater(len(docx_bytes), 1000)
        self.assertTrue(fname_docx.endswith(".docx"))

        # PDF export
        pdf_bytes, mime_pdf, fname_pdf = export_uc.execute(dir_user, "pdf", filter_dto)
        self.assertGreater(len(pdf_bytes), 1000)
        self.assertTrue(fname_pdf.endswith(".pdf"))


if __name__ == "__main__":
    unittest.main()
