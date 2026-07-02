import uuid
from dataclasses import dataclass
from typing import Optional
from base_entry import BaseEntry, ValidationError

@dataclass
class MedicationEntry(BaseEntry):
    medicationName: str = ""
    dosageAmount: Optional[float] = None
    dosageUnit: Optional[str] = None
    scheduleType: str = ""
    notes: Optional[str] = None

    VALID_SCHEDULE_TYPES = {"as-needed", "scheduled"}

    def __post_init__(self):
        self.entryType = "medication"
        super().__post_init__()

    def validate(self):
        super().validate()

        if not self.medicationName or not self.medicationName.strip():
            raise ValidationError("medicationName", "Medication name is required")

        if len(self.medicationName) > 100:
            raise ValidationError("medicationName", "Maximum 100 characters")

        if self.dosageAmount is not None:
            if not isinstance(self.dosageAmount, (int, float)):
                raise ValidationError("dosageAmount", "Must be a numeric value")
            if self.dosageAmount < 0.01 or self.dosageAmount > 99999:
                raise ValidationError("dosageAmount", "Must be between 0.01 and 99999")

        if self.scheduleType not in self.VALID_SCHEDULE_TYPES:
            raise ValidationError("scheduleType", "Must be 'as-needed' or 'scheduled'")

    def toDict(self) -> dict:
        data = super().toDict()
        data.update({
            "medicationName": self.medicationName,
            "dosageAmount": self.dosageAmount,
            "dosageUnit": self.dosageUnit,
            "scheduleType": self.scheduleType,
            "notes": self.notes,
        })
        return data

    @classmethod
    def fromDict(cls, data: dict) -> "MedicationEntry":
        return cls(
            userId=data["userId"],
            entryId=data.get("entryId") or str(uuid.uuid4()),
            timestamp=data.get("timestamp"),
            createdAt=data.get("createdAt"),
            updatedAt=data.get("updatedAt"),
            version=data.get("version", 1),
            medicationName=data.get("medicationName", ""),
            dosageAmount=data.get("dosageAmount"),
            dosageUnit=data.get("dosageUnit"),
            scheduleType=data.get("scheduleType", ""),
            notes=data.get("notes"),
        )