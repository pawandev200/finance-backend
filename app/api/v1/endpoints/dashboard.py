"""
Dashboard Endpoints
────────────────────
GET /dashboard/summary    → KPI cards (ALL roles)
GET /dashboard/analytics  → Category breakdowns (ANALYST, ADMIN)
GET /dashboard/trends     → Monthly chart data (ANALYST, ADMIN)
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.permissions import Permission
from app.db.session import get_db
from app.schemas.dashboard import DashboardAnalytics, DashboardSummary, DashboardTrends
from app.services.dashboard_service import DashboardService

router = APIRouter()


@router.get(
    "/summary",
    response_model=DashboardSummary,
    summary="Dashboard Summary",
    dependencies=[Depends(require_permission(Permission.DASHBOARD_SUMMARY))],
)
def get_summary(
    date_from: Optional[date] = Query(default=None, description="Filter start date"),
    date_to: Optional[date] = Query(default=None, description="Filter end date"),
    db: Session = Depends(get_db),
):
    """
    Returns top-level KPI metrics:
    total income, total expense, net balance, transaction counts.

    Available to all authenticated roles (VIEWER, ANALYST, ADMIN).
    Optionally filter by date range.
    """
    service = DashboardService(db)
    return service.get_summary(date_from=date_from, date_to=date_to)


@router.get(
    "/analytics",
    response_model=DashboardAnalytics,
    summary="Dashboard Analytics",
    dependencies=[Depends(require_permission(Permission.DASHBOARD_ANALYTICS))],
)
def get_analytics(
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    db: Session = Depends(get_db),
):
    """
    Richer analytics including:
    - Summary KPIs
    - Income breakdown by category (with percentages)
    - Expense breakdown by category (with percentages)
    - 10 most recent transactions

    Requires ANALYST or ADMIN role.
    """
    service = DashboardService(db)
    return service.get_analytics(date_from=date_from, date_to=date_to)


@router.get(
    "/trends",
    response_model=DashboardTrends,
    summary="Monthly Trends",
    dependencies=[Depends(require_permission(Permission.DASHBOARD_TRENDS))],
)
def get_trends(
    months: int = Query(default=12, ge=1, le=24, description="Number of months to include"),
    db: Session = Depends(get_db),
):
    """
    Returns monthly income vs expense time-series data for charts.
    Each month includes: income total, expense total, net balance.

    Requires ANALYST or ADMIN role.
    """
    service = DashboardService(db)
    return service.get_trends(months=months)
