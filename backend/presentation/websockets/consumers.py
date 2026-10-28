import json
import logging
from channels.generic.websocket import AsyncJsonWebsocketConsumer

logger = logging.getLogger(__name__)


class BoardConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.board_id = self.scope["url_route"]["kwargs"].get("board_id")
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
        """
        Receive event from WebSocket client and broadcast to other clients in board group.
        """
        await self.channel_layer.group_send(
            self.board_group_name,
            {
                "type": "board_event",
                "sender_channel": self.channel_name,
                "payload": content,
            }
        )

    async def board_event(self, event):
        """
        Send event down to WebSocket client.
        """
        payload = event.get("payload", {})
        sender_channel = event.get("sender_channel")

        data = dict(payload)
        data["is_self"] = (sender_channel == self.channel_name)

        await self.send_json(data)
