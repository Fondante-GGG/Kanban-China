from typing import Optional, List, Dict
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Q
from backend.application.interfaces.repositories import (
    IUserRepository, IDepartmentRepository, IBoardRepository, IColumnRepository,
    ICardRepository, IChecklistRepository, ICommentRepository, IAttachmentRepository,
    IActivityLogRepository, INotificationRepository,
    IOfficeRepository, IWorkScheduleRepository, IAttendanceRecordRepository,
    IAbsenceRepository, ILocationLogRepository, IConsentRepository
)
from backend.domain.entities import (
    User, Department, Board, BoardMember, Column, Card, ChecklistItem, Comment, Attachment, ActivityLog, Notification,
    Office, WorkSchedule, AttendanceRecord, Absence, LocationLog, Consent
)
from backend.infrastructure.persistence.models import (
    UserModel, DepartmentModel, BoardModel, BoardMemberModel, ColumnModel,
    CardModel, CardAssigneeModel, ChecklistModel, CommentModel, AttachmentModel,
    ActivityLogModel, NotificationModel,
    OfficeModel, WorkScheduleModel, AttendanceRecordModel, AbsenceModel,
    LocationLogModel, ConsentModel
)
from backend.infrastructure.persistence.mappers import DataMapper


class DjangoUserRepository(IUserRepository):
    def get_by_id(self, user_id: int) -> Optional[User]:
        try:
            m = UserModel.objects.select_related("department").get(id=user_id)
            return DataMapper.user_to_domain(m)
        except UserModel.DoesNotExist:
            return None

    def get_by_email(self, email: str) -> Optional[User]:
        try:
            m = UserModel.objects.select_related("department").get(email__iexact=email)
            return DataMapper.user_to_domain(m)
        except UserModel.DoesNotExist:
            return None

    def list_all(self, department_id: Optional[int] = None) -> List[User]:
        qs = UserModel.objects.select_related("department").all()
        if department_id:
            qs = qs.filter(department_id=department_id)
        return [DataMapper.user_to_domain(m) for m in qs]

    def create(self, user: User) -> User:
        m = UserModel(
            email=user.email,
            password=user.password_hash,
            full_name=user.full_name,
            role=user.role,
            department_id=user.department_id,
            interface_language=user.interface_language,
            phone=user.phone,
            is_active=user.is_active,
        )
        m.save()
        return DataMapper.user_to_domain(m)

    def update(self, user: User) -> User:
        m = UserModel.objects.get(id=user.id)
        m.email = user.email
        m.password = user.password_hash
        m.full_name = user.full_name
        m.role = user.role
        m.department_id = user.department_id
        m.interface_language = user.interface_language
        m.phone = user.phone
        m.is_active = user.is_active
        m.save()
        return DataMapper.user_to_domain(m)

    def delete(self, user_id: int) -> bool:
        deleted, _ = UserModel.objects.filter(id=user_id).delete()
        return deleted > 0

    def get_assigned_board_id(self, user_id: int) -> Optional[int]:
        bm = BoardMemberModel.objects.filter(user_id=user_id).first()
        if bm:
            return bm.board_id
        try:
            u = UserModel.objects.filter(id=user_id).first()
            if u and u.department_id:
                b = BoardModel.objects.filter(department_id=u.department_id).first()
                if b:
                    return b.id
        except Exception:
            pass
        return None


class DjangoDepartmentRepository(IDepartmentRepository):
    def get_by_id(self, dept_id: int) -> Optional[Department]:
        try:
            m = DepartmentModel.objects.get(id=dept_id)
            return DataMapper.department_to_domain(m)
        except DepartmentModel.DoesNotExist:
            return None

    def list_all(self) -> List[Department]:
        return [DataMapper.department_to_domain(m) for m in DepartmentModel.objects.all()]

    def create(self, department: Department) -> Department:
        m = DepartmentModel.objects.create(name=department.name)
        return DataMapper.department_to_domain(m)

    def update(self, department: Department) -> Department:
        m = DepartmentModel.objects.get(id=department.id)
        m.name = department.name
        m.save()
        return DataMapper.department_to_domain(m)

    def delete(self, dept_id: int) -> bool:
        deleted, _ = DepartmentModel.objects.filter(id=dept_id).delete()
        return deleted > 0


