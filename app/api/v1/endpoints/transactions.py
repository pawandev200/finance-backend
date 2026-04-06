"""
Transaction Endpoints
──────────────────────
POST   /transactions            → Create (ADMIN)
GET    /transactions            → List with filters + pagination (ALL roles)
GET    /transactions/{id}       → Get by ID (ALL roles)
PATCH  /transactions/{id}       → Update (ADMIN)
DELETE /transactions/{id}       → Soft delete (ADMIN)
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.core.permissions import Permission
from app.db.session import get_db
from app.models.transaction import TransactionType
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.transaction import (
    TransactionCreate,
    TransactionDetailResponse,
    TransactionFilter,
    TransactionResponse,
    TransactionUpdate,
)
from app.services.transaction_service import TransactionService

router = APIRouter()


@router.post(
    "/",
    response_model=TransactionDetailResponse,
    status_code=201,
    summary="Create Transaction",
    dependencies=[Depends(require_permission(Permission.TRANSACTION_CREATE))],
)
def create_transaction(
    data: TransactionCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Creates a new financial transaction record.
    Requires ADMIN role. Amount must be > 0.
    """
    service = TransactionService(db)
    transaction = service.create(data=data, created_by_id=current_user.id)
    return TransactionDetailResponse.model_validate(transaction)


@router.get(
    "/",
    response_model=PaginatedResponse[TransactionResponse],
    summary="List Transactions",
    dependencies=[Depends(require_permission(Permission.TRANSACTION_READ))],
)
def list_transactions(
    # ── Pagination ────────────────────────────────────────────
    page: int = Query(default=1, ge=1, description="Page number"),
    size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    # ── Sorting ───────────────────────────────────────────────
    sort_by: str = Query(default="date", pattern="^(date|amount|category|created_at)$"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    # ── Filters ───────────────────────────────────────────────
    type: Optional[TransactionType] = Query(default=None, description="income or expense"),
    category: Optional[str] = Query(default=None, description="Filter by category (partial match)"),
    date_from: Optional[str] = Query(default=None, description="Start date YYYY-MM-DD"),
    date_to: Optional[str] = Query(default=None, description="End date YYYY-MM-DD"),
    search: Optional[str] = Query(default=None, description="Search notes and category"),
    db: Session = Depends(get_db),
):
    """
    Returns paginated transactions with optional filters.

    Accessible by all roles (VIEWER, ANALYST, ADMIN).
    Supports filtering by type, category, date range, and text search.
    """
    from datetime import date as date_type
    filters = TransactionFilter(
        type=type,
        category=category,
        date_from=date_type.fromisoformat(date_from) if date_from else None,
        date_to=date_type.fromisoformat(date_to) if date_to else None,
        search=search,
    )
    service = TransactionService(db)
    return service.get_paginated(
        filters=filters, page=page, size=size, sort_by=sort_by, sort_order=sort_order
    )


@router.get(
    "/{transaction_id}",
    response_model=TransactionDetailResponse,
    summary="Get Transaction by ID",
    dependencies=[Depends(require_permission(Permission.TRANSACTION_READ))],
)
def get_transaction(transaction_id: str, db: Session = Depends(get_db)):
    """Returns a specific transaction with creator details."""
    service = TransactionService(db)
    transaction = service.get_by_id(transaction_id)
    return TransactionDetailResponse.model_validate(transaction)


@router.patch(
    "/{transaction_id}",
    response_model=TransactionDetailResponse,
    summary="Update Transaction",
    dependencies=[Depends(require_permission(Permission.TRANSACTION_UPDATE))],
)
def update_transaction(
    transaction_id: str,
    data: TransactionUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Partially updates a transaction. Only ADMIN role.
    All changes are recorded in the audit log with before/after state.
    """
    service = TransactionService(db)
    transaction = service.update(
        transaction_id=transaction_id,
        data=data,
        updated_by_id=current_user.id,
    )
    return TransactionDetailResponse.model_validate(transaction)


@router.delete(
    "/{transaction_id}",
    response_model=MessageResponse,
    summary="Delete Transaction (Soft)",
    dependencies=[Depends(require_permission(Permission.TRANSACTION_DELETE))],
)
def delete_transaction(
    transaction_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Soft-deletes a transaction — it is marked as deleted but not removed from DB.
    This preserves the financial audit trail. Only ADMIN role.
    """
    service = TransactionService(db)
    service.soft_delete(transaction_id=transaction_id, deleted_by_id=current_user.id)
    return MessageResponse(message=f"Transaction {transaction_id} deleted successfully.")
