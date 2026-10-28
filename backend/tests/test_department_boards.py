from django.test import TestCase
from backend.domain.entities import User
from backend.infrastructure.di.container import container
from backend.infrastructure.persistence.models import DepartmentModel, BoardModel, ColumnModel


class DepartmentBoardIntegrationTest(TestCase):
    def setUp(self):
        self.director = User(
            id=1,
            email="director@company.com",
            full_name="Ген Директор",
            role="general_director",
            department_id=None,
            is_active=True,
            password_hash="hash",
            interface_language="ru"
        )
        self.uow = container.get_uow()

    def test_department_auto_creates_board_and_columns(self):
        # 1. Create a department via UoW (simulating admin action)
        from backend.domain.entities import Department
        with self.uow:
            dept = Department(id=None, name="Новый Экспериментальный Отдел")
            created_dept = self.uow.departments.create(dept)
            self.uow.commit()

        # Check DepartmentModel exists
        self.assertIsNotNone(created_dept.id)
        
        # Check signal / use case automatically created a board
        dept_model = DepartmentModel.objects.get(id=created_dept.id)
        boards = dept_model.boards.all()
        self.assertEqual(boards.count(), 1)
        board = boards.first()
        self.assertEqual(board.title, "Новый Экспериментальный Отдел")
        
        # Check standard 6 columns were created
        columns = board.columns.all()
        self.assertEqual(columns.count(), 6)

        # 2. Check ListBoardsUseCase returns this board for general director
        list_boards_use_case = container.get_list_boards_use_case()
        board_list = list_boards_use_case.execute(self.director)
        board_ids = [b["id"] for b in board_list]
        self.assertIn(board.id, board_ids)
        
        # Verify department_name is populated
        matching_board = next(b for b in board_list if b["id"] == board.id)
        self.assertEqual(matching_board["department_name"], "Новый Экспериментальный Отдел")
