from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware

from backend.infrastructure.di.container import container
from backend.infrastructure.persistence.models import BoardMemberModel, UserModel


@database_sync_to_async
def get_active_user(user_id):
    return UserModel.objects.filter(id=user_id, is_active=True).values("id", "role").first()


@database_sync_to_async
def can_view_board(user, board_id):
    if user["role"] == "general_director":
        return True
    return BoardMemberModel.objects.filter(user_id=user["id"], board_id=board_id).exists()


class JwtBoardAuthMiddleware(BaseMiddleware):
    """Authenticate board sockets with the same Bearer JWT used by the HTTP API."""
    async def __call__(self, scope, receive, send):
        headers = dict(scope.get("headers", []))
        authorization = headers.get(b"authorization", b"").decode("latin1")
        if not authorization.startswith("Bearer "):
            scope["board_user"] = None
            return await super().__call__(scope, receive, send)
        try:
            payload = container.jwt_service.verify_token(authorization.split(" ", 1)[1].strip())
            scope["board_user"] = await get_active_user(payload.get("sub"))
        except Exception:
            scope["board_user"] = None
        return await super().__call__(scope, receive, send)
