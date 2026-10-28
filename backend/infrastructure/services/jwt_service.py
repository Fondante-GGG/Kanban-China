import jwt
from datetime import datetime, timedelta, timezone
from typing import Dict, Any
from django.conf import settings
from backend.application.interfaces.services import ITokenService
from backend.domain.entities import User
from backend.domain.exceptions import AuthenticationFailedException


class JwtTokenService(ITokenService):
    def __init__(self, secret_key: str = None, algorithm: str = "HS256", expiration_hours: int = 72):
        self.secret_key = secret_key or getattr(settings, "SECRET_KEY", "fallback-secret-key-change-in-prod")
        self.algorithm = algorithm
        self.expiration_hours = expiration_hours

    def generate_token(self, user: User) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "department_id": user.department_id,
            "interface_language": user.interface_language,
            "iat": now,
            "exp": now + timedelta(hours=self.expiration_hours)
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str) -> Dict[str, Any]:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            if "sub" in payload and str(payload["sub"]).isdigit():
                payload["sub"] = int(payload["sub"])
            return payload
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailedException("Token has expired.")
        except jwt.InvalidTokenError:
            raise AuthenticationFailedException("Invalid authentication token.")
