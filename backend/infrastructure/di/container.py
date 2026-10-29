from backend.infrastructure.persistence.uow import DjangoUnitOfWork
from backend.infrastructure.services.jwt_service import JwtTokenService
from backend.infrastructure.services.translation_service import ResilientTranslationService
from backend.infrastructure.services.report_service import ReportService
from backend.infrastructure.services.attendance_report_service import AttendanceReportService

from backend.application.use_cases.auth_use_cases import (
    LoginUseCase, GetProfileUseCase, ResetPasswordUseCase
)
from backend.application.use_cases.user_use_cases import (
    ListUsersUseCase, CreateUserUseCase, UpdateUserUseCase, DeleteUserUseCase
)
from backend.application.use_cases.board_use_cases import (
    ListBoardsUseCase, GetBoardDetailsUseCase, CreateBoardUseCase, UpdateBoardUseCase, DeleteBoardUseCase
)
from backend.application.use_cases.column_use_cases import (
    CreateColumnUseCase, UpdateColumnUseCase, DeleteColumnUseCase, ReorderColumnsUseCase
)
from backend.application.use_cases.card_use_cases import (
    CreateCardUseCase, UpdateCardUseCase, MoveCardUseCase, DeleteCardUseCase, GetCardDetailUseCase
)
from backend.application.use_cases.checklist_use_cases import (
    AddChecklistItemUseCase, ToggleChecklistItemUseCase, DeleteChecklistItemUseCase
)
from backend.application.use_cases.comment_use_cases import (
    AddCommentUseCase, DeleteCommentUseCase
)
from backend.application.use_cases.attachment_use_cases import (
    UploadAttachmentUseCase, DeleteAttachmentUseCase
)
from backend.application.use_cases.notification_use_cases import (
    GetNotificationsUseCase, MarkNotificationsReadUseCase
)
from backend.application.use_cases.report_use_cases import (
    GetAnalyticsReportUseCase, ExportReportUseCase
)
from backend.application.use_cases.attendance_use_cases import (
    GetAttendanceStatusUseCase, CheckInUseCase, CheckOutUseCase, LeaveAbsenceUseCase,
    ResumeAbsenceUseCase, RecordLocationLogUseCase, ListAttendanceRecordsUseCase,
    EditAttendanceRecordUseCase, ManageConsentUseCase, CreateDayStatusUseCase
)
from backend.application.use_cases.attendance_report_use_cases import (
    GetMonthlyTimesheetUseCase, ExportMonthlyTimesheetUseCase
)


