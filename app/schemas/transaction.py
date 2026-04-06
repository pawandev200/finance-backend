from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, field_validator

from app.models.transaction import TransactionType
from app.schemas.user import UserSummary


class TransactionCreate(BaseModel):
    amount: Decimal
    type: TransactionType
    category: str
    date: date
    notes: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Amount must be greater than zero.")
        return round(v, 2)

    @field_validator("category")
    @classmethod
    def category_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Category cannot be empty.")
        return v


class TransactionUpdate(BaseModel):
    amount: Optional[Decimal] = None
    type: Optional[TransactionType] = None
    category: Optional[str] = None
    date: Optional[date] = None
    notes: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v <= 0:
            raise ValueError("Amount must be greater than zero.")
        return v


class TransactionResponse(BaseModel):
    id: str
    amount: Decimal
    type: TransactionType
    category: str
    date: date
    notes: Optional[str]
    created_by_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TransactionDetailResponse(TransactionResponse):
    """Full response including creator info."""
    creator: Optional[UserSummary] = None


class TransactionFilter(BaseModel):
    """Query parameters for filtering transactions."""
    type: Optional[TransactionType] = None
    category: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    search: Optional[str] = None  # Searches notes + category
