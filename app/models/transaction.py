import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Enum as SAEnum,
    ForeignKey, Numeric, String, Text,
)
from sqlalchemy.orm import relationship

from app.db.base import Base


class TransactionType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Core financial fields
    amount = Column(Numeric(15, 2), nullable=False)
    type = Column(SAEnum(TransactionType), nullable=False)
    category = Column(String(100), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    notes = Column(Text, nullable=True)

    # ── Soft Delete ───────────────────────────────────────────────────────────
    # Records are never physically deleted — crucial for financial audit trails
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by_id = Column(String(36), ForeignKey("users.id"), nullable=True)

    # ── Audit Trail ───────────────────────────────────────────────────────────
    created_by_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    updated_by_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    creator = relationship("User", foreign_keys=[created_by_id], back_populates="created_transactions")
    updater = relationship("User", foreign_keys=[updated_by_id])
    deleter = relationship("User", foreign_keys=[deleted_by_id])

    def __repr__(self) -> str:
        return f"<Transaction id={self.id} type={self.type} amount={self.amount}>"
