import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo

class ValidationError(Exception):
    def __init__(self, field_name: str, message: str):
        self.field_name = field_name
        self.message = message
        super().__init__(f"Validation error on '{field_name}': {message}")

@dataclass
class BaseEntry:
    userId: str
    entryType: str = ""
    entryId: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: Optional[str] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None
    version: int = 1

    VALID_ENTRY_TYPES = {"symptom", "medication", "food", "sleep"}

    def __post_init__(self):
        now = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ')

        if self.timestamp is None:
            self.timestamp = now

        if self.createdAt is None:
            self.createdAt = now

        if self.updatedAt is None:
            self.updatedAt = now

    def validate(self):
        if not self.userId or not self.userId.strip():
            raise ValidationError("userId", "userId is required")

        if self.entryType not in self.VALID_ENTRY_TYPES:
            raise ValidationError("entryType", f"Must be one of: {', '.join(sorted(self.VALID_ENTRY_TYPES))}")

        try:
            parsed = uuid.UUID(self.entryId, version=4)
            if str(parsed) != self.entryId:
                raise ValueError()
        except (ValueError, AttributeError):
            raise ValidationError("entryId", "Must be a valid UUID v4")

        if self.timestamp:
            try:
                datetime.fromisoformat(self.timestamp.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                raise ValidationError("timestamp", "Must be a valid ISO 8601 timestamp")

        if not isinstance(self.version, int) or self.version < 1:
            raise ValidationError("version", "Must be a positive integer")

    def toDict(self) -> dict:
        return {
            "userId": self.userId,
            "entryId": self.entryId,
            "entryType": self.entryType,
            "timestamp": self.timestamp,
            "createdAt": self.createdAt,
            "updatedAt": self.updatedAt,
            "version": self.version,
        }

    @classmethod
    def fromDict(cls, data: dict) -> "BaseEntry":
        return cls(
            userId=data["userId"],
            entryType=data["entryType"],
            entryId=data.get("entryId", str(uuid.uuid4())),
            timestamp=data.get("timestamp"),
            createdAt=data.get("createdAt"),
            updatedAt=data.get("updatedAt"),
            version=data.get("version", 1),
        )

    def prepareForUpdate(self, currentVersion: int) -> dict:
        self.updatedAt = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        self.version = currentVersion + 1

        return {
            "condition_expression": "version = :expected_version",
            "expression_values": {":expected_version": currentVersion},
        }

    @staticmethod
    def generateSortKey(createdAt: str, entryId: str) -> str:
        return f"{createdAt}#{entryId}"

    @staticmethod
    def defaultTimestampForTimezone(tzName: Optional[str] = None) -> str:
        try:
            if tzName:
                tz = ZoneInfo(tzName)
                return datetime.now(tz).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                
        except (KeyError, ImportError):
            pass

        return datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
