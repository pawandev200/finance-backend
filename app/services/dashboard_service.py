"""
Dashboard Service
──────────────────
Computes aggregated financial data for dashboard views.

Design: Aggregations happen at the DB layer (TransactionRepository)
and this service focuses on composition + business presentation logic.
"""

from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.models.transaction import TransactionType
from app.repositories.transaction_repo import TransactionRepository
from app.schemas.dashboard import (
    CategoryBreakdown,
    DashboardAnalytics,
    DashboardSummary,
    DashboardTrends,
    MonthlyTrend,
    RecentTransaction,
)


class DashboardService:
    def __init__(self, db: Session):
        self.repo = TransactionRepository(db)

    def get_summary(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> DashboardSummary:
        """
        Core KPI metrics — available to all roles.
        Used for the top-level cards on a financial dashboard.
        """
        totals = self.repo.get_totals(date_from=date_from, date_to=date_to)
        return DashboardSummary(
            total_income=totals["total_income"],
            total_expense=totals["total_expense"],
            net_balance=totals["total_income"] - totals["total_expense"],
            transaction_count=totals["transaction_count"],
            income_count=totals["income_count"],
            expense_count=totals["expense_count"],
        )

    def get_analytics(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> DashboardAnalytics:
        """
        Full analytics — category breakdowns + recent activity.
        Requires ANALYST or ADMIN role.
        """
        summary = self.get_summary(date_from=date_from, date_to=date_to)

        income_breakdown = self.repo.get_category_breakdown(
            TransactionType.INCOME, date_from, date_to
        )
        expense_breakdown = self.repo.get_category_breakdown(
            TransactionType.EXPENSE, date_from, date_to
        )
        recent = self.repo.get_recent(limit=10)

        return DashboardAnalytics(
            summary=summary,
            income_by_category=[CategoryBreakdown(**row) for row in income_breakdown],
            expense_by_category=[CategoryBreakdown(**row) for row in expense_breakdown],
            recent_transactions=[
                RecentTransaction(
                    id=t.id,
                    amount=t.amount,
                    type=t.type.value,
                    category=t.category,
                    date=str(t.date),
                    notes=t.notes,
                )
                for t in recent
            ],
        )

    def get_trends(self, months: int = 12) -> DashboardTrends:
        """
        Monthly income vs expense time-series data for charts.
        Requires ANALYST or ADMIN role.
        """
        monthly_data = self.repo.get_monthly_trends(months=months)
        return DashboardTrends(
            monthly_trends=[MonthlyTrend(**row) for row in monthly_data],
            period_label=f"Last {months} months",
        )