class DjangoBoardRepository(IBoardRepository):
    def get_by_id(self, board_id: int) -> Optional[Board]:
        try:
            m = BoardModel.objects.select_related("department").get(id=board_id)
            return DataMapper.board_to_domain(m)
        except BoardModel.DoesNotExist:
            return None

    def list_all(self, include_archived: bool = False) -> List[Board]:
        qs = BoardModel.objects.select_related("department").all()
        if not include_archived:
            qs = qs.filter(is_archived=False)
        return [DataMapper.board_to_domain(m) for m in qs]

    def list_by_ids(self, board_ids: List[int]) -> List[Board]:
        qs = BoardModel.objects.select_related("department").filter(id__in=board_ids, is_archived=False)
        return [DataMapper.board_to_domain(m) for m in qs]

    def create(self, board: Board) -> Board:
        m = BoardModel.objects.create(
            title=board.title,
            department_id=board.department_id,
            background_theme=board.background_theme,
            is_archived=board.is_archived
        )
        return DataMapper.board_to_domain(m)

    def update(self, board: Board) -> Board:
        m = BoardModel.objects.get(id=board.id)
        m.title = board.title
        m.department_id = board.department_id
        m.background_theme = board.background_theme
        m.is_archived = board.is_archived
        m.save()
        return DataMapper.board_to_domain(m)

    def delete(self, board_id: int) -> bool:
        deleted, _ = BoardModel.objects.filter(id=board_id).delete()
        return deleted > 0

    def get_members(self, board_id: int) -> List[BoardMember]:
        qs = BoardMemberModel.objects.select_related("user").filter(board_id=board_id)
        return [DataMapper.board_member_to_domain(m) for m in qs]

    def set_members(self, board_id: int, manager_id: Optional[int], employee_ids: List[int]) -> None:
        # Clear existing memberships for this board
        BoardMemberModel.objects.filter(board_id=board_id).delete()

        # Re-create memberships
        if manager_id:
            # Also clear any other boards this manager might be assigned to (strictly 1 board rule)
            BoardMemberModel.objects.filter(user_id=manager_id).delete()
            BoardMemberModel.objects.create(board_id=board_id, user_id=manager_id, role="manager")

        for emp_id in employee_ids:
            if emp_id and emp_id != manager_id:
                BoardMemberModel.objects.filter(user_id=emp_id).delete()
                BoardMemberModel.objects.create(board_id=board_id, user_id=emp_id, role="employee")


class DjangoColumnRepository(IColumnRepository):
    def get_by_id(self, col_id: int) -> Optional[Column]:
        try:
            m = ColumnModel.objects.get(id=col_id)
            return DataMapper.column_to_domain(m)
        except ColumnModel.DoesNotExist:
            return None

    def list_by_board(self, board_id: int) -> List[Column]:
        qs = ColumnModel.objects.filter(board_id=board_id).order_by("order", "created_at")
        return [DataMapper.column_to_domain(m) for m in qs]

    def create(self, column: Column) -> Column:
        m = ColumnModel.objects.create(
            board_id=column.board_id,
            title_ru=column.title_ru,
            title_zh=column.title_zh,
            title_ky=column.title_ky,
            original_lang=column.original_lang,
            order=column.order,
        )
        return DataMapper.column_to_domain(m)

    def update(self, column: Column) -> Column:
        m = ColumnModel.objects.get(id=column.id)
        m.title_ru = column.title_ru
        m.title_zh = column.title_zh
        m.title_ky = column.title_ky
        m.original_lang = column.original_lang
        m.order = column.order
        m.save()
        return DataMapper.column_to_domain(m)

    def delete(self, col_id: int) -> bool:
        deleted, _ = ColumnModel.objects.filter(id=col_id).delete()
        return deleted > 0

    def reorder(self, board_id: int, order_map: Dict[int, int]) -> None:
        for col_id, new_order in order_map.items():
            ColumnModel.objects.filter(id=col_id, board_id=board_id).update(order=new_order)


