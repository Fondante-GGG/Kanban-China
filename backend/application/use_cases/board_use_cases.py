from typing import List, Dict, Any, Optional
from backend.application.interfaces.uow import IUnitOfWork
from backend.application.interfaces.services import ITranslationService
from backend.application.dtos import BoardCreateDTO, BoardUpdateDTO
from backend.domain.entities import User, Board, Column
from backend.domain.services import AccessPolicyService
from backend.domain.exceptions import EntityNotFoundException, ValidationException

DEFAULT_TEMPLATE_COLUMNS = [
    {"ru": "Нужно сделать", "zh": "待办事项", "ky": "Керектуу иштер"},
    {"ru": "Баги", "zh": "缺陷与错误", "ky": "Мүчүлүштүктөр"},
    {"ru": "В процессе фронт", "zh": "前端开发中", "ky": "Фронтенд иштеп жатат"},
    {"ru": "В процессе бэк", "zh": "后端开发中", "ky": "Бэкенд иштеп жатат"},
    {"ru": "На проверке", "zh": "待审核", "ky": "Текшерүүдө"},
    {"ru": "Готово", "zh": "已完成", "ky": "Даяр болду"},
]


class ListBoardsUseCase:
    def __init__(self, uow: IUnitOfWork):
        self.uow = uow

    def execute(self, current_user: User) -> List[Dict[str, Any]]:
        with self.uow:
            if current_user.is_general_director:
                all_depts = self.uow.departments.list_all()
                existing_boards = self.uow.boards.list_all()
                existing_dept_ids = {b.department_id for b in existing_boards if b.department_id}

                created_any = False
                for dept in all_depts:
                    if dept.id not in existing_dept_ids:
                        new_board = Board(
                            id=None,
                            title=dept.name,
                            department_id=dept.id,
                            background_theme="gradient-blue",
                            is_archived=False,
                        )
                        created_b = self.uow.boards.create(new_board)
                        for idx, col_template in enumerate(DEFAULT_TEMPLATE_COLUMNS):
                            col = Column(
                                id=None,
                                board_id=created_b.id,
                                title_ru=col_template["ru"],
                                title_zh=col_template["zh"],
                                title_ky=col_template["ky"],
                                original_lang="ru",
                                order=idx,
                            )
                            self.uow.columns.create(col)
                        created_any = True

                if created_any:
                    self.uow.commit()

                boards = self.uow.boards.list_all()
            else:
                assigned_board_id = self.uow.users.get_assigned_board_id(current_user.id)
                if not assigned_board_id:
                    return []
                board = self.uow.boards.get_by_id(assigned_board_id)
                boards = [board] if board and not board.is_archived else []

            res = []
            for b in boards:
                dept = self.uow.departments.get_by_id(b.department_id) if b.department_id else None
                members = self.uow.boards.get_members(b.id)
                cols = self.uow.columns.list_by_board(b.id)
                cards = self.uow.cards.list_by_board(b.id)
                res.append({
                    "id": b.id,
                    "title": b.title,
                    "department_id": b.department_id,
                    "department_name": dept.name if dept else None,
                    "background_theme": b.background_theme,
                    "is_archived": b.is_archived,
                    "columns_count": len(cols),
                    "cards_count": len(cards),
                    "members_count": len(members),
                    "created_at": b.created_at.isoformat() if b.created_at else None,
                })
            return res


