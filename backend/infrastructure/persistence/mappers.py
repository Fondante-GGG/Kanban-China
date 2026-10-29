from typing import Optional
from backend.domain.entities import (
    User, Department, Board, BoardMember, Column, Card, ChecklistItem, Comment, Attachment, ActivityLog, Notification,
    Office, WorkSchedule, AttendanceRecord, Absence, LocationLog, Consent
)
from backend.infrastructure.persistence.models import (
    UserModel, DepartmentModel, BoardModel, BoardMemberModel, ColumnModel, CardModel, ChecklistModel,
    CommentModel, AttachmentModel, ActivityLogModel, NotificationModel,
    OfficeModel, WorkScheduleModel, AttendanceRecordModel, AbsenceModel, LocationLogModel, ConsentModel
)


class DataMapper:
    @staticmethod
    def user_to_domain(model: UserModel) -> User:
        return User(
            id=model.id,
            email=model.email,
            password_hash=model.password,
            full_name=model.full_name,
            role=model.role,
            department_id=model.department_id,
            interface_language=model.interface_language,
            phone=model.phone,
            is_active=model.is_active,
            created_at=model.date_joined,
        )

    @staticmethod
    def department_to_domain(model: DepartmentModel) -> Department:
        return Department(
            id=model.id,
            name=model.name,
            created_at=model.created_at,
        )

    @staticmethod
    def board_to_domain(model: BoardModel) -> Board:
        return Board(
            id=model.id,
            title=model.title,
            department_id=model.department_id,
            background_theme=model.background_theme,
            is_archived=model.is_archived,
            created_at=model.created_at,
            department_name=model.department.name if model.department else None,
        )

    @staticmethod
    def board_member_to_domain(model: BoardMemberModel) -> BoardMember:
        return BoardMember(
            id=model.id,
            user_id=model.user_id,
            board_id=model.board_id,
            role=model.role,
            user_full_name=model.user.full_name if model.user else None,
            user_email=model.user.email if model.user else None,
        )

    @staticmethod
    def column_to_domain(model: ColumnModel) -> Column:
        return Column(
            id=model.id,
            board_id=model.board_id,
            title_ru=model.title_ru,
            title_zh=model.title_zh,
            title_ky=model.title_ky,
            original_lang=model.original_lang,
            order=model.order,
            created_at=model.created_at,
        )

    @staticmethod
    def card_to_domain(model: CardModel) -> Card:
        return Card(
            id=model.id,
            column_id=model.column_id,
            title_ru=model.title_ru,
            title_zh=model.title_zh,
            title_ky=model.title_ky,
            desc_ru=model.desc_ru,
            desc_zh=model.desc_zh,
            desc_ky=model.desc_ky,
            original_lang=model.original_lang,
            priority=model.priority,
            due_date=model.due_date,
            order=model.order,
            created_by_id=model.created_by_id,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def checklist_to_domain(model: ChecklistModel) -> ChecklistItem:
        return ChecklistItem(
            id=model.id,
            card_id=model.card_id,
            title=model.title,
            is_completed=model.is_completed,
            order=model.order,
            created_at=model.created_at,
        )

    @staticmethod
    def comment_to_domain(model: CommentModel) -> Comment:
        return Comment(
            id=model.id,
            card_id=model.card_id,
            user_id=model.user_id,
            text_ru=model.text_ru,
            text_zh=model.text_zh,
            text_ky=model.text_ky,
            original_lang=model.original_lang,
            created_at=model.created_at,
            user_full_name=model.user.full_name if model.user else None,
            user_role=model.user.role if model.user else None,
        )

    @staticmethod
    def attachment_to_domain(model: AttachmentModel) -> Attachment:
        return Attachment(
            id=model.id,
            card_id=model.card_id,
            file_path=model.file_path,
            file_name=model.file_name,
            file_size=model.file_size,
            content_type=model.content_type,
            uploaded_by_id=model.uploaded_by_id,
            created_at=model.created_at,
            uploader_name=model.uploaded_by.full_name if model.uploaded_by else None,
        )

    @staticmethod
    def activity_log_to_domain(model: ActivityLogModel) -> ActivityLog:
        return ActivityLog(
            id=model.id,
            card_id=model.card_id,
            user_id=model.user_id,
            action_type=model.action_type,
            details=model.details,
            created_at=model.created_at,
            user_full_name=model.user.full_name if model.user else None,
        )

    @staticmethod
    def notification_to_domain(model: NotificationModel) -> Notification:
        return Notification(
            id=model.id,
            user_id=model.user_id,
            title=model.title,
            message=model.message,
            entity_type=model.entity_type,
            entity_id=model.entity_id,
            is_read=model.is_read,
            created_at=model.created_at,
        )

    @staticmethod
    def office_to_domain(model: OfficeModel) -> Office:
        return Office(
            id=model.id,
            name=model.name,
            address=model.address,
            latitude=model.latitude,
            longitude=model.longitude,
            radius_meters=model.radius_meters,
            ip_subnet=model.ip_subnet,
            is_ip_check_enabled=model.is_ip_check_enabled,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def work_schedule_to_domain(model: WorkScheduleModel) -> WorkSchedule:
        return WorkSchedule(
            id=model.id,
            name=model.name,
            user_id=model.user_id,
            department_id=model.department_id,
            start_time=model.start_time.strftime("%H:%M") if hasattr(model.start_time, "strftime") else str(model.start_time)[:5],
            end_time=model.end_time.strftime("%H:%M") if hasattr(model.end_time, "strftime") else str(model.end_time)[:5],
            break_duration_minutes=model.break_duration_minutes,
            timezone=model.timezone,
            is_active=model.is_active,
            created_at=model.created_at,
            user_full_name=model.user.full_name if model.user else None,
            department_name=model.department.name if model.department else None,
        )

    @staticmethod
    def attendance_record_to_domain(model: AttendanceRecordModel) -> AttendanceRecord:
        return AttendanceRecord(
            id=model.id,
            user_id=model.user_id,
            office_id=model.office_id,
            record_type=model.record_type,
            timestamp=model.timestamp,
            latitude=model.latitude,
            longitude=model.longitude,
            accuracy_meters=model.accuracy_meters,
            is_within_radius=model.is_within_radius,
            ip_address=model.ip_address,
            verification_result=model.verification_result,
            rejection_reason=model.rejection_reason,
            is_edited=model.is_edited,
            edited_by_id=model.edited_by_id,
            edit_reason=model.edit_reason,
            original_timestamp=model.original_timestamp,
            created_at=model.created_at,
            user_full_name=model.user.full_name if model.user else None,
            user_email=model.user.email if model.user else None,
            office_name=model.office.name if model.office else None,
            edited_by_name=model.edited_by.full_name if model.edited_by else None,
        )

    @staticmethod
    def absence_to_domain(model: AbsenceModel) -> Absence:
        return Absence(
            id=model.id,
            user_id=model.user_id,
            category=model.category,
            absence_type=model.absence_type,
            start_time=model.start_time,
            end_time=model.end_time,
            reason=model.reason,
            comment=model.comment,
            is_approved=model.is_approved,
            approved_by_id=model.approved_by_id,
            created_at=model.created_at,
            user_full_name=model.user.full_name if model.user else None,
            user_department_name=model.user.department.name if (model.user and model.user.department) else None,
            approved_by_name=model.approved_by.full_name if model.approved_by else None,
        )

    @staticmethod
    def location_log_to_domain(model: LocationLogModel) -> LocationLog:
        return LocationLog(
            id=model.id,
            user_id=model.user_id,
            timestamp=model.timestamp,
            latitude=model.latitude,
            longitude=model.longitude,
            accuracy_meters=model.accuracy_meters,
            source=model.source,
            is_outside_office=model.is_outside_office,
            created_at=model.created_at,
            user_full_name=model.user.full_name if model.user else None,
        )

    @staticmethod
    def consent_to_domain(model: ConsentModel) -> Consent:
        return Consent(
            id=model.id,
            user_id=model.user_id,
            consent_version=model.consent_version,
            is_granted=model.is_granted,
            granted_at=model.granted_at,
            revoked_at=model.revoked_at,
            consent_text=model.consent_text,
            created_at=model.created_at,
            user_full_name=model.user.full_name if model.user else None,
        )

