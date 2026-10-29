from typing import Dict, Any, Tuple
from datetime import datetime
from backend.domain.entities import User
from backend.infrastructure.services.attendance_report_service import AttendanceReportService


class GetMonthlyTimesheetUseCase:
    def __init__(self, service: AttendanceReportService):
        self.service = service

    def execute(
        self,
        current_user: User,
        year: int,
        month: int,
        department_id: int = None,
        user_id: int = None
    ) -> Dict[str, Any]:
        return self.service.get_monthly_timesheet_data(
            year=year,
            month=month,
            department_id=department_id,
            user_id=user_id,
            current_user=current_user
        )


class ExportMonthlyTimesheetUseCase:
    def __init__(self, service: AttendanceReportService):
        self.service = service

    def execute(
        self,
        current_user: User,
        fmt: str,
        year: int,
        month: int,
        department_id: int = None,
        user_id: int = None
    ) -> Tuple[bytes, str, str]:
        data = self.service.get_monthly_timesheet_data(
            year=year,
            month=month,
            department_id=department_id,
            user_id=user_id,
            current_user=current_user
        )

        filename_prefix = f"timesheet_{year}_{month:02d}"

        if fmt == "xlsx":
            buf = self.service.export_excel(data)
            return (
                buf.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                f"{filename_prefix}.xlsx"
            )
        elif fmt == "docx":
            buf = self.service.export_word(data)
            return (
                buf.getvalue(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                f"{filename_prefix}.docx"
            )
        elif fmt == "pdf":
            buf = self.service.export_pdf(data)
            return (
                buf.getvalue(),
                "application/pdf",
                f"{filename_prefix}.pdf"
            )
        else:
            raise ValueError(f"Unsupported format: {fmt}")
