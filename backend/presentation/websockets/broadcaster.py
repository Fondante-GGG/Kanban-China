import asyncio
import logging
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)


def broadcast_to_board(board_id: int, payload: dict):
    """
    Utility to broadcast an event payload to all clients connected to board_{board_id}.
    Works seamlessly whether called from synchronous Django views or async contexts.
    """
    try:
        channel_layer = get_channel_layer()
        if not channel_layer:
            return

        message = {
            "type": "board_event",
            "payload": payload,
        }

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            asyncio.create_task(channel_layer.group_send(f"board_{board_id}", message))
        else:
            async_to_sync(channel_layer.group_send)(f"board_{board_id}", message)
    except Exception as e:
        logger.warning(f"Failed to broadcast WebSocket event to board {board_id}: {e}")
