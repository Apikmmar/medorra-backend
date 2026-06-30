from dataclasses import dataclass, field
from typing import Optional, List
from base_entry import BaseEntry, ValidationError

@dataclass
class FoodItem:
    description: str = ""
    tags: List[str] = field(default_factory=list)

    def validate(self):
        if not self.description or not self.description.strip():
            raise ValidationError("description", "Food description is required")

        if len(self.description) > 500:
            raise ValidationError("description", "Maximum 500 characters")

        if len(self.tags) > 10:            
            raise ValidationError("tags", "Maximum 10 tags allowed")

        for tag in self.tags:
            if len(tag) > 50:
                raise ValidationError("tags", "Each tag must be at most 50 characters")

    def toDict(self) -> dict:
        return {
            "description": self.description,
            "tags": self.tags,
        }

    @classmethod
    def fromDict(cls, data: dict) -> "FoodItem":
        return cls(
            description=data.get("description", ""),
            tags=data.get("tags", []),
        )

@dataclass
class FoodEntry(BaseEntry):
    mealType: str = ""
    items: List[FoodItem] = field(default_factory=list)

    VALID_MEAL_TYPES = {"breakfast", "lunch", "dinner", "snack", "beverage"}

    def __post_init__(self):
        self.entryType = "food"
        super().__post_init__()

    def validate(self):
        super().validate()

        if not self.mealType or self.mealType not in self.VALID_MEAL_TYPES:
            raise ValidationError("mealType", f"Must be one of: {', '.join(sorted(self.VALID_MEAL_TYPES))}")

        if len(self.items) < 1:
            raise ValidationError("items", "At least 1 food item is required")

        if len(self.items) > 20:
            raise ValidationError("items", "Maximum 20 items per meal")

        for item in self.items:
            item.validate()

    def toDict(self) -> dict:
        data = super().toDict()
        data.update({
            "mealType": self.mealType,
            "items": [item.toDict() for item in self.items],
        })
        return data

    @classmethod
    def fromDict(cls, data: dict) -> "FoodEntry":
        items = [FoodItem.fromDict(item) for item in data.get("items", [])]
        return cls(
            userId=data["userId"],
            entryId=data.get("entryId"),
            timestamp=data.get("timestamp"),
            createdAt=data.get("createdAt"),
            updatedAt=data.get("updatedAt"),
            version=data.get("version", 1),
            mealType=data.get("mealType", ""),
            items=items,
        )