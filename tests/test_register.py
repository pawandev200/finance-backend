"""
Registration endpoint tests.
Verifies the public register flow and role enforcement.
"""


class TestRegister:
    def test_register_success(self, client):
        response = client.post("/api/v1/auth/register", json={
            "email": "newuser@example.com",
            "full_name": "New User",
            "password": "Password1",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        # Critical: self-registered users MUST always be VIEWER
        assert data["role"] == "viewer"
        assert data["is_active"] is True

    def test_register_role_always_viewer(self, client):
        """
        Even if a clever user somehow passes a role field, they should get VIEWER.
        RegisterRequest schema doesn't accept 'role', so it's ignored by Pydantic.
        """
        response = client.post("/api/v1/auth/register", json={
            "email": "tricky@example.com",
            "full_name": "Tricky User",
            "password": "Password1",
            "role": "admin",  # This field is not in RegisterRequest — ignored
        })
        assert response.status_code == 201
        assert response.json()["role"] == "viewer"

    def test_register_duplicate_email(self, client):
        payload = {
            "email": "duplicate@example.com",
            "full_name": "First",
            "password": "Password1",
        }
        client.post("/api/v1/auth/register", json=payload)
        response = client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 409

    def test_register_weak_password(self, client):
        response = client.post("/api/v1/auth/register", json={
            "email": "weak@example.com",
            "full_name": "Weak",
            "password": "short",
        })
        assert response.status_code == 422

    def test_register_no_digit_password(self, client):
        response = client.post("/api/v1/auth/register", json={
            "email": "nodigit@example.com",
            "full_name": "No Digit",
            "password": "NoDigitHere",
        })
        assert response.status_code == 422

    def test_register_invalid_email(self, client):
        response = client.post("/api/v1/auth/register", json={
            "email": "not-an-email",
            "full_name": "Bad Email",
            "password": "Password1",
        })
        assert response.status_code == 422

    def test_register_then_login(self, client):
        """Full flow: register → login → get /me"""
        client.post("/api/v1/auth/register", json={
            "email": "fullflow@example.com",
            "full_name": "Full Flow",
            "password": "FlowPass1",
        })
        login_resp = client.post("/api/v1/auth/login", json={
            "email": "fullflow@example.com",
            "password": "FlowPass1",
        })
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]

        me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_resp.status_code == 200
        assert me_resp.json()["email"] == "fullflow@example.com"
        assert me_resp.json()["role"] == "viewer"

    def test_viewer_cannot_access_analytics_after_register(self, client):
        """Self-registered VIEWER should be blocked from ANALYST endpoints."""
        client.post("/api/v1/auth/register", json={
            "email": "justviewer@example.com",
            "full_name": "Just Viewer",
            "password": "ViewOnly1",
        })
        login_resp = client.post("/api/v1/auth/login", json={
            "email": "justviewer@example.com",
            "password": "ViewOnly1",
        })
        token = login_resp.json()["access_token"]

        resp = client.get("/api/v1/dashboard/analytics",
                          headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403
