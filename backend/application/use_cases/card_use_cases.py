from datetime import datetime
from typing import Dict, Any, List, Optional
from backend.application.interfaces.uow import IUnitOfWork
from backend.application.interfaces.services import ITranslationService
from backend.application.dtos import CardCreateDTO, CardUpdateDTO, CardMoveDTO
from backend.domain.entities import User, Card, ActivityLog, Notification
from backend.domain.value_objects import ActivityAction, CardPriority
from backend.domain.services import AccessPolicyService
from backend.domain.exceptions import EntityNotFoundException, ValidationException


def ensure_assignees_are_board_members(uow: IUnitOfWork, board_id: int, assignee_ids: List[int]) -> None:
    requested_ids = set(assignee_ids)
    member_ids = {member.user_id for member in uow.boards.get_members(board_id)}
    invalid_ids = requested_ids - member_ids
    if invalid_ids:
        raise ValidationException("Assignees must be active members of this board.")


class CreateCardUseCase:
    def __init__(self, uow: IUnitOfWork, translation_service: ITranslationService):
        self.uow = uow
        self.translation_service = translation_service

    def execute(self, current_user: User, dto: CardCreateDTO) -> Dict[str, Any]:
        with self.uow:
            column = self.uow.columns.get_by_id(dto.column_id)
            if not column:
                raise EntityNotFoundException("Column", dto.column_id)

            assigned_board_id = self.uow.users.get_assigned_board_id(current_user.id)
            AccessPolicyService.ensure_can_manage_cards(current_user, column.board_id, assigned_board_id)

            if not dto.title.strip():
                raise ValidationException("Card title is required.")

            # Translate title & description into ru, zh, ky
            title_trans = self.translation_service.translate_multilingual(dto.title.strip(), dto.language)
            desc_trans = self.translation_service.translate_multilingual(dto.description.strip(), dto.language) if dto.description else {"ru": "", "zh": "", "ky": ""}

            due_date_parsed = None
            if dto.due_date:
                try:
                    due_date_parsed = datetime.fromisoformat(dto.due_date.replace("Z", "+00:00"))
                except Exception:
                    due_date_parsed = None

            cards_in_col = self.uow.cards.list_by_column(dto.column_id)
            order = len(cards_in_col)

            card = Card(
                id=None,
                column_id=dto.column_id,
                title_ru=title_trans.get("ru", dto.title),
                title_zh=title_trans.get("zh", dto.title),
                title_ky=title_trans.get("ky", dto.title),
                desc_ru=desc_trans.get("ru", ""),
                desc_zh=desc_trans.get("zh", ""),
                desc_ky=desc_trans.get("ky", ""),
                original_lang=dto.language or "ru",
                priority=dto.priority or CardPriority.MEDIUM.value,
                due_date=due_date_parsed,
                order=order,
                created_by_id=current_user.id,
            )
            created_card = self.uow.cards.create(card)

            # Assign users
            if dto.assignee_ids:
                ensure_assignees_are_board_members(self.uow, column.board_id, dto.assignee_ids)
                self.uow.cards.set_assignees(created_card.id, dto.assignee_ids)
                # Create notification for each assignee
                for uid in dto.assignee_ids:
                    if uid != current_user.id:
                        notif = Notification(
                            id=None,
                            user_id=uid,
                            title="Назначена новая задача / 新任务分配 / Жаңы тапшырма дайындалды",
                            message=f"{current_user.full_name} назначил(а) вас на задачу: «{created_card.title_ru}»",
                            entity_type="card",
                            entity_id=created_card.id,
                            is_read=False,
                        )
                        self.uow.notifications.create(notif)

            # Log activity
            log = ActivityLog(
                id=None,
                card_id=created_card.id,
                user_id=current_user.id,
                action_type=ActivityAction.CREATED.value,
                details=f"Создал(а) задачу в колонке «{column.title_ru}»",
            )
            self.uow.activity_logs.create(log)

            self.uow.commit()

            assignees = self.uow.cards.get_assignees(created_card.id)
            return {
                "id": created_card.id,
                "column_id": created_card.column_id,
                "title_ru": created_card.title_ru,
                "title_zh": created_card.title_zh,
                "title_ky": created_card.title_ky,
                "desc_ru": created_card.desc_ru,
                "desc_zh": created_card.desc_zh,
                "desc_ky": created_card.desc_ky,
                "original_lang": created_card.original_lang,
                "priority": created_card.priority,
                "due_date": created_card.due_date.isoformat() if created_card.due_date else None,
                "order": created_card.order,
                "created_by_id": created_card.created_by_id,
                "created_at": created_card.created_at.isoformat() if created_card.created_at else None,
                "assignees": [{"id": a.id, "full_name": a.full_name, "email": a.email, "role": a.role} for a in assignees],
                "checklists_summary": {"total": 0, "completed": 0},
                "comments_count": 0,
                "attachments_count": 0,
            }


