import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from base_entry import ValidationError


@dataclass
class FeedbackEntry:
    userId: str
    category: str = ""
    message: str = ""
    subject: Optional[str] = None
    rating: Optional[int] = None
    feedbackId: str = field(default_factory=lambda: str(uuid.uuid4()))
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None
    version: int = 1

    VALID_CATEGORIES = {"bug", "feature", "improvement", "general", "praise"}
    MAX_SUBJECT_LENGTH = 120
    MAX_MESSAGE_LENGTH = 2000

    def __post_init__(self):
        now = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ')

        if self.createdAt is None:
            self.createdAt = now

        if self.updatedAt is None:
            self.updatedAt = now

    def validate(self):
        if not self.userId or not self.userId.strip():
            raise ValidationError("userId", "userId is required")

        if self.category not in self.VALID_CATEGORIES:
            raise ValidationError(
                "category",
                f"Must be one of: {', '.join(sorted(self.VALID_CATEGORIES))}",
            )

        if not self.message or not self.message.strip():
            raise ValidationError("message", "Feedback message is required")

        if len(self.message) > self.MAX_MESSAGE_LENGTH:
            raise ValidationError(
                "message", f"Maximum {self.MAX_MESSAGE_LENGTH} characters"
            )

        if self.subject is not None and len(self.subject) > self.MAX_SUBJECT_LENGTH:
            raise ValidationError(
                "subject", f"Maximum {self.MAX_SUBJECT_LENGTH} characters"
            )

        if self.rating is not None:
            if not isinstance(self.rating, int) or isinstance(self.rating, bool):
                raise ValidationError("rating", "Must be an integer between 1 and 5")
            if self.rating < 1 or self.rating > 5:
                raise ValidationError("rating", "Must be between 1 and 5")

        try:
            parsed = uuid.UUID(self.feedbackId, version=4)
            if str(parsed) != self.feedbackId:
                raise ValueError()
        except (ValueError, AttributeError):
            raise ValidationError("feedbackId", "Must be a valid UUID v4")

        if not isinstance(self.version, int) or self.version < 1:
            raise ValidationError("version", "Must be a positive integer")

    def toDict(self) -> dict:
        return {
            "userId": self.userId,
            "feedbackId": self.feedbackId,
            "category": self.category,
            "subject": self.subject,
            "message": self.message,
            "rating": self.rating,
            "createdAt": self.createdAt,
            "updatedAt": self.updatedAt,
            "version": self.version,
        }

    @classmethod
    def fromDict(cls, data: dict) -> "FeedbackEntry":
        subject = data.get("subject")
        if isinstance(subject, str):
            subject = subject.strip() or None

        rating = data.get("rating")
        if rating is not None:
            try:
                rating = int(rating)
            except (ValueError, TypeError):
                raise ValidationError("rating", "Must be an integer between 1 and 5")

        return cls(
            userId=data["userId"],
            category=data.get("category", ""),
            message=data.get("message", ""),
            subject=subject,
            rating=rating,
            feedbackId=data.get("feedbackId") or str(uuid.uuid4()),
            createdAt=data.get("createdAt"),
            updatedAt=data.get("updatedAt"),
            version=data.get("version", 1),
        )