class DjangoCardRepository(ICardRepository):
    def get_by_id(self, card_id: int) -> Optional[Card]:
        try:
            m = CardModel.objects.get(id=card_id)
            return DataMapper.card_to_domain(m)
        except CardModel.DoesNotExist:
            return None

    def list_by_board(
        self,
        board_id: int,
        search: Optional[str] = None,
        priority: Optional[str] = None,
        assignee_id: Optional[int] = None
    ) -> List[Card]:
        qs = CardModel.objects.filter(column__board_id=board_id).select_related("column")
        if search:
            qs = qs.filter(
                Q(title_ru__icontains=search) |
                Q(title_zh__icontains=search) |
                Q(title_ky__icontains=search) |
                Q(desc_ru__icontains=search) |
                Q(desc_zh__icontains=search) |
                Q(desc_ky__icontains=search)
            )
        if priority:
            qs = qs.filter(priority=priority)
        if assignee_id:
            qs = qs.filter(assignee_relations__user_id=assignee_id)

        qs = qs.order_by("order", "-created_at").distinct()
        return [DataMapper.card_to_domain(m) for m in qs]

    def list_by_column(self, column_id: int) -> List[Card]:
        qs = CardModel.objects.filter(column_id=column_id).order_by("order", "-created_at")
        return [DataMapper.card_to_domain(m) for m in qs]

    def create(self, card: Card) -> Card:
        m = CardModel.objects.create(
            column_id=card.column_id,
            title_ru=card.title_ru,
            title_zh=card.title_zh,
            title_ky=card.title_ky,
            desc_ru=card.desc_ru,
            desc_zh=card.desc_zh,
            desc_ky=card.desc_ky,
            original_lang=card.original_lang,
            priority=card.priority,
            due_date=card.due_date,
            order=card.order,
            created_by_id=card.created_by_id,
        )
        return DataMapper.card_to_domain(m)

    def update(self, card: Card) -> Card:
        m = CardModel.objects.get(id=card.id)
        m.column_id = card.column_id
        m.title_ru = card.title_ru
        m.title_zh = card.title_zh
        m.title_ky = card.title_ky
        m.desc_ru = card.desc_ru
        m.desc_zh = card.desc_zh
        m.desc_ky = card.desc_ky
        m.original_lang = card.original_lang
        m.priority = card.priority
        m.due_date = card.due_date
        m.order = card.order
        m.save()
        return DataMapper.card_to_domain(m)

    def delete(self, card_id: int) -> bool:
        deleted, _ = CardModel.objects.filter(id=card_id).delete()
        return deleted > 0

    def move(self, card_id: int, target_column_id: int, new_order: int) -> Card:
        card = CardModel.objects.get(id=card_id)
        card.column_id = target_column_id
        card.order = new_order
        card.save()
        return DataMapper.card_to_domain(card)

    def set_assignees(self, card_id: int, user_ids: List[int]) -> None:
        CardAssigneeModel.objects.filter(card_id=card_id).delete()
        for uid in user_ids:
            CardAssigneeModel.objects.create(card_id=card_id, user_id=uid)

    def get_assignees(self, card_id: int) -> List[User]:
        qs = UserModel.objects.filter(assigned_card_relations__card_id=card_id)
        return [DataMapper.user_to_domain(m) for m in qs]


