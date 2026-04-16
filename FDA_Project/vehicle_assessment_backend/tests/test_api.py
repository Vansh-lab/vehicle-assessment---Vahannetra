from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_login_and_dashboard_access():
    login = client.post(
        "/auth/login",
        json={"email": "ops@insurer.com", "password": "password123"},
    )
    assert login.status_code == 200
    payload = login.json()
    assert payload["access_token"]
    assert payload["refresh_token"]

    headers = {"Authorization": f"Bearer {payload['access_token']}"}
    dashboard = client.get("/dashboard/overview", headers=headers)
    assert dashboard.status_code == 200
    body = dashboard.json()
    assert "fleet_health" in body
    assert "recent_inspections" in body


def test_protected_route_requires_auth():
    response = client.get("/dashboard/overview")
    assert response.status_code == 401


def test_claim_submit_flow():
    login = client.post(
        "/auth/login",
        json={"email": "ops@insurer.com", "password": "password123"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    claim = client.post(
        "/claims/submit",
        headers=headers,
        json={"inspection_id": "INSP-1021", "destination": "claims-core"},
    )
    assert claim.status_code == 200
    data = claim.json()
    assert data["status"] == "Submitted"
    assert data["inspection_id"] == "INSP-1021"
