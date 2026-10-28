from django.test import TestCase
from channels.testing import WebsocketCommunicator
from backend.config.asgi import application
from backend.presentation.websockets.broadcaster import broadcast_to_board


class WebSocketTests(TestCase):
    async def test_board_websocket_connection_and_broadcast(self):
        board_id = 999
        communicator = WebsocketCommunicator(application, f"/ws/boards/{board_id}/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # Test sending client message
        test_payload = {
            "type": "card_moved",
            "card_id": 42,
            "target_column_id": 10,
            "target_order": 0,
        }
        await communicator.send_json_to(test_payload)
        response = await communicator.receive_json_from()
        self.assertEqual(response.get("type"), "card_moved")
        self.assertEqual(response.get("card_id"), 42)
        self.assertTrue(response.get("is_self"))

        # Test server-side broadcast
        broadcast_to_board(board_id, {
            "type": "server_alert",
            "message": "Board updated",
        })
        broadcast_response = await communicator.receive_json_from()
        self.assertEqual(broadcast_response.get("type"), "server_alert")
        self.assertEqual(broadcast_response.get("message"), "Board updated")

        await communicator.disconnect()
