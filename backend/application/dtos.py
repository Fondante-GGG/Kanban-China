from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any


@dataclass
class LoginInputDTO:
    email: str
    password: str


@dataclass
class TokenResponseDTO:
    access_token: str
    user: Dict[str, Any]


@dataclass
class UserCreateDTO:
    email: str
    password: str
    full_name: str
    role: str
    department_id: Optional[int] = None
    board_id: Optional[int] = None
    phone: Optional[str] = None
    interface_language: str = "ru"


@dataclass
class UserUpdateDTO:
    full_name: Optional[str] = None
    role: Optional[str] = None
    department_id: Optional[int] = None
    board_id: Optional[int] = None
    phone: Optional[str] = None
    password: Optional[str] = None
    interface_language: Optional[str] = None
    is_active: Optional[bool] = None


@dataclass
class BoardCreateDTO:
    title: str
    department_id: Optional[int] = None
    background_theme: str = "gradient-blue"
    manager_id: Optional[int] = None
    employee_ids: List[int] = field(default_factory=list)


@dataclass
class BoardUpdateDTO:
    title: Optional[str] = None
    department_id: Optional[int] = None
    background_theme: Optional[str] = None
    is_archived: Optional[bool] = None
    manager_id: Optional[int] = None
    employee_ids: Optional[List[int]] = None


@dataclass
class ColumnCreateDTO:
    board_id: int
    title: str  # Given title in current language
    language: str = "ru"
    order: Optional[int] = None


@dataclass
class ColumnUpdateDTO:
    title: Optional[str] = None
    language: str = "ru"
    order: Optional[int] = None


@dataclass
class ReorderColumnsDTO:
    board_id: int
    column_orders: List[Dict[str, int]]  # [{"id": 1, "order": 0}, ...]


@dataclass
class CardCreateDTO:
    column_id: int
    title: str
    description: str = ""
    language: str = "ru"
    priority: str = "medium"
    due_date: Optional[str] = None
    assignee_ids: List[int] = field(default_factory=list)


@dataclass
class CardUpdateDTO:
    title: Optional[str] = None
    description: Optional[str] = None
    language: str = "ru"
    priority: Optional[str] = None
    due_date: Optional[str] = None
    assignee_ids: Optional[List[int]] = None


@dataclass
class CardMoveDTO:
    target_column_id: int
    target_order: int


@dataclass
class CommentCreateDTO:
    card_id: int
    text: str
    language: str = "ru"


@dataclass
class ChecklistItemCreateDTO:
    card_id: int
    title: str


@dataclass
class ReportFilterDTO:
    period: str = "month"  # "week", "month", "quarter", "custom"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    department_id: Optional[int] = None
    user_id: Optional[int] = None
