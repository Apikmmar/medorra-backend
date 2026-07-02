import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from base_entry import BaseEntry, ValidationError


@dataclass
class SleepSegment:
    startTime: str = ""
    endTime: str = ""
    durationMinutes: float = 0.0

    def validate(self):
        if not self.startTime:
            raise ValidationError("startTime", "Start time is required")
        if not self.endTime:
            raise ValidationError("endTime", "End time is required")

        try:
            start = datetime.fromisoformat(self.startTime.replace('Z', '+00:00'))
            end = datetime.fromisoformat(self.endTime.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            raise ValidationError("startTime", "Must be valid ISO 8601 timestamps")

        if end <= start:
            raise ValidationError("endTime", "End time must be after start time")

    def calculateDuration(self) -> float:
        start = datetime.fromisoformat(self.startTime.replace('Z', '+00:00'))
        end = datetime.fromisoformat(self.endTime.replace('Z', '+00:00'))
        delta = (end - start).total_seconds() / 60.0
        self.durationMinutes = delta

        return delta

    def toDict(self) -> dict:
        return {
            "startTime": self.startTime,
            "endTime": self.endTime,
            "durationMinutes": self.durationMinutes,
        }

    @classmethod
    def fromDict(cls, data: dict) -> "SleepSegment":
        return cls(
            startTime=data.get("startTime", ""),
            endTime=data.get("endTime", ""),
            durationMinutes=data.get("durationMinutes", 0.0),
        )


@dataclass
class SleepEntry(BaseEntry):
    segments: List[SleepSegment] = field(default_factory=list)
    totalDuration: float = 0.0
    qualityRating: int = 0
    notes: Optional[str] = None

    def __post_init__(self):
        self.entryType = "sleep"
        super().__post_init__()

    def validate(self):
        super().validate()

        if len(self.segments) < 1:
            raise ValidationError("segments", "At least 1 sleep segment is required")

        if len(self.segments) > 10:
            raise ValidationError("segments", "Maximum 10 segments per entry")

        for segment in self.segments:
            segment.validate()

        self.validateNoOverlaps()

        self.calculateTotalDuration()

        if self.totalDuration > 1440:
            raise ValidationError("duration", "Sleep duration cannot exceed 24 hours")

        if not isinstance(self.qualityRating, int) or self.qualityRating < 1 or self.qualityRating > 10:
            raise ValidationError("qualityRating", "Must be integer 1-10")

        if self.notes is not None and len(self.notes) > 1000:
            raise ValidationError("notes", "Maximum 1000 characters")

    def validateNoOverlaps(self):
        parsed = []

        for segment in self.segments:
            start = datetime.fromisoformat(segment.startTime.replace('Z', '+00:00'))
            end = datetime.fromisoformat(segment.endTime.replace('Z', '+00:00'))
            parsed.append((start, end))

        parsed.sort(key=lambda x: x[0])

        for i in range(len(parsed) - 1):
            if parsed[i][1] > parsed[i + 1][0]:
                raise ValidationError("segments", "Segments must not overlap")

    def calculateTotalDuration(self):
        total = 0.0
        for segment in self.segments:
            total += segment.calculateDuration()
        self.totalDuration = total

    def toDict(self) -> dict:
        data = super().toDict()
        data.update({
            "segments": [seg.toDict() for seg in self.segments],
            "totalDuration": self.totalDuration,
            "qualityRating": self.qualityRating,
            "notes": self.notes,
        })
        return data

    @classmethod
    def fromDict(cls, data: dict) -> "SleepEntry":
        segments = [SleepSegment.fromDict(seg) for seg in data.get("segments", [])]
        return cls(
            userId=data["userId"],
            entryId=data.get("entryId") or str(uuid.uuid4()),
            timestamp=data.get("timestamp"),
            createdAt=data.get("createdAt"),
            updatedAt=data.get("updatedAt"),
            version=data.get("version", 1),
            segments=segments,
            totalDuration=data.get("totalDuration", 0.0),
            qualityRating=data.get("qualityRating", 0),
            notes=data.get("notes"),
        )
