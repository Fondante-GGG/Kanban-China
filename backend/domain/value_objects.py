from enum import Enum


class RoleType(str, Enum):
    GENERAL_DIRECTOR = "general_director"
    MANAGER = "manager"
    EMPLOYEE = "employee"

    @classmethod
    def list(cls):
        return [c.value for c in cls]


class CardPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

    @classmethod
    def list(cls):
        return [c.value for c in cls]


class SupportedLanguage(str, Enum):
    RU = "ru"
    ZH_HANS = "zh-Hans"
    ZH_HANT = "zh-Hant"
    KY = "ky"

    @classmethod
    def list(cls):
        return [c.value for c in cls]


class ActivityAction(str, Enum):
    CREATED = "created"
    UPDATED = "updated"
    MOVED = "moved"
    COMMENTED = "commented"
    ASSIGNED = "assigned"
    UNASSIGNED = "unassigned"
    CHECKLIST_TOGGLED = "checklist_toggled"
    ATTACHMENT_ADDED = "attachment_added"


class AttendanceRecordType(str, Enum):
    CHECK_IN = "check_in"
    CHECK_OUT = "check_out"

    @classmethod
    def list(cls):
        return [c.value for c in cls]


class VerificationResult(str, Enum):
    VERIFIED = "verified"
    REJECTED = "rejected"
    MANUAL_OVERRIDE = "manual_override"

    @classmethod
    def list(cls):
        return [c.value for c in cls]


class AbsenceCategory(str, Enum):
    BREAK = "break"
    DAY_STATUS = "day_status"

    @classmethod
    def list(cls):
        return [c.value for c in cls]


class AbsenceType(str, Enum):
    # Intra-day breaks
    LUNCH = "lunch"
    BUSINESS = "business"
    PERSONAL = "personal"
    OTHER = "other"
    # Day statuses
    VACATION = "vacation"
    SICK_LEAVE = "sick_leave"
    BUSINESS_TRIP = "business_trip"
    DAY_OFF = "day_off"

    @classmethod
    def list(cls):
        return [c.value for c in cls]


class LocationSource(str, Enum):
    GPS = "gps"
    NETWORK = "network"
    WEB = "web"
    MOBILE = "mobile"

    @classmethod
    def list(cls):
        return [c.value for c in cls]