class Container:
    """Dependency Injection Container (Service Locator / Composition Root)"""
    def __init__(self):
        # Singletons for infrastructure services
        self.jwt_service = JwtTokenService()
        self.translation_service = ResilientTranslationService()
        self.report_service = ReportService()
        self.attendance_report_service = AttendanceReportService()

    def get_uow(self) -> DjangoUnitOfWork:
        return DjangoUnitOfWork()

    # Auth Use Cases
    def get_login_use_case(self) -> LoginUseCase:
        return LoginUseCase(self.get_uow(), self.jwt_service)

    def get_profile_use_case(self) -> GetProfileUseCase:
        return GetProfileUseCase(self.get_uow())

    def get_reset_password_use_case(self) -> ResetPasswordUseCase:
        return ResetPasswordUseCase(self.get_uow())

    # User Use Cases
    def get_list_users_use_case(self) -> ListUsersUseCase:
        return ListUsersUseCase(self.get_uow())

    def get_create_user_use_case(self) -> CreateUserUseCase:
        return CreateUserUseCase(self.get_uow())

    def get_update_user_use_case(self) -> UpdateUserUseCase:
        return UpdateUserUseCase(self.get_uow())

    def get_delete_user_use_case(self) -> DeleteUserUseCase:
        return DeleteUserUseCase(self.get_uow())

    # Board Use Cases
    def get_list_boards_use_case(self) -> ListBoardsUseCase:
        return ListBoardsUseCase(self.get_uow())

    def get_board_details_use_case(self) -> GetBoardDetailsUseCase:
        return GetBoardDetailsUseCase(self.get_uow())

    def get_create_board_use_case(self) -> CreateBoardUseCase:
        return CreateBoardUseCase(self.get_uow(), self.translation_service)

    def get_update_board_use_case(self) -> UpdateBoardUseCase:
        return UpdateBoardUseCase(self.get_uow())

    def get_delete_board_use_case(self) -> DeleteBoardUseCase:
        return DeleteBoardUseCase(self.get_uow())

    # Column Use Cases
    def get_create_column_use_case(self) -> CreateColumnUseCase:
        return CreateColumnUseCase(self.get_uow(), self.translation_service)

    def get_update_column_use_case(self) -> UpdateColumnUseCase:
        return UpdateColumnUseCase(self.get_uow(), self.translation_service)

    def get_delete_column_use_case(self) -> DeleteColumnUseCase:
        return DeleteColumnUseCase(self.get_uow())

    def get_reorder_columns_use_case(self) -> ReorderColumnsUseCase:
        return ReorderColumnsUseCase(self.get_uow())

    # Card Use Cases
    def get_create_card_use_case(self) -> CreateCardUseCase:
        return CreateCardUseCase(self.get_uow(), self.translation_service)

    def get_update_card_use_case(self) -> UpdateCardUseCase:
        return UpdateCardUseCase(self.get_uow(), self.translation_service)

    def get_move_card_use_case(self) -> MoveCardUseCase:
        return MoveCardUseCase(self.get_uow())

    def get_delete_card_use_case(self) -> DeleteCardUseCase:
        return DeleteCardUseCase(self.get_uow())

    def get_card_detail_use_case(self) -> GetCardDetailUseCase:
        return GetCardDetailUseCase(self.get_uow())

    # Checklist Use Cases
    def get_add_checklist_use_case(self) -> AddChecklistItemUseCase:
        return AddChecklistItemUseCase(self.get_uow())

    def get_toggle_checklist_use_case(self) -> ToggleChecklistItemUseCase:
        return ToggleChecklistItemUseCase(self.get_uow())

    def get_delete_checklist_use_case(self) -> DeleteChecklistItemUseCase:
        return DeleteChecklistItemUseCase(self.get_uow())

    # Comment Use Cases
    def get_add_comment_use_case(self) -> AddCommentUseCase:
        return AddCommentUseCase(self.get_uow(), self.translation_service)

    def get_delete_comment_use_case(self) -> DeleteCommentUseCase:
        return DeleteCommentUseCase(self.get_uow())

    # Attachment Use Cases
    def get_upload_attachment_use_case(self) -> UploadAttachmentUseCase:
        return UploadAttachmentUseCase(self.get_uow())

    def get_delete_attachment_use_case(self) -> DeleteAttachmentUseCase:
        return DeleteAttachmentUseCase(self.get_uow())

    # Notification Use Cases
    def get_notifications_use_case(self) -> GetNotificationsUseCase:
        return GetNotificationsUseCase(self.get_uow())

    def get_mark_notifications_read_use_case(self) -> MarkNotificationsReadUseCase:
        return MarkNotificationsReadUseCase(self.get_uow())

    # Report Use Cases
    def get_analytics_report_use_case(self) -> GetAnalyticsReportUseCase:
        return GetAnalyticsReportUseCase(self.get_uow(), self.report_service)

    def get_export_report_use_case(self) -> ExportReportUseCase:
        return ExportReportUseCase(self.get_uow(), self.report_service)

    # Attendance Use Cases
    def get_attendance_status_use_case(self) -> GetAttendanceStatusUseCase:
        return GetAttendanceStatusUseCase(self.get_uow())

    def get_check_in_use_case(self) -> CheckInUseCase:
        return CheckInUseCase(self.get_uow())

    def get_check_out_use_case(self) -> CheckOutUseCase:
        return CheckOutUseCase(self.get_uow())

    def get_leave_absence_use_case(self) -> LeaveAbsenceUseCase:
        return LeaveAbsenceUseCase(self.get_uow())

    def get_resume_absence_use_case(self) -> ResumeAbsenceUseCase:
        return ResumeAbsenceUseCase(self.get_uow())

    def get_location_log_use_case(self) -> RecordLocationLogUseCase:
        return RecordLocationLogUseCase(self.get_uow())

    def get_list_attendance_records_use_case(self) -> ListAttendanceRecordsUseCase:
        return ListAttendanceRecordsUseCase(self.get_uow())

    def get_edit_attendance_record_use_case(self) -> EditAttendanceRecordUseCase:
        return EditAttendanceRecordUseCase(self.get_uow())

    def get_manage_consent_use_case(self) -> ManageConsentUseCase:
        return ManageConsentUseCase(self.get_uow())

    def get_create_day_status_use_case(self) -> CreateDayStatusUseCase:
        return CreateDayStatusUseCase(self.get_uow())

    def get_monthly_timesheet_use_case(self) -> GetMonthlyTimesheetUseCase:
        return GetMonthlyTimesheetUseCase(self.attendance_report_service)

    def get_export_monthly_timesheet_use_case(self) -> ExportMonthlyTimesheetUseCase:
        return ExportMonthlyTimesheetUseCase(self.attendance_report_service)


# Global container instance
container = Container()
