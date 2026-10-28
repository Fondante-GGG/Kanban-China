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
