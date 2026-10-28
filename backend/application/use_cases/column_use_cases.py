from typing import Dict, Any, List
from backend.application.interfaces.uow import IUnitOfWork
from backend.application.interfaces.services import ITranslationService
from backend.application.dtos import ColumnCreateDTO, ColumnUpdateDTO, ReorderColumnsDTO
from backend.domain.entities import User, Column
from backend.domain.services import AccessPolicyService
from backend.domain.exceptions import EntityNotFoundException, ValidationException


class CreateColumnUseCase:
    def __init__(self, uow: IUnitOfWork, translation_service: ITranslationService):
        self.uow = uow
        self.translation_service = translation_service

    def execute(self, current_user: User, dto: ColumnCreateDTO) -> Dict[str, Any]:
        with self.uow:
            assigned_board_id = self.uow.users.get_assigned_board_id(current_user.id)
            AccessPolicyService.ensure_can_manage_board_structure(current_user, dto.board_id, assigned_board_id)

            if not dto.title.strip():
                raise ValidationException("Column title is required.")

            translations = self.translation_service.translate_multilingual(dto.title.strip(), dto.language)
            cols = self.uow.columns.list_by_board(dto.board_id)
            order = dto.order if dto.order is not None else len(cols)

            col = Column(
                id=None,
                board_id=dto.board_id,
                title_ru=translations.get("ru", dto.title),
                title_zh=translations.get("zh", dto.title),
                title_ky=translations.get("ky", dto.title),
                original_lang=dto.language or "ru",
                order=order,
            )
            created = self.uow.columns.create(col)
            self.uow.commit()

            return {
                "id": created.id,
                "board_id": created.board_id,
                "title_ru": created.title_ru,
                "title_zh": created.title_zh,
                "title_ky": created.title_ky,
                "original_lang": created.original_lang,
                "order": created.order,
                "cards_count": 0,
                "cards": [],
            }


class UpdateColumnUseCase:
    def __init__(self, uow: IUnitOfWork, translation_service: ITranslationService):
        self.uow = uow
        self.translation_service = translation_service

    def execute(self, current_user: User, column_id: int, dto: ColumnUpdateDTO) -> Dict[str, Any]:
        with self.uow:
            column = self.uow.columns.get_by_id(column_id)
            if not column:
                raise EntityNotFoundException("Column", column_id)

            assigned_board_id = self.uow.users.get_assigned_board_id(current_user.id)
            AccessPolicyService.ensure_can_manage_board_structure(current_user, column.board_id, assigned_board_id)

            if dto.title is not None and dto.title.strip():
                translations = self.translation_service.translate_multilingual(dto.title.strip(), dto.language)
                column.title_ru = translations.get("ru", dto.title)
                column.title_zh = translations.get("zh", dto.title)
                column.title_ky = translations.get("ky", dto.title)
                column.original_lang = dto.language or "ru"

            if dto.order is not None:
                column.order = dto.order

            updated = self.uow.columns.update(column)
            self.uow.commit()

            return {
                "id": updated.id,
                "board_id": updated.board_id,
                "title_ru": updated.title_ru,
                "title_zh": updated.title_zh,
                "title_ky": updated.title_ky,
                "original_lang": updated.original_lang,
                "order": updated.order,
            }


class DeleteColumnUseCase:
    def __init__(self, uow: IUnitOfWork):
        self.uow = uow

    def execute(self, current_user: User, column_id: int) -> bool:
        with self.uow:
            column = self.uow.columns.get_by_id(column_id)
            if not column:
                raise EntityNotFoundException("Column", column_id)

            assigned_board_id = self.uow.users.get_assigned_board_id(current_user.id)
            AccessPolicyService.ensure_can_manage_board_structure(current_user, column.board_id, assigned_board_id)

            deleted = self.uow.columns.delete(column_id)
            self.uow.commit()
            return deleted


class ReorderColumnsUseCase:
    def __init__(self, uow: IUnitOfWork):
        self.uow = uow

    def execute(self, current_user: User, dto: ReorderColumnsDTO) -> None:
        with self.uow:
            assigned_board_id = self.uow.users.get_assigned_board_id(current_user.id)
            AccessPolicyService.ensure_can_manage_board_structure(current_user, dto.board_id, assigned_board_id)

            order_map = {item["id"]: item["order"] for item in dto.column_orders}
            self.uow.columns.reorder(dto.board_id, order_map)
            self.uow.commit()
