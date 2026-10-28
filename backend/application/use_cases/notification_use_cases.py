from typing import List, Dict, Any
from backend.application.interfaces.uow import IUnitOfWork
from backend.domain.entities import User


class GetNotificationsUseCase:
    def __init__(self, uow: IUnitOfWork):
        self.uow = uow

    def execute(self, current_user: User, unread_only: bool = False) -> List[Dict[str, Any]]:
        with self.uow:
            notifs = self.uow.notifications.list_by_user(current_user.id, unread_only)
            return [
                {
                    "id": n.id,
                    "title": n.title,
                    "message": n.message,
                    "entity_type": n.entity_type,
                    "entity_id": n.entity_id,
                    "is_read": n.is_read,
                    "created_at": n.created_at.isoformat() if n.created_at else None,
                }
                for n in notifs
            ]


class MarkNotificationsReadUseCase:
    def __init__(self, uow: IUnitOfWork):
        self.uow = uow

    def execute(self, current_user: User, notification_id: int = None) -> None:
        with self.uow:
            if notification_id:
                self.uow.notifications.mark_as_read(notification_id, current_user.id)
            else:
                self.uow.notifications.mark_all_as_read(current_user.id)
            self.uow.commit()