class GetBoardDetailsUseCase:
    def __init__(self, uow: IUnitOfWork):
        self.uow = uow

    def execute(self, current_user: User, board_id: int, search: Optional[str] = None, priority: Optional[str] = None, assignee_id: Optional[int] = None) -> Dict[str, Any]:
        with self.uow:
            assigned_board_id = self.uow.users.get_assigned_board_id(current_user.id)
            AccessPolicyService.ensure_can_view_board(current_user, board_id, assigned_board_id)

            board = self.uow.boards.get_by_id(board_id)
            if not board:
                raise EntityNotFoundException("Board", board_id)

            dept = self.uow.departments.get_by_id(board.department_id) if board.department_id else None
            members = self.uow.boards.get_members(board.id)
            columns = self.uow.columns.list_by_board(board.id)
            cards = self.uow.cards.list_by_board(board.id, search=search, priority=priority, assignee_id=assignee_id)

            # Group cards by column_id
            cards_by_column: Dict[int, List[Dict[str, Any]]] = {c.id: [] for c in columns}
            for card in cards:
                assignees = self.uow.cards.get_assignees(card.id)
                checklists = self.uow.checklists.list_by_card(card.id)
                completed_checklists = sum(1 for item in checklists if item.is_completed)
                total_checklists = len(checklists)
                comments = self.uow.comments.list_by_card(card.id)
                attachments = self.uow.attachments.list_by_card(card.id)

                card_data = {
                    "id": card.id,
                    "column_id": card.column_id,
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
                    "assignees": [
                        {
                            "id": a.id,
                            "full_name": a.full_name,
                            "email": a.email,
                            "role": a.role
                        } for a in assignees
                    ],
                    "checklists_summary": {
                        "total": total_checklists,
                        "completed": completed_checklists,
                    },
                    "comments_count": len(comments),
                    "attachments_count": len(attachments),
                }
                if card.column_id in cards_by_column:
                    cards_by_column[card.column_id].append(card_data)

            columns_data = []
            for c in columns:
                col_cards = cards_by_column.get(c.id, [])
                columns_data.append({
                    "id": c.id,
                    "board_id": c.board_id,
                    "title_ru": c.title_ru,
                    "title_zh": c.title_zh,
                    "title_ky": c.title_ky,
                    "original_lang": c.original_lang,
                    "order": c.order,
                    "cards_count": len(col_cards),
                    "cards": col_cards,
                })

            members_data = []
            for m in members:
                user = self.uow.users.get_by_id(m.user_id)
                if user:
                    members_data.append({
                        "user_id": user.id,
                        "full_name": user.full_name,
                        "email": user.email,
                        "board_role": m.role,
                        "system_role": user.role,
                    })

            user_permissions = {
                "can_manage_columns": current_user.is_general_director or (current_user.is_manager and assigned_board_id == board.id),
                "can_manage_cards": current_user.is_general_director or (current_user.is_manager and assigned_board_id == board.id),
                "can_move_cards": current_user.is_general_director or assigned_board_id == board.id,
                "can_comment": current_user.is_general_director or assigned_board_id == board.id,
            }

            return {
                "id": board.id,
                "title": board.title,
                "department_id": board.department_id,
                "department_name": dept.name if dept else None,
                "background_theme": board.background_theme,
                "is_archived": board.is_archived,
                "created_at": board.created_at.isoformat() if board.created_at else None,
                "members": members_data,
                "columns": columns_data,
                "permissions": user_permissions,
            }


class CreateBoardUseCase:
    def __init__(self, uow: IUnitOfWork, translation_service: ITranslationService):
        self.uow = uow
        self.translation_service = translation_service

    def execute(self, current_user: User, dto: BoardCreateDTO) -> Dict[str, Any]:
        AccessPolicyService.ensure_can_manage_users(current_user)
        if not dto.title.strip():
            raise ValidationException("Board title cannot be empty.")

        with self.uow:
            board = Board(
                id=None,
                title=dto.title.strip(),
                department_id=dto.department_id,
                background_theme=dto.background_theme or "gradient-blue",
                is_archived=False,
            )
            created_board = self.uow.boards.create(board)

            # Assign members
            self.uow.boards.set_members(
                created_board.id,
                dto.manager_id,
                dto.employee_ids or []
            )

            # Create default columns template
            for idx, col_template in enumerate(DEFAULT_TEMPLATE_COLUMNS):
                col = Column(
                    id=None,
                    board_id=created_board.id,
                    title_ru=col_template["ru"],
                    title_zh=col_template["zh"],
                    title_ky=col_template["ky"],
                    original_lang="ru",
                    order=idx,
                )
                self.uow.columns.create(col)

            self.uow.commit()

            return {
                "id": created_board.id,
                "title": created_board.title,
                "department_id": created_board.department_id,
                "background_theme": created_board.background_theme,
                "is_archived": created_board.is_archived,
            }


class UpdateBoardUseCase:
    def __init__(self, uow: IUnitOfWork):
        self.uow = uow

    def execute(self, current_user: User, board_id: int, dto: BoardUpdateDTO) -> Dict[str, Any]:
        AccessPolicyService.ensure_can_manage_users(current_user)
        with self.uow:
            board = self.uow.boards.get_by_id(board_id)
            if not board:
                raise EntityNotFoundException("Board", board_id)

            if dto.title is not None:
                board.title = dto.title.strip()
            if dto.department_id is not None:
                board.department_id = dto.department_id
            if dto.background_theme is not None:
                board.background_theme = dto.background_theme
            if dto.is_archived is not None:
                board.is_archived = dto.is_archived

            updated_board = self.uow.boards.update(board)

            if dto.manager_id is not None or dto.employee_ids is not None:
                members = self.uow.boards.get_members(board_id)
                current_mgr = dto.manager_id if dto.manager_id is not None else next((m.user_id for m in members if m.role == "manager"), None)
                current_emps = dto.employee_ids if dto.employee_ids is not None else [m.user_id for m in members if m.role == "employee"]
                self.uow.boards.set_members(board_id, current_mgr, current_emps)

            self.uow.commit()
            return {
                "id": updated_board.id,
                "title": updated_board.title,
                "department_id": updated_board.department_id,
                "background_theme": updated_board.background_theme,
                "is_archived": updated_board.is_archived,
            }


class DeleteBoardUseCase:
    def __init__(self, uow: IUnitOfWork):
        self.uow = uow

    def execute(self, current_user: User, board_id: int) -> bool:
        AccessPolicyService.ensure_can_manage_users(current_user)
        with self.uow:
            deleted = self.uow.boards.delete(board_id)
            self.uow.commit()
            return deleted