class DjangoChecklistRepository(IChecklistRepository):
    def list_by_card(self, card_id: int) -> List[ChecklistItem]:
        qs = ChecklistModel.objects.filter(card_id=card_id).order_by("order", "created_at")
        return [DataMapper.checklist_to_domain(m) for m in qs]

    def get_by_id(self, item_id: int) -> Optional[ChecklistItem]:
        try:
            m = ChecklistModel.objects.get(id=item_id)
            return DataMapper.checklist_to_domain(m)
        except ChecklistModel.DoesNotExist:
            return None

    def create(self, item: ChecklistItem) -> ChecklistItem:
        m = ChecklistModel.objects.create(
            card_id=item.card_id,
            title=item.title,
            is_completed=item.is_completed,
            order=item.order,
        )
        return DataMapper.checklist_to_domain(m)

    def update(self, item: ChecklistItem) -> ChecklistItem:
        m = ChecklistModel.objects.get(id=item.id)
        m.title = item.title
        m.is_completed = item.is_completed
        m.order = item.order
        m.save()
        return DataMapper.checklist_to_domain(m)

    def delete(self, item_id: int) -> bool:
        deleted, _ = ChecklistModel.objects.filter(id=item_id).delete()
        return deleted > 0


class DjangoCommentRepository(ICommentRepository):
    def list_by_card(self, card_id: int) -> List[Comment]:
        qs = CommentModel.objects.select_related("user").filter(card_id=card_id).order_by("created_at")
        return [DataMapper.comment_to_domain(m) for m in qs]

    def create(self, comment: Comment) -> Comment:
        m = CommentModel.objects.create(
            card_id=comment.card_id,
            user_id=comment.user_id,
            text_ru=comment.text_ru,
            text_zh=comment.text_zh,
            text_ky=comment.text_ky,
            original_lang=comment.original_lang,
        )
        # Re-fetch with user relation
        m = CommentModel.objects.select_related("user").get(id=m.id)
        return DataMapper.comment_to_domain(m)

    def delete(self, comment_id: int) -> bool:
        deleted, _ = CommentModel.objects.filter(id=comment_id).delete()
        return deleted > 0


class DjangoAttachmentRepository(IAttachmentRepository):
    def list_by_card(self, card_id: int) -> List[Attachment]:
        qs = AttachmentModel.objects.select_related("uploaded_by").filter(card_id=card_id).order_by("-created_at")
        return [DataMapper.attachment_to_domain(m) for m in qs]

    def get_by_id(self, attachment_id: int) -> Optional[Attachment]:
        try:
            m = AttachmentModel.objects.select_related("uploaded_by").get(id=attachment_id)
            return DataMapper.attachment_to_domain(m)
        except AttachmentModel.DoesNotExist:
            return None

    def create(self, attachment: Attachment) -> Attachment:
        m = AttachmentModel.objects.create(
            card_id=attachment.card_id,
            file_path=attachment.file_path,
            file_name=attachment.file_name,
            file_size=attachment.file_size,
            content_type=attachment.content_type,
            uploaded_by_id=attachment.uploaded_by_id,
        )
        m = AttachmentModel.objects.select_related("uploaded_by").get(id=m.id)
        return DataMapper.attachment_to_domain(m)

    def delete(self, attachment_id: int) -> bool:
        deleted, _ = AttachmentModel.objects.filter(id=attachment_id).delete()
        return deleted > 0


class DjangoActivityLogRepository(IActivityLogRepository):
    def list_by_card(self, card_id: int) -> List[ActivityLog]:
        qs = ActivityLogModel.objects.select_related("user").filter(card_id=card_id).order_by("-created_at")
        return [DataMapper.activity_log_to_domain(m) for m in qs]

    def create(self, log: ActivityLog) -> ActivityLog:
        m = ActivityLogModel.objects.create(
            card_id=log.card_id,
            user_id=log.user_id,
            action_type=log.action_type,
            details=log.details,
        )
        m = ActivityLogModel.objects.select_related("user").get(id=m.id)
        return DataMapper.activity_log_to_domain(m)


class DjangoNotificationRepository(INotificationRepository):
    def list_by_user(self, user_id: int, unread_only: bool = False) -> List[Notification]:
        qs = NotificationModel.objects.filter(user_id=user_id)
        if unread_only:
            qs = qs.filter(is_read=False)
        return [DataMapper.notification_to_domain(m) for m in qs[:50]]

    def create(self, notification: Notification) -> Notification:
        m = NotificationModel.objects.create(
            user_id=notification.user_id,
            title=notification.title,
            message=notification.message,
            entity_type=notification.entity_type,
            entity_id=notification.entity_id,
            is_read=notification.is_read,
        )
        return DataMapper.notification_to_domain(m)

    def mark_all_as_read(self, user_id: int) -> None:
        NotificationModel.objects.filter(user_id=user_id, is_read=False).update(is_read=True)

    def mark_as_read(self, notification_id: int, user_id: int) -> None:
        NotificationModel.objects.filter(id=notification_id, user_id=user_id).update(is_read=True)


