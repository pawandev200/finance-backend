from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel


class CategoryBreakdown(BaseModel):
    category: str
    total: Decimal
    count: int
    percentage: float


class MonthlyTrend(BaseModel):
    year: int
    month: int
    month_label: str   # e.g. "Jan 2024"
    income: Decimal
    expense: Decimal
    net: Decimal


class RecentTransaction(BaseModel):
    id: str
    amount: Decimal
    type: str
    category: str
    date: str
    notes: Optional[str]


class DashboardSummary(BaseModel):
    """High-level financial snapshot — the main dashboard card data."""
    total_income: Decimal
    total_expense: Decimal
    net_balance: Decimal
    transaction_count: int
    income_count: int
    expense_count: int


class DashboardAnalytics(BaseModel):
    """
    Richer analytics for ANALYST and ADMIN roles.
    Includes category breakdowns and recent activity.
    """
    summary: DashboardSummary
    income_by_category: List[CategoryBreakdown]
    expense_by_category: List[CategoryBreakdown]
    recent_transactions: List[RecentTransaction]


class DashboardTrends(BaseModel):
    """Time-series data for charts — ANALYST and ADMIN roles."""
    monthly_trends: List[MonthlyTrend]
    period_label: str   # e.g. "Last 12 months"
