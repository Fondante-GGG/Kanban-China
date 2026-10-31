import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.config.settings")
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from backend.presentation.websockets.routing import websocket_urlpatterns
from backend.presentation.websockets.middleware import JwtBoardAuthMiddleware

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": JwtBoardAuthMiddleware(URLRouter(websocket_urlpatterns)),
})
