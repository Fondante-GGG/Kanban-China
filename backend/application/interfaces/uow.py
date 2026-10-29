from abc import ABC, abstractmethod
from types import TracebackType
from typing import Optional, Type
from backend.application.interfaces.repositories import (
    IUserRepository,
    IDepartmentRepository,
    IBoardRepository,
    IColumnRepository,
    ICardRepository,
    IChecklistRepository,
    ICommentRepository,
    IAttachmentRepository,
    IActivityLogRepository,
    INotificationRepository,
    IOfficeRepository,
    IWorkScheduleRepository,
    IAttendanceRecordRepository,
    IAbsenceRepository,
    ILocationLogRepository,
    IConsentRepository
)


class IUnitOfWork(ABC):
    users: IUserRepository
    departments: IDepartmentRepository
    boards: IBoardRepository
    columns: IColumnRepository
    cards: ICardRepository
    checklists: IChecklistRepository
    comments: ICommentRepository
    attachments: IAttachmentRepository
    activity_logs: IActivityLogRepository
    notifications: INotificationRepository
    offices: IOfficeRepository
    work_schedules: IWorkScheduleRepository
    attendance_records: IAttendanceRecordRepository
    absences: IAbsenceRepository
    location_logs: ILocationLogRepository
    consents: IConsentRepository

    @abstractmethod
    def __enter__(self) -> "IUnitOfWork":
        pass

    @abstractmethod
    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType]
    ) -> None:
        pass

    @abstractmethod
    def commit(self) -> None:
        pass

    @abstractmethod
    def rollback(self) -> None:
        pass
