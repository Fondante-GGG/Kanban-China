import logging
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from backend.presentation.websockets.middleware import can_view_board

logger = logging.getLogger(__name__)


class BoardConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.board_id = self.scope["url_route"]["kwargs"].get("board_id")
        user = self.scope.get("board_user")
        if not user or not await can_view_board(user, self.board_id):
            await self.close(code=4403)
            return
        self.board_group_name = f"board_{self.board_id}"

        # Join board group
        await self.channel_layer.group_add(
            self.board_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Leave board group
        if hasattr(self, "board_group_name"):
            await self.channel_layer.group_discard(
                self.board_group_name,
                self.channel_name
            )

    async def receive_json(self, content, **kwargs):
        await self.send_json({"type": "error", "error": "Client board events are not accepted."})

    async def board_event(self, event):
        payload = event.get("payload", {})
        sender_channel = event.get("sender_channel")

        data = dict(payload)
        data["is_self"] = (sender_channel == self.channel_name)

        await self.send_json(data)
