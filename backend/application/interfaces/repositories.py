from abc import ABC, abstractmethod
from typing import Optional, List
from datetime import datetime
from backend.domain.entities import (
    User, Department, Board, BoardMember, Column, Card, ChecklistItem, Comment, Attachment, ActivityLog, Notification,
    Office, WorkSchedule, AttendanceRecord, Absence, LocationLog, Consent
)


class IUserRepository(ABC):
    @abstractmethod
    def get_by_id(self, user_id: int) -> Optional[User]:
        pass

    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]:
        pass

    @abstractmethod
    def list_all(self, department_id: Optional[int] = None) -> List[User]:
        pass

    @abstractmethod
    def create(self, user: User) -> User:
        pass

    @abstractmethod
    def update(self, user: User) -> User:
        pass

    @abstractmethod
    def delete(self, user_id: int) -> bool:
        pass

    @abstractmethod
    def get_assigned_board_id(self, user_id: int) -> Optional[int]:
        pass


class IDepartmentRepository(ABC):
    @abstractmethod
    def get_by_id(self, dept_id: int) -> Optional[Department]:
        pass

    @abstractmethod
    def list_all(self) -> List[Department]:
        pass

    @abstractmethod
    def create(self, department: Department) -> Department:
        pass

    @abstractmethod
    def update(self, department: Department) -> Department:
        pass

    @abstractmethod
    def delete(self, dept_id: int) -> bool:
        pass


class IBoardRepository(ABC):
    @abstractmethod
    def get_by_id(self, board_id: int) -> Optional[Board]:
        pass

    @abstractmethod
    def list_all(self, include_archived: bool = False) -> List[Board]:
        pass

    @abstractmethod
    def list_by_ids(self, board_ids: List[int]) -> List[Board]:
        pass

    @abstractmethod
    def create(self, board: Board) -> Board:
        pass

    @abstractmethod
    def update(self, board: Board) -> Board:
        pass

    @abstractmethod
    def delete(self, board_id: int) -> bool:
        pass

    @abstractmethod
    def get_members(self, board_id: int) -> List[BoardMember]:
        pass

    @abstractmethod
    def set_members(self, board_id: int, manager_id: Optional[int], employee_ids: List[int]) -> None:
        pass


class IColumnRepository(ABC):
    @abstractmethod
    def get_by_id(self, col_id: int) -> Optional[Column]:
        pass

    @abstractmethod
    def list_by_board(self, board_id: int) -> List[Column]:
        pass

    @abstractmethod
    def create(self, column: Column) -> Column:
        pass

    @abstractmethod
    def update(self, column: Column) -> Column:
        pass

    @abstractmethod
    def delete(self, col_id: int) -> bool:
        pass

    @abstractmethod
    def reorder(self, board_id: int, order_map: dict[int, int]) -> None:
        pass


class ICardRepository(ABC):
    @abstractmethod
    def get_by_id(self, card_id: int) -> Optional[Card]:
        pass

    @abstractmethod
    def list_by_board(self, board_id: int, search: Optional[str] = None, priority: Optional[str] = None, assignee_id: Optional[int] = None) -> List[Card]:
        pass

    @abstractmethod
    def list_by_column(self, column_id: int) -> List[Card]:
        pass

    @abstractmethod
    def create(self, card: Card) -> Card:
        pass

    @abstractmethod
    def update(self, card: Card) -> Card:
        pass

    @abstractmethod
    def delete(self, card_id: int) -> bool:
        pass

    @abstractmethod
    def move(self, card_id: int, target_column_id: int, new_order: int) -> Card:
        pass

    @abstractmethod
    def set_assignees(self, card_id: int, user_ids: List[int]) -> None:
        pass

    @abstractmethod
    def get_assignees(self, card_id: int) -> List[User]:
        pass


class IChecklistRepository(ABC):
    @abstractmethod
    def list_by_card(self, card_id: int) -> List[ChecklistItem]:
        pass

    @abstractmethod
    def get_by_id(self, item_id: int) -> Optional[ChecklistItem]:
        pass

    @abstractmethod
    def create(self, item: ChecklistItem) -> ChecklistItem:
        pass

    @abstractmethod
    def update(self, item: ChecklistItem) -> ChecklistItem:
        pass

    @abstractmethod
    def delete(self, item_id: int) -> bool:
        pass


class ICommentRepository(ABC):
    @abstractmethod
    def list_by_card(self, card_id: int) -> List[Comment]:
        pass

    @abstractmethod
    def create(self, comment: Comment) -> Comment:
        pass

    @abstractmethod
    def delete(self, comment_id: int) -> bool:
        pass