class DjangoOfficeRepository(IOfficeRepository):
    def get_by_id(self, office_id: int) -> Optional[Office]:
        try:
            m = OfficeModel.objects.get(id=office_id)
            return DataMapper.office_to_domain(m)
        except OfficeModel.DoesNotExist:
            return None

    def list_all(self) -> List[Office]:
        return [DataMapper.office_to_domain(m) for m in OfficeModel.objects.all()]

    def create(self, office: Office) -> Office:
        m = OfficeModel.objects.create(
            name=office.name,
            address=office.address or "",
            latitude=office.latitude,
            longitude=office.longitude,
            radius_meters=office.radius_meters,
            ip_subnet=office.ip_subnet or "",
            is_ip_check_enabled=office.is_ip_check_enabled,
        )
        return DataMapper.office_to_domain(m)

    def update(self, office: Office) -> Office:
        OfficeModel.objects.filter(id=office.id).update(
            name=office.name,
            address=office.address or "",
            latitude=office.latitude,
            longitude=office.longitude,
            radius_meters=office.radius_meters,
            ip_subnet=office.ip_subnet or "",
            is_ip_check_enabled=office.is_ip_check_enabled,
        )
        return self.get_by_id(office.id)

    def delete(self, office_id: int) -> bool:
        cnt, _ = OfficeModel.objects.filter(id=office_id).delete()
        return cnt > 0


class DjangoWorkScheduleRepository(IWorkScheduleRepository):
    def get_by_id(self, schedule_id: int) -> Optional[WorkSchedule]:
        try:
            m = WorkScheduleModel.objects.select_related("user", "department").get(id=schedule_id)
            return DataMapper.work_schedule_to_domain(m)
        except WorkScheduleModel.DoesNotExist:
            return None

    def get_for_user(self, user_id: int, department_id: Optional[int] = None) -> Optional[WorkSchedule]:
        # 1. Personal schedule
        ps = WorkScheduleModel.objects.select_related("user", "department").filter(user_id=user_id, is_active=True).first()
        if ps:
            return DataMapper.work_schedule_to_domain(ps)
        # 2. Department schedule
        if department_id:
            ds = WorkScheduleModel.objects.select_related("user", "department").filter(department_id=department_id, is_active=True).first()
            if ds:
                return DataMapper.work_schedule_to_domain(ds)
        # 3. Default company schedule (first active without user and department or general)
        gs = WorkScheduleModel.objects.select_related("user", "department").filter(user__isnull=True, department__isnull=True, is_active=True).first()
        if gs:
            return DataMapper.work_schedule_to_domain(gs)
        return None

    def list_all(self) -> List[WorkSchedule]:
        qs = WorkScheduleModel.objects.select_related("user", "department").all()
        return [DataMapper.work_schedule_to_domain(m) for m in qs]

    def create(self, schedule: WorkSchedule) -> WorkSchedule:
        m = WorkScheduleModel.objects.create(
            name=schedule.name,
            user_id=schedule.user_id,
            department_id=schedule.department_id,
            start_time=schedule.start_time,
            end_time=schedule.end_time,
            break_duration_minutes=schedule.break_duration_minutes,
            timezone=schedule.timezone,
            is_active=schedule.is_active,
        )
        m = WorkScheduleModel.objects.select_related("user", "department").get(id=m.id)
        return DataMapper.work_schedule_to_domain(m)

    def update(self, schedule: WorkSchedule) -> WorkSchedule:
        WorkScheduleModel.objects.filter(id=schedule.id).update(
            name=schedule.name,
            user_id=schedule.user_id,
            department_id=schedule.department_id,
            start_time=schedule.start_time,
            end_time=schedule.end_time,
            break_duration_minutes=schedule.break_duration_minutes,
            timezone=schedule.timezone,
            is_active=schedule.is_active,
        )
        return self.get_by_id(schedule.id)

    def delete(self, schedule_id: int) -> bool:
        cnt, _ = WorkScheduleModel.objects.filter(id=schedule_id).delete()
        return cnt > 0


