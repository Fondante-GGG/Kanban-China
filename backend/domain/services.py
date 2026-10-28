from typing import Optional
from backend.domain.entities import User
from backend.domain.exceptions import PermissionDeniedException


class AccessPolicyService:
    """Domain service enforcing access control business rules defined in Section 2 & 5 of the specification."""

    @staticmethod
    def ensure_can_view_board(user: User, board_id: int, user_assigned_board_id: Optional[int]) -> None:
        if user.is_general_director:
            return
        if user_assigned_board_id != board_id:
            raise PermissionDeniedException(
                "Access denied: You can only access your designated department board."
            )

    @staticmethod
    def ensure_can_manage_board_structure(user: User, board_id: int, user_assigned_board_id: Optional[int]) -> None:
        """Creating, renaming, reordering or deleting columns (sections)"""
        if user.is_general_director:
            return
        if user.is_manager and (user_assigned_board_id == board_id or user_assigned_board_id is None):
            return
        raise PermissionDeniedException(
            "Access denied: Only General Director and Department Managers can manage and move sections. Employees cannot."
        )

    @staticmethod
    def ensure_can_manage_cards(user: User, board_id: int, user_assigned_board_id: Optional[int]) -> None:
        """Creating, editing, or deleting cards"""
        if user.is_general_director:
            return
        if user.is_manager and user_assigned_board_id == board_id:
            return
        raise PermissionDeniedException(
            "Access denied: Employees cannot create, modify or delete cards."
        )

    @staticmethod
    def ensure_can_move_card(user: User, board_id: int, user_assigned_board_id: Optional[int]) -> None:
        """Moving cards between columns"""
        if user.is_general_director:
            return
        if (user.is_manager or user.is_employee) and user_assigned_board_id == board_id:
            return
        raise PermissionDeniedException(
            "Access denied: You can only move cards within your assigned board."
        )

    @staticmethod
    def ensure_can_comment(user: User, board_id: int, user_assigned_board_id: Optional[int]) -> None:
        """Adding comments"""
        if user.is_general_director:
            return
        if (user.is_manager or user.is_employee) and user_assigned_board_id == board_id:
            return
        raise PermissionDeniedException(
            "Access denied: You can only comment on cards within your assigned board."
        )

    @staticmethod
    def ensure_can_view_reports(user: User) -> None:
        """Viewing statistics and reports"""
        if not user.is_general_director:
            raise PermissionDeniedException(
                "Access denied: Only General Director can view and export organizational reports."
            )

    @staticmethod
    def ensure_can_manage_users(user: User) -> None:
        """Admin capabilities for user & board administration"""
        if not user.is_general_director:
            raise PermissionDeniedException(
                "Access denied: Administrator privileges required."
            )
