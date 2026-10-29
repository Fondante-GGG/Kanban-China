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


@dataclass
class CheckInDTO:
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    accuracy_meters: Optional[float] = None
    office_id: Optional[int] = None
    ip_address: Optional[str] = None


@dataclass
class CheckOutDTO:
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    accuracy_meters: Optional[float] = None
    office_id: Optional[int] = None
    ip_address: Optional[str] = None


@dataclass
class LeaveAbsenceDTO:
    absence_type: str  # lunch, business, personal, other
    reason: str = ""
    comment: str = ""


@dataclass
class LocationLogDTO:
    latitude: float
    longitude: float
    accuracy_meters: Optional[float] = None
    source: str = "gps"


@dataclass
class AttendanceRecordEditDTO:
    timestamp: str  # ISO timestamp
    edit_reason: str


@dataclass
class ConsentDTO:
    is_granted: bool
    consent_version: str = "1.0"
    consent_text: str = ""


@dataclass
class DayStatusDTO:
    user_id: int
    absence_type: str  # vacation, sick_leave, business_trip, day_off
    start_time: str
    end_time: Optional[str] = None
    reason: str = ""
    comment: str = ""


@dataclass
class OfficeDTO:
    name: str
    address: str = ""
    latitude: float = 42.8746
    longitude: float = 74.5698
    radius_meters: int = 100
    ip_subnet: str = ""
    is_ip_check_enabled: bool = False


@dataclass
class WorkScheduleDTO:
    name: str
    user_id: Optional[int] = None
    department_id: Optional[int] = None
    start_time: str = "09:00"
    end_time: str = "18:00"
    break_duration_minutes: int = 60
    timezone: str = "Asia/Bishkek"
    is_active: bool = True

