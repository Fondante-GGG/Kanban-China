from typing import Optional, List, Dict
from django.db.models import Q
from backend.application.interfaces.repositories import (
    IUserRepository, IDepartmentRepository, IBoardRepository, IColumnRepository,
    ICardRepository, IChecklistRepository, ICommentRepository, IAttachmentRepository,
    IActivityLogRepository, INotificationRepository
)
from backend.domain.entities import (
    User, Department, Board, BoardMember, Column, Card, ChecklistItem, Comment, Attachment, ActivityLog, Notification
)
from backend.infrastructure.persistence.models import (
    UserModel, DepartmentModel, BoardModel, BoardMemberModel, ColumnModel,
    CardModel, CardAssigneeModel, ChecklistModel, CommentModel, AttachmentModel,
    ActivityLogModel, NotificationModel
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
        return bm.board_id if bm else None


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