class UpdateCardUseCase:
    def __init__(self, uow: IUnitOfWork, translation_service: ITranslationService):
        self.uow = uow
        self.translation_service = translation_service

    def execute(self, current_user: User, card_id: int, dto: CardUpdateDTO) -> Dict[str, Any]:
        with self.uow:
            card = self.uow.cards.get_by_id(card_id)
            if not card:
                raise EntityNotFoundException("Card", card_id)

            column = self.uow.columns.get_by_id(card.column_id)
            assigned_board_id = self.uow.users.get_assigned_board_id(current_user.id)
            AccessPolicyService.ensure_can_manage_cards(current_user, column.board_id, assigned_board_id)

            details_changed = []

            if dto.title is not None and dto.title.strip():
                trans = self.translation_service.translate_multilingual(dto.title.strip(), dto.language)
                card.title_ru = trans.get("ru", dto.title)
                card.title_zh = trans.get("zh", dto.title)
                card.title_ky = trans.get("ky", dto.title)
                card.original_lang = dto.language or "ru"
                details_changed.append("название")

            if dto.description is not None:
                if dto.description.strip():
                    trans = self.translation_service.translate_multilingual(dto.description.strip(), dto.language)
                    card.desc_ru = trans.get("ru", "")
                    card.desc_zh = trans.get("zh", "")
                    card.desc_ky = trans.get("ky", "")
                else:
                    card.desc_ru = ""
                    card.desc_zh = ""
                    card.desc_ky = ""
                details_changed.append("описание")

            if dto.priority is not None:
                card.priority = dto.priority
                details_changed.append("приоритет")

            if dto.due_date is not None:
                if dto.due_date:
                    try:
                        card.due_date = datetime.fromisoformat(dto.due_date.replace("Z", "+00:00"))
                    except Exception:
                        pass
                else:
                    card.due_date = None
                details_changed.append("срок")

            updated_card = self.uow.cards.update(card)

            if dto.assignee_ids is not None:
                ensure_assignees_are_board_members(self.uow, column.board_id, dto.assignee_ids)
                old_assignees = self.uow.cards.get_assignees(card_id)
                old_ids = {a.id for a in old_assignees}
                new_ids = set(dto.assignee_ids)
                self.uow.cards.set_assignees(card_id, dto.assignee_ids)

                newly_added = new_ids - old_ids
                for uid in newly_added:
                    if uid != current_user.id:
                        notif = Notification(
                            id=None,
                            user_id=uid,
                            title="Назначена задача",
                            message=f"{current_user.full_name} назначил(а) вас на задачу: «{updated_card.title_ru}»",
                            entity_type="card",
                            entity_id=card_id,
                            is_read=False,
                        )
                        self.uow.notifications.create(notif)
                details_changed.append("исполнителей")

            if details_changed:
                log = ActivityLog(
                    id=None,
                    card_id=card_id,
                    user_id=current_user.id,
                    action_type=ActivityAction.UPDATED.value,
                    details=f"Изменил(а) {', '.join(details_changed)}",
                )
                self.uow.activity_logs.create(log)

            self.uow.commit()

            assignees = self.uow.cards.get_assignees(card_id)
            return {
                "id": updated_card.id,
                "column_id": updated_card.column_id,
                "title_ru": updated_card.title_ru,
                "title_zh": updated_card.title_zh,
                "title_ky": updated_card.title_ky,
                "desc_ru": updated_card.desc_ru,
                "desc_zh": updated_card.desc_zh,
                "desc_ky": updated_card.desc_ky,
                "original_lang": updated_card.original_lang,
                "priority": updated_card.priority,
                "due_date": updated_card.due_date.isoformat() if updated_card.due_date else None,
                "order": updated_card.order,
                "assignees": [{"id": a.id, "full_name": a.full_name, "email": a.email, "role": a.role} for a in assignees],
            }


class MoveCardUseCase:
    def __init__(self, uow: IUnitOfWork):
        self.uow = uow

    def execute(self, current_user: User, card_id: int, dto: CardMoveDTO) -> Dict[str, Any]:
        with self.uow:
            card = self.uow.cards.get_by_id(card_id)
            if not card:
                raise EntityNotFoundException("Card", card_id)

            old_col = self.uow.columns.get_by_id(card.column_id)
            target_col = self.uow.columns.get_by_id(dto.target_column_id)
            if not target_col:
                raise EntityNotFoundException("Column", dto.target_column_id)

            # Both columns must belong to the same board
            if old_col.board_id != target_col.board_id:
                raise ValidationException("Cards cannot be moved across different boards.")

            assigned_board_id = self.uow.users.get_assigned_board_id(current_user.id)
            # Ensure user has permission to move card on this board (Director, Manager, Employee)
            AccessPolicyService.ensure_can_move_card(current_user, target_col.board_id, assigned_board_id)

            moved_card = self.uow.cards.move(card_id, dto.target_column_id, dto.target_order)

            # Activity log
            log = ActivityLog(
                id=None,
                card_id=card_id,
                user_id=current_user.id,
                action_type=ActivityAction.MOVED.value,
                details=f"Переместил(а) задачу из «{old_col.title_ru}» в «{target_col.title_ru}»",
            )
            self.uow.activity_logs.create(log)

            # Notify assignees
            assignees = self.uow.cards.get_assignees(card_id)
            for a in assignees:
                if a.id != current_user.id:
                    notif = Notification(
                        id=None,
                        user_id=a.id,
                        title="Карточка перемещена",
                        message=f"{current_user.full_name} переместил(а) карточку «{moved_card.title_ru}» в раздел «{target_col.title_ru}»",
                        entity_type="card",
                        entity_id=card_id,
                        is_read=False,
                    )
                    self.uow.notifications.create(notif)

            self.uow.commit()

            return {
                "id": moved_card.id,
                "column_id": moved_card.column_id,
                "order": moved_card.order,
            }


