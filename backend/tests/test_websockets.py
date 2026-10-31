from django.test import TestCase
from channels.testing import WebsocketCommunicator
from backend.config.asgi import application
from backend.presentation.websockets.broadcaster import broadcast_to_board
from backend.infrastructure.persistence.models import UserModel, BoardModel
from backend.domain.entities import User
from backend.infrastructure.di.container import container


class WebSocketTests(TestCase):
    def setUp(self):
        self.user = UserModel.objects.create_user(email="socket-director@test.local", password="password123", full_name="Socket Director", role="general_director")
        self.board = BoardModel.objects.create(title="Socket board")
        domain_user = User(id=self.user.id, email=self.user.email, password_hash=self.user.password, full_name=self.user.full_name, role=self.user.role)
        self.token = container.jwt_service.generate_token(domain_user)

    async def test_board_websocket_connection_and_broadcast(self):
        board_id = self.board.id
        denied = WebsocketCommunicator(application, f"/ws/boards/{board_id}/")
        connected, _ = await denied.connect()
        self.assertFalse(connected)
        communicator = WebsocketCommunicator(application, f"/ws/boards/{board_id}/", headers=[(b"authorization", f"Bearer {self.token}".encode())])
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # Clients cannot forge events; only the server broadcasts board updates.
        test_payload = {
            "type": "card_moved",
            "card_id": 42,
            "target_column_id": 10,
            "target_order": 0,
        }
        await communicator.send_json_to(test_payload)
        response = await communicator.receive_json_from()
        self.assertEqual(response.get("type"), "error")

        # Test server-side broadcast
        broadcast_to_board(board_id, {
            "type": "server_alert",
            "message": "Board updated",
        })
        broadcast_response = await communicator.receive_json_from()
        self.assertEqual(broadcast_response.get("type"), "server_alert")
        self.assertEqual(broadcast_response.get("message"), "Board updated")

        await communicator.disconnect()
