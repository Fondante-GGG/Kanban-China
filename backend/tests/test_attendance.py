import json
from datetime import datetime, date, time
from django.test import TestCase, Client
from django.utils import timezone

from backend.infrastructure.persistence.models import (
    UserModel, DepartmentModel, BoardModel, BoardMemberModel,
    OfficeModel, WorkScheduleModel, AttendanceRecordModel, AbsenceModel, ConsentModel
)
from backend.infrastructure.di.container import container


class AttendanceTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.jwt_service = container.jwt_service

        # Department
        self.dept = DepartmentModel.objects.create(name="Разработка")

        # Users
        self.director = UserModel.objects.create_user(
            email="director@company.com",
            password="password123",
            full_name="Асанов Асан",
            role="general_director",
            department=self.dept
        )

        self.manager = UserModel.objects.create_user(
            email="manager@company.com",
            password="password123",
            full_name="Иванов Иван",
            role="manager",
            department=self.dept
        )

        self.employee = UserModel.objects.create_user(
            email="employee@company.com",
            password="password123",
            full_name="Пак Александр",
            role="employee",
            department=self.dept
        )

        # Board and memberships
        self.board = BoardModel.objects.create(title="Доска разработки", department=self.dept)
        BoardMemberModel.objects.create(board=self.board, user=self.manager, role="manager")
        BoardMemberModel.objects.create(board=self.board, user=self.employee, role="employee")

        # Office in Bishkek
        self.office = OfficeModel.objects.create(
            name="Главный офис Бишкек",
            address="г. Бишкек, пр. Чуй 120",
            latitude=42.8746,
            longitude=74.5698,
            radius_meters=100,
            ip_subnet="",
            is_ip_check_enabled=False
        )

        # Work Schedule 09:00 - 18:00
        self.schedule = WorkScheduleModel.objects.create(
            name="Стандартный",
            start_time="09:00:00",
            end_time="18:00:00",
            break_duration_minutes=60,
            timezone="Asia/Bishkek"
        )

        # Auth tokens
        self.dir_token = self.jwt_service.generate_token(self.director)
        self.mgr_token = self.jwt_service.generate_token(self.manager)
        self.emp_token = self.jwt_service.generate_token(self.employee)

    def test_check_in_within_radius_succeeds(self):
        # Lat/Lon right at the office
        res = self.client.post(
            "/api/attendance/check-in",
            data=json.dumps({
                "latitude": 42.87461,
                "longitude": 74.56981,
                "accuracy_meters": 10.0,
                "office_id": self.office.id
            }),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.emp_token}"
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("success"))
        self.assertLess(data.get("distance_meters"), 100)

        # Verify record in DB
        record = AttendanceRecordModel.objects.filter(user=self.employee, record_type="check_in").first()
        self.assertIsNotNone(record)
        self.assertTrue(record.is_within_radius)
        self.assertEqual(record.verification_result, "verified")

    def test_check_in_outside_radius_is_rejected(self):
        # Far coordinate outside Bishkek
        res = self.client.post(
            "/api/attendance/check-in",
            data=json.dumps({
                "latitude": 42.9500,
                "longitude": 74.8000,
                "accuracy_meters": 15.0,
                "office_id": self.office.id
            }),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.emp_token}"
        )
        self.assertEqual(res.status_code, 400)
        data = res.json()
        self.assertIn("вне радиуса", data.get("error", "").lower())

        # Check that rejection is saved in DB for audit
        record = AttendanceRecordModel.objects.filter(user=self.employee, record_type="check_in").first()
        self.assertIsNotNone(record)
        self.assertFalse(record.is_within_radius)
        self.assertEqual(record.verification_result, "rejected")

    def test_leave_and_resume_absence(self):
        # 1. Employee goes on lunch
        res = self.client.post(
            "/api/attendance/leave",
            data=json.dumps({
                "absence_type": "lunch",
                "reason": "Обед в кафе",
                "comment": "Буду через 40 минут"
            }),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.emp_token}"
        )
        self.assertEqual(res.status_code, 200)

        active = AbsenceModel.objects.filter(user=self.employee, category="break", end_time__isnull=True).first()
        self.assertIsNotNone(active)
        self.assertEqual(active.absence_type, "lunch")

        # 2. Employee returns
        res2 = self.client.post(
            "/api/attendance/resume",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.emp_token}"
        )
        self.assertEqual(res2.status_code, 200)

        active.refresh_from_db()
        self.assertIsNotNone(active.end_time)

    def test_manager_can_edit_attendance_with_reason(self):
        # Create a record for employee
        record = AttendanceRecordModel.objects.create(
            user=self.employee,
            record_type="check_in",
            timestamp=timezone.now(),
            is_within_radius=True,
            verification_result="verified"
        )

        new_time = timezone.now().replace(hour=8, minute=55, second=0).isoformat()
        res = self.client.put(
            f"/api/attendance/records/{record.id}",
            data=json.dumps({
                "timestamp": new_time,
                "edit_reason": "Сотрудник пришёл вовремя, забыл нажать кнопку из-за разряженного телефона"
            }),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.mgr_token}"
        )
        self.assertEqual(res.status_code, 200)

        record.refresh_from_db()
        self.assertTrue(record.is_edited)
        self.assertEqual(record.edited_by, self.manager)
        self.assertIn("Сотрудник пришёл вовремя", record.edit_reason)
        self.assertIsNotNone(record.original_timestamp)

    def test_employee_cannot_edit_attendance(self):
        record = AttendanceRecordModel.objects.create(
            user=self.employee,
            record_type="check_in",
            timestamp=timezone.now()
        )
        res = self.client.put(
            f"/api/attendance/records/{record.id}",
            data=json.dumps({
                "timestamp": timezone.now().isoformat(),
                "edit_reason": "Пытаюсь сам исправить"
            }),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.emp_token}"
        )
        self.assertEqual(res.status_code, 403)

    def test_monthly_timesheet_and_exports(self):
        now = timezone.now()
        # Create check in & out
        AttendanceRecordModel.objects.create(
            user=self.employee,
            record_type="check_in",
            timestamp=now.replace(hour=9, minute=0, second=0),
            is_within_radius=True,
            verification_result="verified"
        )
        AttendanceRecordModel.objects.create(
            user=self.employee,
            record_type="check_out",
            timestamp=now.replace(hour=18, minute=0, second=0),
            is_within_radius=True,
            verification_result="verified"
        )

        # 1. Timesheet JSON
        res = self.client.get(
            f"/api/attendance/reports/timesheet?year={now.year}&month={now.month}",
            HTTP_AUTHORIZATION=f"Bearer {self.dir_token}"
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("employees", data)
        self.assertGreaterEqual(len(data["employees"]), 1)

        # 2. Excel Export
        res_xlsx = self.client.get(
            f"/api/attendance/reports/export?format=xlsx&year={now.year}&month={now.month}",
            HTTP_AUTHORIZATION=f"Bearer {self.dir_token}"
        )
        self.assertEqual(res_xlsx.status_code, 200)
        self.assertEqual(res_xlsx["Content-Type"], "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        self.assertGreater(len(res_xlsx.content), 100)

        # 3. PDF Export
        res_pdf = self.client.get(
            f"/api/attendance/reports/export?format=pdf&year={now.year}&month={now.month}",
            HTTP_AUTHORIZATION=f"Bearer {self.dir_token}"
        )
        self.assertEqual(res_pdf.status_code, 200)
        self.assertEqual(res_pdf["Content-Type"], "application/pdf")
        self.assertGreater(len(res_pdf.content), 100)

        # 4. Word Export
        res_docx = self.client.get(
            f"/api/attendance/reports/export?format=docx&year={now.year}&month={now.month}",
            HTTP_AUTHORIZATION=f"Bearer {self.dir_token}"
        )
        self.assertEqual(res_docx.status_code, 200)
        self.assertEqual(res_docx["Content-Type"], "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        self.assertGreater(len(res_docx.content), 100)
