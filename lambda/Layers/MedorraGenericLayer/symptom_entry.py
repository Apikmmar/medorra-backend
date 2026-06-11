from dataclasses import dataclass, field
from typing import Optional, List
from base_entry import BaseEntry, ValidationError

@dataclass
class SymptomEntry(BaseEntry):
    symptomName: str = ""
    severity: int = 0
    notes: Optional[str] = None
    customSymptomTypes: List[str] = field(default_factory=list)

    def __post_init__(self):
        self.entryType = "symptom"
        super().__post_init__()

    def validate(self):
        super().validate()

        if not self.symptomName or not self.symptomName.strip():
            raise ValidationError("symptomName", "Symptom name is required")

        if len(self.symptomName) > 100:
            raise ValidationError("symptomName", "Symptom name must be 100 characters or less")

        if not isinstance(self.severity, int) or self.severity < 1 or self.severity > 10:
            raise ValidationError("severity", "Must be integer 1-10")

        if self.notes is not None and len(self.notes) > 2000:
            raise ValidationError("notes", "Maximum 2000 characters")

        if len(self.customSymptomTypes) > 200:
            raise ValidationError("customSymptomTypes", "Maximum 200 custom symptom types per user")

    def toDict(self) -> dict:
        data = super().toDict()
        data.update({
            "symptomName": self.symptomName,
            "severity": self.severity,
            "notes": self.notes,
        })
        return data

    @classmethod
    def fromDict(cls, data: dict) -> "SymptomEntry":
        return cls(
            userId=data["userId"],
            entryId=data.get("entryId"),
            timestamp=data.get("timestamp"),
            createdAt=data.get("createdAt"),
            updatedAt=data.get("updatedAt"),
            version=data.get("version", 1),
            symptomName=data.get("symptomName", ""),
            severity=data.get("severity", 0),
            notes=data.get("notes"),
            customSymptomTypes=data.get("customSymptomTypes", []),
        )