class DjangoAttendanceRecordRepository(IAttendanceRecordRepository):
    def get_by_id(self, record_id: int) -> Optional[AttendanceRecord]:
        try:
            m = AttendanceRecordModel.objects.select_related("user", "office", "edited_by").get(id=record_id)
            return DataMapper.attendance_record_to_domain(m)
        except AttendanceRecordModel.DoesNotExist:
            return None

    def get_latest_for_user(self, user_id: int) -> Optional[AttendanceRecord]:
        m = AttendanceRecordModel.objects.select_related("user", "office", "edited_by").filter(user_id=user_id).order_by("-timestamp").first()
        return DataMapper.attendance_record_to_domain(m) if m else None

    def list_for_user_date(self, user_id: int, date_obj) -> List[AttendanceRecord]:
        qs = AttendanceRecordModel.objects.select_related("user", "office", "edited_by").filter(
            user_id=user_id,
            timestamp__date=date_obj
        ).order_by("timestamp")
        return [DataMapper.attendance_record_to_domain(m) for m in qs]

    def list_records(
        self,
        user_ids: Optional[List[int]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[AttendanceRecord]:
        qs = AttendanceRecordModel.objects.select_related("user", "office", "edited_by").all()
        if user_ids is not None:
            qs = qs.filter(user_id__in=user_ids)
        if start_date:
            qs = qs.filter(timestamp__gte=start_date)
        if end_date:
            qs = qs.filter(timestamp__lte=end_date)
        qs = qs.order_by("-timestamp")
        return [DataMapper.attendance_record_to_domain(m) for m in qs]

    def create(self, record: AttendanceRecord) -> AttendanceRecord:
        m = AttendanceRecordModel.objects.create(
            user_id=record.user_id,
            office_id=record.office_id,
            record_type=record.record_type,
            timestamp=record.timestamp or timezone.now(),
            latitude=record.latitude,
            longitude=record.longitude,
            accuracy_meters=record.accuracy_meters,
            is_within_radius=record.is_within_radius,
            ip_address=record.ip_address,
            verification_result=record.verification_result,
            rejection_reason=record.rejection_reason,
            is_edited=record.is_edited,
            edited_by_id=record.edited_by_id,
            edit_reason=record.edit_reason,
            original_timestamp=record.original_timestamp,
        )
        m = AttendanceRecordModel.objects.select_related("user", "office", "edited_by").get(id=m.id)
        return DataMapper.attendance_record_to_domain(m)

    def update(self, record: AttendanceRecord) -> AttendanceRecord:
        AttendanceRecordModel.objects.filter(id=record.id).update(
            timestamp=record.timestamp,
            is_edited=record.is_edited,
            edited_by_id=record.edited_by_id,
            edit_reason=record.edit_reason,
            original_timestamp=record.original_timestamp,
            verification_result=record.verification_result,
        )
        return self.get_by_id(record.id)


class DjangoAbsenceRepository(IAbsenceRepository):
    def get_by_id(self, absence_id: int) -> Optional[Absence]:
        try:
            m = AbsenceModel.objects.select_related("user__department", "approved_by").get(id=absence_id)
            return DataMapper.absence_to_domain(m)
        except AbsenceModel.DoesNotExist:
            return None

    def get_active_break_for_user(self, user_id: int) -> Optional[Absence]:
        m = AbsenceModel.objects.select_related("user__department", "approved_by").filter(
            user_id=user_id,
            category="break",
            end_time__isnull=True
        ).order_by("-start_time").first()
        return DataMapper.absence_to_domain(m) if m else None

    def get_active_day_status_for_user(self, user_id: int, date_obj) -> Optional[Absence]:
        m = AbsenceModel.objects.select_related("user__department", "approved_by").filter(
            user_id=user_id,
            category="day_status",
            start_time__date__lte=date_obj
        ).filter(
            Q(end_time__isnull=True) | Q(end_time__date__gte=date_obj)
        ).order_by("-start_time").first()
        return DataMapper.absence_to_domain(m) if m else None

    def list_absences(
        self,
        user_ids: Optional[List[int]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        category: Optional[str] = None
    ) -> List[Absence]:
        qs = AbsenceModel.objects.select_related("user__department", "approved_by").all()
        if user_ids is not None:
            qs = qs.filter(user_id__in=user_ids)
        if start_date:
            qs = qs.filter(start_time__gte=start_date)
        if end_date:
            qs = qs.filter(start_time__lte=end_date)
        if category:
            qs = qs.filter(category=category)
        qs = qs.order_by("-start_time")
        return [DataMapper.absence_to_domain(m) for m in qs]

    def create(self, absence: Absence) -> Absence:
        m = AbsenceModel.objects.create(
            user_id=absence.user_id,
            category=absence.category,
            absence_type=absence.absence_type,
            start_time=absence.start_time or timezone.now(),
            end_time=absence.end_time,
            reason=absence.reason or "",
            comment=absence.comment or "",
            is_approved=absence.is_approved,
            approved_by_id=absence.approved_by_id,
        )
        m = AbsenceModel.objects.select_related("user__department", "approved_by").get(id=m.id)
        return DataMapper.absence_to_domain(m)

    def update(self, absence: Absence) -> Absence:
        AbsenceModel.objects.filter(id=absence.id).update(
            end_time=absence.end_time,
            reason=absence.reason or "",
            comment=absence.comment or "",
            is_approved=absence.is_approved,
            approved_by_id=absence.approved_by_id,
        )
        return self.get_by_id(absence.id)


class DjangoLocationLogRepository(ILocationLogRepository):
    def create(self, log: LocationLog) -> LocationLog:
        m = LocationLogModel.objects.create(
            user_id=log.user_id,
            timestamp=log.timestamp or timezone.now(),
            latitude=log.latitude,
            longitude=log.longitude,
            accuracy_meters=log.accuracy_meters,
            source=log.source,
            is_outside_office=log.is_outside_office,
        )
        return DataMapper.location_log_to_domain(m)

    def list_for_user(self, user_id: int, limit: int = 50) -> List[LocationLog]:
        qs = LocationLogModel.objects.select_related("user").filter(user_id=user_id).order_by("-timestamp")[:limit]
        return [DataMapper.location_log_to_domain(m) for m in qs]

    def cleanup_older_than(self, days: int = 90) -> int:
        cutoff = timezone.now() - timedelta(days=days)
        deleted, _ = LocationLogModel.objects.filter(created_at__lt=cutoff).delete()
        return deleted


class DjangoConsentRepository(IConsentRepository):
    def get_for_user(self, user_id: int) -> Optional[Consent]:
        m = ConsentModel.objects.select_related("user").filter(user_id=user_id).order_by("-granted_at").first()
        return DataMapper.consent_to_domain(m) if m else None

    def create_or_update(self, user_id: int, is_granted: bool, consent_version: str = "1.0", consent_text: str = "") -> Consent:
        m = ConsentModel.objects.filter(user_id=user_id).first()
        now = timezone.now()
        if m:
            m.is_granted = is_granted
            m.consent_version = consent_version
            if is_granted:
                m.granted_at = now
                m.revoked_at = None
            else:
                m.revoked_at = now
            if consent_text:
                m.consent_text = consent_text
            m.save()
        else:
            m = ConsentModel.objects.create(
                user_id=user_id,
                consent_version=consent_version,
                is_granted=is_granted,
                granted_at=now,
                revoked_at=None if is_granted else now,
                consent_text=consent_text,
            )
        m = ConsentModel.objects.select_related("user").get(id=m.id)
        return DataMapper.consent_to_domain(m)

