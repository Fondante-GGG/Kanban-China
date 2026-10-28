from typing import List, Dict, Any, Optional
from django.contrib.auth.hashers import make_password
from backend.application.interfaces.uow import IUnitOfWork
from backend.application.dtos import UserCreateDTO, UserUpdateDTO
from backend.domain.entities import User
from backend.domain.value_objects import RoleType
from backend.domain.services import AccessPolicyService
from backend.domain.exceptions import ValidationException, EntityNotFoundException


class ListUsersUseCase:
    def __init__(self, uow: IUnitOfWork):
        self.uow = uow

    def execute(self, current_user: User, department_id: Optional[int] = None) -> List[Dict[str, Any]]:
        AccessPolicyService.ensure_can_manage_users(current_user)
        with self.uow:
            users = self.uow.users.list_all(department_id)
            result = []
            for u in users:
                board_id = self.uow.users.get_assigned_board_id(u.id)
                dept_name = None
                if u.department_id:
                    dept = self.uow.departments.get_by_id(u.department_id)
                    dept_name = dept.name if dept else None
                board_title = None
                if board_id:
                    board = self.uow.boards.get_by_id(board_id)
                    board_title = board.title if board else None

                result.append({
                    "id": u.id,
                    "email": u.email,
                    "full_name": u.full_name,
                    "role": u.role,
                    "department_id": u.department_id,
                    "department_name": dept_name,
                    "assigned_board_id": board_id,
                    "assigned_board_title": board_title,
                    "phone": u.phone,
                    "interface_language": u.interface_language,
                    "is_active": u.is_active,
                    "created_at": u.created_at.isoformat() if u.created_at else None,
                })
            return result


class CreateUserUseCase:
    def __init__(self, uow: IUnitOfWork):
        self.uow = uow

    def execute(self, current_user: User, dto: UserCreateDTO) -> Dict[str, Any]:
        AccessPolicyService.ensure_can_manage_users(current_user)

        if not dto.email or "@" not in dto.email:
            raise ValidationException("Valid email is required.")
        if not dto.password or len(dto.password) < 6:
            raise ValidationException("Password must be at least 6 characters.")
        if not dto.full_name.strip():
            raise ValidationException("Full name is required.")
        if dto.role not in RoleType.list():
            raise ValidationException(f"Invalid role. Must be one of: {RoleType.list()}")

        with self.uow:
            existing = self.uow.users.get_by_email(dto.email.strip().lower())
            if existing:
                raise ValidationException("User with this email already exists.")

            user = User(
                id=None,
                email=dto.email.strip().lower(),
                password_hash=make_password(dto.password),
                full_name=dto.full_name.strip(),
                role=dto.role,
                department_id=dto.department_id,
                interface_language=dto.interface_language or "ru",
                phone=dto.phone.strip() if dto.phone else None,
                is_active=True
            )
            created_user = self.uow.users.create(user)

            # Assign to board if specified and not general director (or even if director)
            target_board_id = dto.board_id
            if not target_board_id and dto.department_id:
                all_b = self.uow.boards.list_all()
                for b in all_b:
                    if b.department_id == dto.department_id:
                        target_board_id = b.id
                        break

            if target_board_id:
                # Update board membership
                board = self.uow.boards.get_by_id(target_board_id)
                if board:
                    members = self.uow.boards.get_members(target_board_id)
                    current_mgr = None
                    emp_ids = []
                    for m in members:
                        if m.role == "manager":
                            current_mgr = m.user_id
                        else:
                            emp_ids.append(m.user_id)

                    if dto.role == RoleType.MANAGER.value:
                        current_mgr = created_user.id
                    elif dto.role == RoleType.EMPLOYEE.value and created_user.id not in emp_ids:
                        emp_ids.append(created_user.id)

                    self.uow.boards.set_members(target_board_id, current_mgr, emp_ids)

            self.uow.commit()

            return {
                "id": created_user.id,
                "email": created_user.email,
                "full_name": created_user.full_name,
                "role": created_user.role,
                "department_id": created_user.department_id,
                "assigned_board_id": dto.board_id,
                "phone": created_user.phone,
                "is_active": created_user.is_active,
            }


class UpdateUserUseCase:
    def __init__(self, uow: IUnitOfWork):
        self.uow = uow

    def execute(self, current_user: User, user_id: int, dto: UserUpdateDTO) -> Dict[str, Any]:
        AccessPolicyService.ensure_can_manage_users(current_user)

        with self.uow:
            user = self.uow.users.get_by_id(user_id)
            if not user:
                raise EntityNotFoundException("User", user_id)

            if dto.full_name is not None:
                user.full_name = dto.full_name.strip()
            if dto.role is not None:
                if dto.role not in RoleType.list():
                    raise ValidationException(f"Invalid role. Must be one of: {RoleType.list()}")
                user.role = dto.role
            if dto.department_id is not None:
                user.department_id = dto.department_id
            if dto.phone is not None:
                user.phone = dto.phone.strip() if dto.phone else None
            if dto.interface_language is not None:
                user.interface_language = dto.interface_language
            if dto.password:
                if len(dto.password) < 6:
                    raise ValidationException("Password must be at least 6 characters.")
                user.password_hash = make_password(dto.password)
            if dto.is_active is not None:
                user.is_active = dto.is_active

            updated_user = self.uow.users.update(user)

            if dto.board_id is not None:
                # Remove from any existing board membership first (since single board rule applies)
                current_board_id = self.uow.users.get_assigned_board_id(user_id)
                if current_board_id and current_board_id != dto.board_id:
                    members = self.uow.boards.get_members(current_board_id)
                    cur_mgr = None
                    emp_ids = []
                    for m in members:
                        if m.user_id == user_id:
                            continue
                        if m.role == "manager":
                            cur_mgr = m.user_id
                        else:
                            emp_ids.append(m.user_id)
                    self.uow.boards.set_members(current_board_id, cur_mgr, emp_ids)

                if dto.board_id > 0:
                    members = self.uow.boards.get_members(dto.board_id)
                    cur_mgr = None
                    emp_ids = []
                    for m in members:
                        if m.role == "manager":
                            cur_mgr = m.user_id
                        else:
                            emp_ids.append(m.user_id)
                    if user.role == RoleType.MANAGER.value:
                        cur_mgr = user.id
                    else:
                        if user.id not in emp_ids:
                            emp_ids.append(user.id)
                    self.uow.boards.set_members(dto.board_id, cur_mgr, emp_ids)

            self.uow.commit()

            assigned_board_id = self.uow.users.get_assigned_board_id(user.id)
            return {
                "id": updated_user.id,
                "email": updated_user.email,
                "full_name": updated_user.full_name,
                "role": updated_user.role,
                "department_id": updated_user.department_id,
                "assigned_board_id": assigned_board_id,
                "phone": updated_user.phone,
                "is_active": updated_user.is_active,
            }


class DeleteUserUseCase:
    def __init__(self, uow: IUnitOfWork):
        self.uow = uow

    def execute(self, current_user: User, user_id: int) -> bool:
        AccessPolicyService.ensure_can_manage_users(current_user)
        if current_user.id == user_id:
            raise ValidationException("Cannot delete currently logged in administrator.")
        with self.uow:
            deleted = self.uow.users.delete(user_id)
            self.uow.commit()
            return deleted
