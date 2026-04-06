"""
Transaction endpoint tests.
Covers CRUD operations and RBAC enforcement for all three roles.
"""

import pytest
from datetime import date


SAMPLE_TRANSACTION = {
    "amount": "1500.00",
    "type": "income",
    "category": "Salary",
    "date": str(date.today()),
    "notes": "Monthly salary",
}


class TestCreateTransaction:
    def test_admin_can_create(self, client, admin_token):
        response = client.post(
            "/api/v1/transactions/",
            json=SAMPLE_TRANSACTION,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["amount"] == "1500.00"
        assert data["type"] == "income"
        assert data["category"] == "Salary"

    def test_viewer_cannot_create(self, client, viewer_token):
        response = client.post(
            "/api/v1/transactions/",
            json=SAMPLE_TRANSACTION,
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert response.status_code == 403

    def test_analyst_cannot_create(self, client, analyst_token):
        response = client.post(
            "/api/v1/transactions/",
            json=SAMPLE_TRANSACTION,
            headers={"Authorization": f"Bearer {analyst_token}"},
        )
        assert response.status_code == 403

    def test_negative_amount_rejected(self, client, admin_token):
        response = client.post(
            "/api/v1/transactions/",
            json={**SAMPLE_TRANSACTION, "amount": "-100"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 422

    def test_zero_amount_rejected(self, client, admin_token):
        response = client.post(
            "/api/v1/transactions/",
            json={**SAMPLE_TRANSACTION, "amount": "0"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 422

    def test_missing_required_fields(self, client, admin_token):
        response = client.post(
            "/api/v1/transactions/",
            json={"amount": "100"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 422


class TestReadTransactions:
    @pytest.fixture(autouse=True)
    def seed_transaction(self, client, admin_token):
        resp = client.post(
            "/api/v1/transactions/",
            json=SAMPLE_TRANSACTION,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self.transaction_id = resp.json()["id"]

    def test_viewer_can_list(self, client, viewer_token):
        response = client.get(
            "/api/v1/transactions/",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "pages" in data

    def test_filter_by_type(self, client, viewer_token):
        response = client.get(
            "/api/v1/transactions/?type=income",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert response.status_code == 200
        for item in response.json()["items"]:
            assert item["type"] == "income"

    def test_get_by_id(self, client, viewer_token):
        response = client.get(
            f"/api/v1/transactions/{self.transaction_id}",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert response.status_code == 200
        assert response.json()["id"] == self.transaction_id

    def test_get_nonexistent(self, client, viewer_token):
        response = client.get(
            "/api/v1/transactions/nonexistent-id",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert response.status_code == 404

    def test_pagination(self, client, viewer_token):
        response = client.get(
            "/api/v1/transactions/?page=1&size=5",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 5


class TestUpdateDeleteTransaction:
    @pytest.fixture(autouse=True)
    def seed_transaction(self, client, admin_token):
        resp = client.post(
            "/api/v1/transactions/",
            json=SAMPLE_TRANSACTION,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self.transaction_id = resp.json()["id"]

    def test_admin_can_update(self, client, admin_token):
        response = client.patch(
            f"/api/v1/transactions/{self.transaction_id}",
            json={"amount": "2000.00", "notes": "Updated salary"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        assert response.json()["amount"] == "2000.00"

    def test_viewer_cannot_update(self, client, viewer_token):
        response = client.patch(
            f"/api/v1/transactions/{self.transaction_id}",
            json={"amount": "2000.00"},
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert response.status_code == 403

    def test_admin_can_delete(self, client, admin_token):
        response = client.delete(
            f"/api/v1/transactions/{self.transaction_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200

        # Deleted record should return 404
        get_response = client.get(
            f"/api/v1/transactions/{self.transaction_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert get_response.status_code == 404

    def test_viewer_cannot_delete(self, client, viewer_token):
        response = client.delete(
            f"/api/v1/transactions/{self.transaction_id}",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert response.status_code == 403
