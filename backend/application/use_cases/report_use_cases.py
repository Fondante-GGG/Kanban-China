from typing import Dict, Any, Optional, Tuple
from backend.application.interfaces.uow import IUnitOfWork
from backend.application.interfaces.services import IReportService
from backend.application.dtos import ReportFilterDTO
from backend.domain.entities import User
from backend.domain.services import AccessPolicyService
from backend.domain.exceptions import ValidationException


class GetAnalyticsReportUseCase:
    def __init__(self, uow: IUnitOfWork, report_service: IReportService):
        self.uow = uow
        self.report_service = report_service

    def execute(self, current_user: User, dto: ReportFilterDTO) -> Dict[str, Any]:
        AccessPolicyService.ensure_can_view_reports(current_user)
        with self.uow:
            return self.report_service.get_analytics_data(
                self.uow,
                dto.period,
                dto.start_date,
                dto.end_date,
                dto.department_id
            )


class ExportReportUseCase:
    def __init__(self, uow: IUnitOfWork, report_service: IReportService):
        self.uow = uow
        self.report_service = report_service

    def execute(self, current_user: User, export_format: str, dto: ReportFilterDTO) -> Tuple[bytes, str, str]:
        """Returns (file_bytes, content_type, filename)"""
        AccessPolicyService.ensure_can_view_reports(current_user)

        with self.uow:
            data = self.report_service.get_analytics_data(
                self.uow,
                dto.period,
                dto.start_date,
                dto.end_date,
                dto.department_id
            )

        fmt = export_format.lower()
        if fmt == "xlsx" or fmt == "excel":
            file_bytes = self.report_service.export_excel(data)
            return file_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", f"report_{dto.period}.xlsx"
        elif fmt == "docx" or fmt == "word":
            file_bytes = self.report_service.export_word(data)
            return file_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", f"report_{dto.period}.docx"
        elif fmt == "pdf":
            file_bytes = self.report_service.export_pdf(data)
            return file_bytes, "application/pdf", f"report_{dto.period}.pdf"
        else:
            raise ValidationException(f"Unsupported export format: {export_format}")
