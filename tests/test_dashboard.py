"""Dashboard endpoint tests — role-based access and response shapes."""

from datetime import date
import pytest


@pytest.fixture
def seeded_transactions(client, admin_token):
    """Creates a few transactions for dashboard aggregation tests."""
    transactions = [
        {"amount": "5000", "type": "income",  "category": "Salary",    "date": str(date.today())},
        {"amount": "1200", "type": "expense", "category": "Rent",      "date": str(date.today())},
        {"amount": "300",  "type": "expense", "category": "Groceries", "date": str(date.today())},
        {"amount": "800",  "type": "income",  "category": "Freelance", "date": str(date.today())},
    ]
    for t in transactions:
        client.post(
            "/api/v1/transactions/",
            json=t,
            headers={"Authorization": f"Bearer {admin_token}"},
        )


class TestDashboardSummary:
    def test_viewer_can_access_summary(self, client, viewer_token, seeded_transactions):
        response = client.get(
            "/api/v1/dashboard/summary",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_income" in data
        assert "total_expense" in data
        assert "net_balance" in data
        assert "transaction_count" in data

    def test_summary_math_is_correct(self, client, admin_token, seeded_transactions):
        response = client.get(
            "/api/v1/dashboard/summary",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        data = response.json()
        expected_net = float(data["total_income"]) - float(data["total_expense"])
        assert abs(float(data["net_balance"]) - expected_net) < 0.01

    def test_unauthenticated_denied(self, client):
        response = client.get("/api/v1/dashboard/summary")
        assert response.status_code == 401


class TestDashboardAnalytics:
    def test_analyst_can_access(self, client, analyst_token, seeded_transactions):
        response = client.get(
            "/api/v1/dashboard/analytics",
            headers={"Authorization": f"Bearer {analyst_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "income_by_category" in data
        assert "expense_by_category" in data
        assert "recent_transactions" in data

    def test_viewer_cannot_access_analytics(self, client, viewer_token):
        response = client.get(
            "/api/v1/dashboard/analytics",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert response.status_code == 403

    def test_admin_can_access(self, client, admin_token):
        response = client.get(
            "/api/v1/dashboard/analytics",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200


class TestDashboardTrends:
    def test_analyst_can_access_trends(self, client, analyst_token):
        response = client.get(
            "/api/v1/dashboard/trends",
            headers={"Authorization": f"Bearer {analyst_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "monthly_trends" in data
        assert "period_label" in data

    def test_viewer_cannot_access_trends(self, client, viewer_token):
        response = client.get(
            "/api/v1/dashboard/trends",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert response.status_code == 403

    def test_custom_months_param(self, client, analyst_token):
        response = client.get(
            "/api/v1/dashboard/trends?months=6",
            headers={"Authorization": f"Bearer {analyst_token}"},
        )
        assert response.status_code == 200
        assert "6" in response.json()["period_label"]
