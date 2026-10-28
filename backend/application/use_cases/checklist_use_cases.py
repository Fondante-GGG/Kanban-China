from typing import Dict, Any
from backend.application.interfaces.uow import IUnitOfWork
from backend.application.dtos import ChecklistItemCreateDTO
from backend.domain.entities import User, ChecklistItem, ActivityLog
from backend.domain.value_objects import ActivityAction
from backend.domain.services import AccessPolicyService
from backend.domain.exceptions import EntityNotFoundException, ValidationException


class AddChecklistItemUseCase:
    def __init__(self, uow: IUnitOfWork):
        self.uow = uow

    def execute(self, current_user: User, dto: ChecklistItemCreateDTO) -> Dict[str, Any]:
        with self.uow:
            card = self.uow.cards.get_by_id(dto.card_id)
            if not card:
                raise EntityNotFoundException("Card", dto.card_id)

            column = self.uow.columns.get_by_id(card.column_id)
            assigned_board_id = self.uow.users.get_assigned_board_id(current_user.id)
            # Allowed for director, manager, or board members
            AccessPolicyService.ensure_can_move_card(current_user, column.board_id, assigned_board_id)

            if not dto.title.strip():
                raise ValidationException("Checklist item title cannot be empty.")

            items = self.uow.checklists.list_by_card(dto.card_id)
            item = ChecklistItem(
                id=None,
                card_id=dto.card_id,
                title=dto.title.strip(),
                is_completed=False,
                order=len(items),
            )
            created = self.uow.checklists.create(item)

            log = ActivityLog(
                id=None,
                card_id=dto.card_id,
                user_id=current_user.id,
                action_type=ActivityAction.UPDATED.value,
                details=f"Добавил(а) пункт чек-листа: «{dto.title.strip()}»",
            )
            self.uow.activity_logs.create(log)

            self.uow.commit()

            return {
                "id": created.id,
                "card_id": created.card_id,
                "title": created.title,
                "is_completed": created.is_completed,
                "order": created.order,
            }


class ToggleChecklistItemUseCase:
    def __init__(self, uow: IUnitOfWork):
        self.uow = uow

    def execute(self, current_user: User, item_id: int) -> Dict[str, Any]:
        with self.uow:
            item = self.uow.checklists.get_by_id(item_id)
            if not item:
                raise EntityNotFoundException("ChecklistItem", item_id)

            card = self.uow.cards.get_by_id(item.card_id)
            column = self.uow.columns.get_by_id(card.column_id)
            assigned_board_id = self.uow.users.get_assigned_board_id(current_user.id)
            AccessPolicyService.ensure_can_move_card(current_user, column.board_id, assigned_board_id)

            item.is_completed = not item.is_completed
            updated = self.uow.checklists.update(item)

            state_str = "выполнил(а)" if item.is_completed else "снял(а) отметку с"
            log = ActivityLog(
                id=None,
                card_id=item.card_id,
                user_id=current_user.id,
                action_type=ActivityAction.CHECKLIST_TOGGLED.value,
                details=f"{state_str} пункта «{item.title}»",
            )
            self.uow.activity_logs.create(log)

            self.uow.commit()

            return {
                "id": updated.id,
                "card_id": updated.card_id,
                "title": updated.title,
                "is_completed": updated.is_completed,
                "order": updated.order,
            }


class DeleteChecklistItemUseCase:
    def __init__(self, uow: IUnitOfWork):
        self.uow = uow

    def execute(self, current_user: User, item_id: int) -> bool:
        with self.uow:
            item = self.uow.checklists.get_by_id(item_id)
            if not item:
                raise EntityNotFoundException("ChecklistItem", item_id)

            card = self.uow.cards.get_by_id(item.card_id)
            column = self.uow.columns.get_by_id(card.column_id)
            assigned_board_id = self.uow.users.get_assigned_board_id(current_user.id)
            AccessPolicyService.ensure_can_move_card(current_user, column.board_id, assigned_board_id)

            deleted = self.uow.checklists.delete(item_id)
            self.uow.commit()
            return deleted
