from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from backend.domain.value_objects import (
    RoleType, CardPriority, SupportedLanguage, ActivityAction,
    AttendanceRecordType, VerificationResult, AbsenceCategory, AbsenceType, LocationSource
)


@dataclass
class User:
    id: Optional[int]
    email: str
    password_hash: str
    full_name: str
    role: RoleType
    department_id: Optional[int] = None
    interface_language: str = SupportedLanguage.RU.value
    phone: Optional[str] = None
    is_active: bool = True
    assigned_board_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def is_general_director(self) -> bool:
        return self.role == RoleType.GENERAL_DIRECTOR.value or self.role == RoleType.GENERAL_DIRECTOR

    @property
    def is_manager(self) -> bool:
        return self.role == RoleType.MANAGER.value or self.role == RoleType.MANAGER

    @property
    def is_employee(self) -> bool:
        return self.role == RoleType.EMPLOYEE.value or self.role == RoleType.EMPLOYEE

    @property
    def is_accountant(self) -> bool:
        return self.role == RoleType.ACCOUNTANT.value or self.role == RoleType.ACCOUNTANT


@dataclass
class Department:
    id: Optional[int]
    name: str
    created_at: Optional[datetime] = None


@dataclass
class Board:
    id: Optional[int]
    title: str
    department_id: Optional[int] = None
    background_theme: str = "gradient-blue"  # e.g., gradient-indigo, slate, emerald, sunset, etc.
    is_archived: bool = False
    created_at: Optional[datetime] = None
    department_name: Optional[str] = None
    members: List["BoardMember"] = field(default_factory=list)
    columns: List["Column"] = field(default_factory=list)


@dataclass
class BoardMember:
    id: Optional[int]
    user_id: int
    board_id: int
    role: str
    user_full_name: Optional[str] = None
    user_email: Optional[str] = None


@dataclass
class Column:
    id: Optional[int]
    board_id: int
    title_ru: str
    title_zh: str
    title_ky: str
    original_lang: str = SupportedLanguage.RU.value
    order: int = 0
    created_at: Optional[datetime] = None
    cards_count: int = 0


@dataclass
class Card:
    id: Optional[int]
    column_id: int
    title_ru: str
    title_zh: str
    title_ky: str
    desc_ru: str = ""
    desc_zh: str = ""
    desc_ky: str = ""
    original_lang: str = SupportedLanguage.RU.value
    priority: CardPriority = CardPriority.MEDIUM
    due_date: Optional[datetime] = None
    order: int = 0
    created_by_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # Enriched data for responses
    column_name: Optional[str] = None
    board_id: Optional[int] = None
    assignees: List[User] = field(default_factory=list)
    checklists: List["ChecklistItem"] = field(default_factory=list)
    attachments_count: int = 0
    comments_count: int = 0


@dataclass
class ChecklistItem:
    id: Optional[int]
    card_id: int
    title: str
    is_completed: bool = False
    order: int = 0
    created_at: Optional[datetime] = None


@dataclass
class Comment:
    id: Optional[int]
    card_id: int
    user_id: int
    text_ru: str
    text_zh: str
    text_ky: str
    original_lang: str = SupportedLanguage.RU.value
    created_at: Optional[datetime] = None
    user_full_name: Optional[str] = None
    user_role: Optional[str] = None


@dataclass
class Attachment:
    id: Optional[int]
    card_id: int
    file_path: str
    file_name: str
    file_size: int
    content_type: str
    uploaded_by_id: int
    created_at: Optional[datetime] = None
    uploader_name: Optional[str] = None


@dataclass
class ActivityLog:
    id: Optional[int]
    card_id: int
    user_id: int
    action_type: ActivityAction
    details: str
    created_at: Optional[datetime] = None
    user_full_name: Optional[str] = None


@dataclass
class Notification:
    id: Optional[int]
    user_id: int
    title: str
    message: str
    entity_type: str  # card, comment, board
    entity_id: Optional[int] = None
    is_read: bool = False
    created_at: Optional[datetime] = None


@dataclass
class Office:
    id: Optional[int]
    name: str
    address: Optional[str] = "ул. Мухаммеда Али Джиннаха, 15/1"
    latitude: float = 40.512143
    longitude: float = 72.808202
    radius_meters: int = 100
    ip_subnet: str = ""
    is_ip_check_enabled: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class WorkSchedule:
    id: Optional[int]
    name: str
    user_id: Optional[int] = None
    department_id: Optional[int] = None
    start_time: str = "09:00"
    end_time: str = "18:00"
    break_duration_minutes: int = 60
    timezone: str = "Asia/Bishkek"
    is_active: bool = True
    created_at: Optional[datetime] = None
    user_full_name: Optional[str] = None
    department_name: Optional[str] = None


@dataclass
class AttendanceRecord:
    id: Optional[int]
    user_id: int
    record_type: AttendanceRecordType
    timestamp: datetime
    office_id: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    accuracy_meters: Optional[float] = None
    is_within_radius: bool = True
    ip_address: Optional[str] = None
    verification_result: VerificationResult = VerificationResult.VERIFIED
    rejection_reason: str = ""
    is_edited: bool = False
    edited_by_id: Optional[int] = None
    edit_reason: str = ""
    original_timestamp: Optional[datetime] = None
    created_at: Optional[datetime] = None
    user_full_name: Optional[str] = None
    user_email: Optional[str] = None
    office_name: Optional[str] = None
    edited_by_name: Optional[str] = None


@dataclass
class Absence:
    id: Optional[int]
    user_id: int
    category: AbsenceCategory
    absence_type: AbsenceType
    start_time: datetime
    end_time: Optional[datetime] = None
    reason: str = ""
    comment: str = ""
    is_approved: bool = True
    approved_by_id: Optional[int] = None
    created_at: Optional[datetime] = None
    user_full_name: Optional[str] = None
    user_department_name: Optional[str] = None
    approved_by_name: Optional[str] = None


@dataclass
class LocationLog:
    id: Optional[int]
    user_id: int
    timestamp: datetime
    latitude: float
    longitude: float
    accuracy_meters: Optional[float] = None
    source: LocationSource = LocationSource.GPS
    is_outside_office: bool = False
    created_at: Optional[datetime] = None
    user_full_name: Optional[str] = None


@dataclass
class Consent:
    id: Optional[int]
    user_id: int
    consent_version: str = "1.0"
    is_granted: bool = True
    granted_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    consent_text: str = ""
    created_at: Optional[datetime] = None
    user_full_name: Optional[str] = None

