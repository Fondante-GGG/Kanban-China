from typing import Dict, Any
from django.contrib.auth.hashers import check_password, make_password
from backend.application.interfaces.uow import IUnitOfWork
from backend.application.interfaces.services import ITokenService
from backend.application.dtos import LoginInputDTO, TokenResponseDTO
from backend.domain.exceptions import AuthenticationFailedException, EntityNotFoundException, ValidationException


class LoginUseCase:
    def __init__(self, uow: IUnitOfWork, token_service: ITokenService):
        self.uow = uow
        self.token_service = token_service

    def execute(self, dto: LoginInputDTO) -> Dict[str, Any]:
        with self.uow:
            user = self.uow.users.get_by_email(dto.email.strip().lower())
            if not user:
                raise AuthenticationFailedException("Invalid email or password.")
            if not user.is_active:
                raise AuthenticationFailedException("User account is inactive or blocked.")

            if not check_password(dto.password, user.password_hash):
                raise AuthenticationFailedException("Invalid email or password.")

            token = self.token_service.generate_token(user)
            assigned_board_id = self.uow.users.get_assigned_board_id(user.id)

            return {
                "access_token": token,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "full_name": user.full_name,
                    "role": user.role,
                    "department_id": user.department_id,
                    "interface_language": user.interface_language,
                    "assigned_board_id": assigned_board_id,
                }
            }


class GetProfileUseCase:
    def __init__(self, uow: IUnitOfWork):
        self.uow = uow

    def execute(self, user_id: int) -> Dict[str, Any]:
        with self.uow:
            user = self.uow.users.get_by_id(user_id)
            if not user:
                raise EntityNotFoundException("User", user_id)
            assigned_board_id = self.uow.users.get_assigned_board_id(user.id)
            return {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
                "department_id": user.department_id,
                "phone": user.phone,
                "interface_language": user.interface_language,
                "assigned_board_id": assigned_board_id,
            }


class UpdateInterfaceLanguageUseCase:
    SUPPORTED_LANGUAGES = {"ru", "ky", "zh-Hans", "zh-Hant"}

    def __init__(self, uow: IUnitOfWork):
        self.uow = uow

    def execute(self, user_id: int, interface_language: str) -> Dict[str, Any]:
        if interface_language not in self.SUPPORTED_LANGUAGES:
            raise ValidationException("interface_language must be ru, ky, zh-Hans or zh-Hant.")
        with self.uow:
            user = self.uow.users.get_by_id(user_id)
            if not user:
                raise EntityNotFoundException("User", user_id)
            user.interface_language = interface_language
            updated = self.uow.users.update(user)
            self.uow.commit()
            assigned_board_id = self.uow.users.get_assigned_board_id(updated.id)
            return {
                "id": updated.id,
                "email": updated.email,
                "full_name": updated.full_name,
                "role": updated.role,
                "department_id": updated.department_id,
                "phone": updated.phone,
                "interface_language": updated.interface_language,
                "assigned_board_id": assigned_board_id,
            }


class ResetPasswordUseCase:
    def __init__(self, uow: IUnitOfWork):
        self.uow = uow

    def execute(self, user_id: int, new_password: str) -> None:
        if not new_password or len(new_password) < 6:
            raise ValidationException("Password must be at least 6 characters long.")
        with self.uow:
            user = self.uow.users.get_by_id(user_id)
            if not user:
                raise EntityNotFoundException("User", user_id)
            user.password_hash = make_password(new_password)
            self.uow.users.update(user)
            self.uow.commit()
