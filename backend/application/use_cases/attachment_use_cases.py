from typing import Dict, Any
from backend.application.interfaces.uow import IUnitOfWork
from backend.domain.entities import User, Attachment, ActivityLog
from backend.domain.value_objects import ActivityAction
from backend.domain.services import AccessPolicyService
from backend.domain.exceptions import EntityNotFoundException


class UploadAttachmentUseCase:
    def __init__(self, uow: IUnitOfWork):
        self.uow = uow

    def execute(
        self,
        current_user: User,
        card_id: int,
        file_path: str,
        file_name: str,
        file_size: int,
        content_type: str
    ) -> Dict[str, Any]:
        with self.uow:
            card = self.uow.cards.get_by_id(card_id)
            if not card:
                raise EntityNotFoundException("Card", card_id)

            column = self.uow.columns.get_by_id(card.column_id)
            assigned_board_id = self.uow.users.get_assigned_board_id(current_user.id)
            AccessPolicyService.ensure_can_move_card(current_user, column.board_id, assigned_board_id)

            attachment = Attachment(
                id=None,
                card_id=card_id,
                file_path=file_path,
                file_name=file_name,
                file_size=file_size,
                content_type=content_type,
                uploaded_by_id=current_user.id,
            )
            created = self.uow.attachments.create(attachment)

            log = ActivityLog(
                id=None,
                card_id=card_id,
                user_id=current_user.id,
                action_type=ActivityAction.ATTACHMENT_ADDED.value,
                details=f"Прикрепил(а) файл: «{file_name}»",
            )
            self.uow.activity_logs.create(log)

            self.uow.commit()

            return {
                "id": created.id,
                "card_id": created.card_id,
                "file_path": created.file_path,
                "file_name": created.file_name,
                "file_size": created.file_size,
                "content_type": created.content_type,
                "uploaded_by_id": created.uploaded_by_id,
                "uploader_name": current_user.full_name,
                "created_at": created.created_at.isoformat() if created.created_at else None,
            }


class DeleteAttachmentUseCase:
    def __init__(self, uow: IUnitOfWork):
        self.uow = uow

    def execute(self, current_user: User, attachment_id: int) -> bool:
        with self.uow:
            attachment = self.uow.attachments.get_by_id(attachment_id)
            if not attachment:
                raise EntityNotFoundException("Attachment", attachment_id)

            deleted = self.uow.attachments.delete(attachment_id)
            self.uow.commit()
            return deleted
