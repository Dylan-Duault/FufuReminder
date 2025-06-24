from enum import Enum


class FrequencyEnum(str, Enum):
    SPAM = "spam"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ValidationStatus(str, Enum):
    PENDING = "pending"
    VALIDATED = "validated"
    EXPIRED = "expired"
    FAILED = "failed"


class ReminderStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"