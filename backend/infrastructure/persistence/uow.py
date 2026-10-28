from types import TracebackType
from typing import Optional, Type
from django.db import transaction
from backend.application.interfaces.uow import IUnitOfWork
from backend.infrastructure.persistence.repositories.django_repositories import (
    DjangoUserRepository,
    DjangoDepartmentRepository,
    DjangoBoardRepository,
    DjangoColumnRepository,
    DjangoCardRepository,
    DjangoChecklistRepository,
    DjangoCommentRepository,
    DjangoAttachmentRepository,
    DjangoActivityLogRepository,
    DjangoNotificationRepository,
)


class DjangoUnitOfWork(IUnitOfWork):
    def __init__(self):
        self.users = DjangoUserRepository()
        self.departments = DjangoDepartmentRepository()
        self.boards = DjangoBoardRepository()
        self.columns = DjangoColumnRepository()
        self.cards = DjangoCardRepository()
        self.checklists = DjangoChecklistRepository()
        self.comments = DjangoCommentRepository()
        self.attachments = DjangoAttachmentRepository()
        self.activity_logs = DjangoActivityLogRepository()
        self.notifications = DjangoNotificationRepository()
        self._atomic = None

    def __enter__(self) -> "DjangoUnitOfWork":
        self._atomic = transaction.atomic()
        self._atomic.__enter__()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType]
    ) -> None:
        if self._atomic:
            self._atomic.__exit__(exc_type, exc_val, exc_tb)

    def commit(self) -> None:
        # transaction.atomic commits automatically on exit if no exception was raised
        pass

    def rollback(self) -> None:
        transaction.set_rollback(True)