class IAttachmentRepository(ABC):
    @abstractmethod
    def list_by_card(self, card_id: int) -> List[Attachment]:
        pass

    @abstractmethod
    def get_by_id(self, attachment_id: int) -> Optional[Attachment]:
        pass

    @abstractmethod
    def create(self, attachment: Attachment) -> Attachment:
        pass

    @abstractmethod
    def delete(self, attachment_id: int) -> bool:
        pass


class IActivityLogRepository(ABC):
    @abstractmethod
    def list_by_card(self, card_id: int) -> List[ActivityLog]:
        pass

    @abstractmethod
    def create(self, log: ActivityLog) -> ActivityLog:
        pass


class INotificationRepository(ABC):
    @abstractmethod
    def list_by_user(self, user_id: int, unread_only: bool = False) -> List[Notification]:
        pass

    @abstractmethod
    def create(self, notification: Notification) -> Notification:
        pass

    @abstractmethod
    def mark_all_as_read(self, user_id: int) -> None:
        pass

    @abstractmethod
    def mark_as_read(self, notification_id: int, user_id: int) -> None:
        pass


class IOfficeRepository(ABC):
    @abstractmethod
    def get_by_id(self, office_id: int) -> Optional[Office]:
        pass

    @abstractmethod
    def list_all(self) -> List[Office]:
        pass

    @abstractmethod
    def create(self, office: Office) -> Office:
        pass

    @abstractmethod
    def update(self, office: Office) -> Office:
        pass

    @abstractmethod
    def delete(self, office_id: int) -> bool:
        pass


class IWorkScheduleRepository(ABC):
    @abstractmethod
    def get_by_id(self, schedule_id: int) -> Optional[WorkSchedule]:
        pass

    @abstractmethod
    def get_for_user(self, user_id: int, department_id: Optional[int] = None) -> Optional[WorkSchedule]:
        pass

    @abstractmethod
    def list_all(self) -> List[WorkSchedule]:
        pass

    @abstractmethod
    def create(self, schedule: WorkSchedule) -> WorkSchedule:
        pass

    @abstractmethod
    def update(self, schedule: WorkSchedule) -> WorkSchedule:
        pass

    @abstractmethod
    def delete(self, schedule_id: int) -> bool:
        pass


class IAttendanceRecordRepository(ABC):
    @abstractmethod
    def get_by_id(self, record_id: int) -> Optional[AttendanceRecord]:
        pass

    @abstractmethod
    def get_latest_for_user(self, user_id: int) -> Optional[AttendanceRecord]:
        pass

    @abstractmethod
    def list_for_user_date(self, user_id: int, date_obj) -> List[AttendanceRecord]:
        pass

    @abstractmethod
    def list_records(
        self,
        user_ids: Optional[List[int]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[AttendanceRecord]:
        pass

    @abstractmethod
    def create(self, record: AttendanceRecord) -> AttendanceRecord:
        pass

    @abstractmethod
    def update(self, record: AttendanceRecord) -> AttendanceRecord:
        pass


class IAbsenceRepository(ABC):
    @abstractmethod
    def get_by_id(self, absence_id: int) -> Optional[Absence]:
        pass

    @abstractmethod
    def get_active_break_for_user(self, user_id: int) -> Optional[Absence]:
        pass

    @abstractmethod
    def get_active_day_status_for_user(self, user_id: int, date_obj) -> Optional[Absence]:
        pass

    @abstractmethod
    def list_absences(
        self,
        user_ids: Optional[List[int]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        category: Optional[str] = None
    ) -> List[Absence]:
        pass

    @abstractmethod
    def create(self, absence: Absence) -> Absence:
        pass

    @abstractmethod
    def update(self, absence: Absence) -> Absence:
        pass


class ILocationLogRepository(ABC):
    @abstractmethod
    def create(self, log: LocationLog) -> LocationLog:
        pass

    @abstractmethod
    def list_for_user(self, user_id: int, limit: int = 50) -> List[LocationLog]:
        pass

    @abstractmethod
    def cleanup_older_than(self, days: int = 90) -> int:
        pass


class IConsentRepository(ABC):
    @abstractmethod
    def get_for_user(self, user_id: int) -> Optional[Consent]:
        pass

    @abstractmethod
    def create_or_update(self, user_id: int, is_granted: bool, consent_version: str = "1.0", consent_text: str = "") -> Consent:
        pass

