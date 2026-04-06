"""
Transaction Repository
───────────────────────
All SQL queries for transactions live here.
Services remain free of SQLAlchemy query syntax.
"""

from datetime import date
from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.transaction import Transaction, TransactionType
from app.repositories.base import BaseRepository
from app.schemas.transaction import TransactionFilter


class TransactionRepository(BaseRepository[Transaction]):
    def __init__(self, db: Session):
        super().__init__(Transaction, db)

    # ── Base query: always exclude soft-deleted records ───────────────────────

    def _active_query(self):
        return self.db.query(Transaction).filter(Transaction.is_deleted == False)

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_by_id_active(self, id: str) -> Optional[Transaction]:
        return (
            self._active_query()
            .options(joinedload(Transaction.creator))
            .filter(Transaction.id == id)
            .first()
        )

    def get_paginated(
        self,
        filters: TransactionFilter,
        skip: int = 0,
        limit: int = 20,
        sort_by: str = "date",
        sort_order: str = "desc",
    ) -> Tuple[List[Transaction], int]:
        query = self._active_query().options(joinedload(Transaction.creator))

        # ── Apply filters ─────────────────────────────────────────────────────
        if filters.type:
            query = query.filter(Transaction.type == filters.type)

        if filters.category:
            query = query.filter(
                Transaction.category.ilike(f"%{filters.category}%")
            )

        if filters.date_from:
            query = query.filter(Transaction.date >= filters.date_from)

        if filters.date_to:
            query = query.filter(Transaction.date <= filters.date_to)

        if filters.search:
            search_term = f"%{filters.search}%"
            query = query.filter(
                Transaction.notes.ilike(search_term)
                | Transaction.category.ilike(search_term)
            )

        # ── Total count before pagination ─────────────────────────────────────
        total = query.count()

        # ── Sorting ───────────────────────────────────────────────────────────
        sort_column = getattr(Transaction, sort_by, Transaction.date)
        if sort_order == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        transactions = query.offset(skip).limit(limit).all()
        return transactions, total

    # ── Aggregation queries (used by dashboard service) ───────────────────────

    def get_totals(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> dict:
        """Returns total income, total expense, and counts."""
        query = self._active_query()
        if date_from:
            query = query.filter(Transaction.date >= date_from)
        if date_to:
            query = query.filter(Transaction.date <= date_to)

        result = query.with_entities(
            Transaction.type,
            func.coalesce(func.sum(Transaction.amount), 0).label("total"),
            func.count(Transaction.id).label("count"),
        ).group_by(Transaction.type).all()

        totals = {
            "total_income": Decimal("0"),
            "total_expense": Decimal("0"),
            "income_count": 0,
            "expense_count": 0,
        }
        for row in result:
            if row.type == TransactionType.INCOME:
                totals["total_income"] = Decimal(str(row.total))
                totals["income_count"] = row.count
            elif row.type == TransactionType.EXPENSE:
                totals["total_expense"] = Decimal(str(row.total))
                totals["expense_count"] = row.count

        totals["transaction_count"] = totals["income_count"] + totals["expense_count"]
        return totals

    def get_category_breakdown(
        self,
        transaction_type: TransactionType,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> List[dict]:
        """Category-wise totals for a given transaction type."""
        query = self._active_query().filter(Transaction.type == transaction_type)
        if date_from:
            query = query.filter(Transaction.date >= date_from)
        if date_to:
            query = query.filter(Transaction.date <= date_to)

        rows = query.with_entities(
            Transaction.category,
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("count"),
        ).group_by(Transaction.category).order_by(func.sum(Transaction.amount).desc()).all()

        grand_total = sum(Decimal(str(r.total)) for r in rows) or Decimal("1")

        return [
            {
                "category": r.category,
                "total": Decimal(str(r.total)),
                "count": r.count,
                "percentage": round(float(Decimal(str(r.total)) / grand_total * 100), 2),
            }
            for r in rows
        ]

    def get_monthly_trends(self, months: int = 12) -> List[dict]:
        """Monthly income vs expense aggregation for trend charts."""
        rows = (
            self._active_query()
            .with_entities(
                func.strftime("%Y", Transaction.date).label("year"),
                func.strftime("%m", Transaction.date).label("month"),
                Transaction.type,
                func.sum(Transaction.amount).label("total"),
            )
            .group_by(
                func.strftime("%Y", Transaction.date),
                func.strftime("%m", Transaction.date),
                Transaction.type,
            )
            .order_by(
                func.strftime("%Y", Transaction.date).desc(),
                func.strftime("%m", Transaction.date).desc(),
            )
            .limit(months * 2)  # * 2 because income + expense per month
            .all()
        )

        # Pivot by (year, month)
        trend_map: dict = {}
        MONTH_NAMES = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                       "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

        for row in rows:
            key = (int(row.year), int(row.month))
            if key not in trend_map:
                trend_map[key] = {
                    "year": int(row.year),
                    "month": int(row.month),
                    "month_label": f"{MONTH_NAMES[int(row.month)]} {row.year}",
                    "income": Decimal("0"),
                    "expense": Decimal("0"),
                }
            if row.type == TransactionType.INCOME:
                trend_map[key]["income"] = Decimal(str(row.total))
            else:
                trend_map[key]["expense"] = Decimal(str(row.total))

        result = sorted(trend_map.values(), key=lambda x: (x["year"], x["month"]))
        for entry in result:
            entry["net"] = entry["income"] - entry["expense"]

        return result[-months:]

    def get_recent(self, limit: int = 10) -> List[Transaction]:
        return (
            self._active_query()
            .order_by(Transaction.created_at.desc())
            .limit(limit)
            .all()
        )