class DeleteCardUseCase:
    def __init__(self, uow: IUnitOfWork):
        self.uow = uow

    def execute(self, current_user: User, card_id: int) -> bool:
        with self.uow:
            card = self.uow.cards.get_by_id(card_id)
            if not card:
                raise EntityNotFoundException("Card", card_id)

            column = self.uow.columns.get_by_id(card.column_id)
            assigned_board_id = self.uow.users.get_assigned_board_id(current_user.id)
            AccessPolicyService.ensure_can_manage_cards(current_user, column.board_id, assigned_board_id)

            deleted = self.uow.cards.delete(card_id)
            self.uow.commit()
            return deleted


class GetCardDetailUseCase:
    def __init__(self, uow: IUnitOfWork):
        self.uow = uow

    def execute(self, current_user: User, card_id: int) -> Dict[str, Any]:
        with self.uow:
            card = self.uow.cards.get_by_id(card_id)
            if not card:
                raise EntityNotFoundException("Card", card_id)

            column = self.uow.columns.get_by_id(card.column_id)
            assigned_board_id = self.uow.users.get_assigned_board_id(current_user.id)
            AccessPolicyService.ensure_can_view_board(current_user, column.board_id, assigned_board_id)

            assignees = self.uow.cards.get_assignees(card_id)
            checklists = self.uow.checklists.list_by_card(card_id)
            comments = self.uow.comments.list_by_card(card_id)
            attachments = self.uow.attachments.list_by_card(card_id)
            activities = self.uow.activity_logs.list_by_card(card_id)

            board_members = self.uow.boards.get_members(column.board_id)
            board_users = []
            for bm in board_members:
                u = self.uow.users.get_by_id(bm.user_id)
                if u:
                    board_users.append({
                        "id": u.id,
                        "full_name": u.full_name,
                        "email": u.email,
                        "role": u.role,
                    })

            return {
                "id": card.id,
                "column_id": card.column_id,
                "column_title_ru": column.title_ru,
                "column_title_zh": column.title_zh,
                "column_title_ky": column.title_ky,
                "board_id": column.board_id,
                "title_ru": card.title_ru,
                "title_zh": card.title_zh,
                "title_ky": card.title_ky,
                "desc_ru": card.desc_ru,
                "desc_zh": card.desc_zh,
                "desc_ky": card.desc_ky,
                "original_lang": card.original_lang,
                "priority": card.priority,
                "due_date": card.due_date.isoformat() if card.due_date else None,
                "order": card.order,
                "created_by_id": card.created_by_id,
                "created_at": card.created_at.isoformat() if card.created_at else None,
                "assignees": [{"id": a.id, "full_name": a.full_name, "email": a.email, "role": a.role} for a in assignees],
                "checklists": [
                    {
                        "id": c.id,
                        "title": c.title,
                        "is_completed": c.is_completed,
                        "order": c.order,
                    } for c in checklists
                ],
                "comments": [
                    {
                        "id": c.id,
                        "user_id": c.user_id,
                        "user_full_name": c.user_full_name,
                        "user_role": c.user_role,
                        "text_ru": c.text_ru,
                        "text_zh": c.text_zh,
                        "text_ky": c.text_ky,
                        "original_lang": c.original_lang,
                        "created_at": c.created_at.isoformat() if c.created_at else None,
                    } for c in comments
                ],
                "attachments": [
                    {
                        "id": a.id,
                        "file_path": f"/api/attachments/{a.id}/download",
                        "file_name": a.file_name,
                        "file_size": a.file_size,
                        "content_type": a.content_type,
                        "uploaded_by_id": a.uploaded_by_id,
                        "uploader_name": a.uploader_name,
                        "created_at": a.created_at.isoformat() if a.created_at else None,
                    } for a in attachments
                ],
                "activities": [
                    {
                        "id": act.id,
                        "action_type": act.action_type,
                        "details": act.details,
                        "user_full_name": act.user_full_name,
                        "created_at": act.created_at.isoformat() if act.created_at else None,
                    } for act in activities
                ],
                "available_assignees": board_users,
                "permissions": {
                    "can_manage_card": current_user.is_general_director or (current_user.is_manager and assigned_board_id == column.board_id),
                    "can_move_card": current_user.is_general_director or assigned_board_id == column.board_id,
                    "can_comment": current_user.is_general_director or assigned_board_id == column.board_id,
                }
            }
