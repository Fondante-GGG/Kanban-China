from typing import Dict, Any
from backend.application.interfaces.uow import IUnitOfWork
from backend.application.interfaces.services import ITranslationService
from backend.application.dtos import CommentCreateDTO
from backend.domain.entities import User, Comment, ActivityLog, Notification
from backend.domain.value_objects import ActivityAction
from backend.domain.services import AccessPolicyService
from backend.domain.exceptions import EntityNotFoundException, ValidationException, PermissionDeniedException


class AddCommentUseCase:
    def __init__(self, uow: IUnitOfWork, translation_service: ITranslationService):
        self.uow = uow
        self.translation_service = translation_service

    def execute(self, current_user: User, dto: CommentCreateDTO) -> Dict[str, Any]:
        with self.uow:
            card = self.uow.cards.get_by_id(dto.card_id)
            if not card:
                raise EntityNotFoundException("Card", dto.card_id)

            column = self.uow.columns.get_by_id(card.column_id)
            assigned_board_id = self.uow.users.get_assigned_board_id(current_user.id)
            AccessPolicyService.ensure_can_comment(current_user, column.board_id, assigned_board_id)

            if not dto.text.strip():
                raise ValidationException("Comment text cannot be empty.")

            # Translate comment across ru, zh, ky
            trans = self.translation_service.translate_multilingual(dto.text.strip(), dto.language)

            comment = Comment(
                id=None,
                card_id=dto.card_id,
                user_id=current_user.id,
                text_ru=trans.get("ru", dto.text),
                text_zh=trans.get("zh", dto.text),
                text_ky=trans.get("ky", dto.text),
                original_lang=dto.language or "ru",
            )
            created = self.uow.comments.create(comment)

            # Activity log
            log = ActivityLog(
                id=None,
                card_id=dto.card_id,
                user_id=current_user.id,
                action_type=ActivityAction.COMMENTED.value,
                details="Оставил(а) комментарий",
            )
            self.uow.activity_logs.create(log)

            # Notify assignees and creator
            assignees = self.uow.cards.get_assignees(dto.card_id)
            recipients = {a.id for a in assignees}
            if card.created_by_id:
                recipients.add(card.created_by_id)
            recipients.discard(current_user.id)

            snippet = dto.text[:40] + "..." if len(dto.text) > 40 else dto.text
            for uid in recipients:
                notif = Notification(
                    id=None,
                    user_id=uid,
                    title="Новый комментарий",
                    message=f"{current_user.full_name}: «{snippet}» в задаче «{card.title_ru}»",
                    entity_type="comment",
                    entity_id=card.id,
                    is_read=False,
                )
                self.uow.notifications.create(notif)

            self.uow.commit()

            return {
                "id": created.id,
                "card_id": created.card_id,
                "user_id": current_user.id,
                "user_full_name": current_user.full_name,
                "user_role": current_user.role,
                "text_ru": created.text_ru,
                "text_zh": created.text_zh,
                "text_ky": created.text_ky,
                "original_lang": created.original_lang,
                "created_at": created.created_at.isoformat() if created.created_at else None,
            }


class DeleteCommentUseCase:
    def __init__(self, uow: IUnitOfWork):
        self.uow = uow

    def execute(self, current_user: User, comment_id: int) -> bool:
        with self.uow:
            comment = self.uow.comments.get_by_id(comment_id)
            if not comment:
                raise EntityNotFoundException("Comment", comment_id)
            card = self.uow.cards.get_by_id(comment.card_id)
            column = self.uow.columns.get_by_id(card.column_id)
            assigned_board_id = self.uow.users.get_assigned_board_id(current_user.id)
            AccessPolicyService.ensure_can_view_board(current_user, column.board_id, assigned_board_id)
            if comment.user_id != current_user.id:
                AccessPolicyService.ensure_can_manage_cards(current_user, column.board_id, assigned_board_id)
            deleted = self.uow.comments.delete(comment_id)
            self.uow.commit()
            return deleted
