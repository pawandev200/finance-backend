"""
Transaction Service
────────────────────
Business logic for financial record management.
Key rules enforced here:
  - Amounts must be > 0 (also validated at schema level — defense in depth)
  - Soft delete only — financial records are never hard-deleted
  - All mutations are audit-logged with old and new state
"""

import math
from datetime import datetime
from typing import List, Tuple

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException
from app.models.transaction import Transaction
from app.repositories.transaction_repo import TransactionRepository
from app.schemas.common import PaginatedResponse
from app.schemas.transaction import (
    TransactionCreate,
    TransactionFilter,
    TransactionResponse,
    TransactionUpdate,
)
from app.services.audit_service import AuditService


class TransactionService:
    def __init__(self, db: Session):
        self.repo = TransactionRepository(db)
        self.audit = AuditService(db)

    def _to_snapshot(self, t: Transaction) -> dict:
        """Serializes a transaction to a dict for audit snapshots."""
        return {
            "amount": str(t.amount),
            "type": t.type,
            "category": t.category,
            "date": str(t.date),
            "notes": t.notes,
        }

    def create(self, data: TransactionCreate, created_by_id: str) -> Transaction:
        transaction = Transaction(
            amount=data.amount,
            type=data.type,
            category=data.category.strip(),
            date=data.date,
            notes=data.notes,
            created_by_id=created_by_id,
        )
        transaction = self.repo.create(transaction)

        self.audit.log(
            user_id=created_by_id,
            action="CREATE",
            resource="transaction",
            resource_id=transaction.id,
            new_value=self._to_snapshot(transaction),
        )
        return transaction

    def get_by_id(self, transaction_id: str) -> Transaction:
        transaction = self.repo.get_by_id_active(transaction_id)
        if not transaction:
            raise NotFoundException("Transaction", transaction_id)
        return transaction

    def get_paginated(
        self,
        filters: TransactionFilter,
        page: int = 1,
        size: int = 20,
        sort_by: str = "date",
        sort_order: str = "desc",
    ) -> PaginatedResponse[TransactionResponse]:
        skip = (page - 1) * size
        transactions, total = self.repo.get_paginated(
            filters=filters,
            skip=skip,
            limit=size,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return PaginatedResponse(
            items=[TransactionResponse.model_validate(t) for t in transactions],
            total=total,
            page=page,
            size=size,
            pages=math.ceil(total / size) if total > 0 else 1,
        )

    def update(
        self,
        transaction_id: str,
        data: TransactionUpdate,
        updated_by_id: str,
    ) -> Transaction:
        transaction = self.get_by_id(transaction_id)
        old_snapshot = self._to_snapshot(transaction)

        if data.amount is not None:
            transaction.amount = data.amount
        if data.type is not None:
            transaction.type = data.type
        if data.category is not None:
            transaction.category = data.category.strip()
        if data.date is not None:
            transaction.date = data.date
        if data.notes is not None:
            transaction.notes = data.notes

        transaction.updated_by_id = updated_by_id
        transaction = self.repo.save(transaction)

        self.audit.log(
            user_id=updated_by_id,
            action="UPDATE",
            resource="transaction",
            resource_id=transaction.id,
            old_value=old_snapshot,
            new_value=self._to_snapshot(transaction),
        )
        return transaction

    def soft_delete(self, transaction_id: str, deleted_by_id: str) -> None:
        """
        Marks a transaction as deleted without removing it from the DB.
        Financial data must always be recoverable for auditing purposes.
        """
        transaction = self.get_by_id(transaction_id)
        old_snapshot = self._to_snapshot(transaction)

        transaction.is_deleted = True
        transaction.deleted_at = datetime.utcnow()
        transaction.deleted_by_id = deleted_by_id
        self.repo.save(transaction)

        self.audit.log(
            user_id=deleted_by_id,
            action="DELETE",
            resource="transaction",
            resource_id=transaction_id,
            old_value=old_snapshot,
        )
