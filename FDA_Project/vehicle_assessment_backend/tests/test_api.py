from fastapi.testclient import TestClient

from app.main import app, init_seed_data

init_seed_data()
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


def _auth_headers() -> dict[str, str]:
    login = client.post(
        "/auth/login",
        json={"email": "ops@insurer.com", "password": "password123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_v1_health_and_stats_endpoints():
    headers = _auth_headers()
    health = client.get("/health")
    assert health.status_code == 200
    health_payload = health.json()
    assert health_payload["database"] in {"up", "down"}
    assert "X-Request-Id" in health.headers
    assert "X-Response-Time-Ms" in health.headers

    stats = client.get("/api/v1/dashboard/stats", headers=headers)
    assert stats.status_code == 200
    assert "total_inspections" in stats.json()

    timeline = client.get("/api/v1/dashboard/timeline?days=7", headers=headers)
    assert timeline.status_code == 200
    assert len(timeline.json()["items"]) == 7

    capabilities = client.get("/api/v1/system/capabilities", headers=headers)
    assert capabilities.status_code == 200
    assert len(capabilities.json()["pipeline_steps"]) == 14
    assert "integrations" in capabilities.json()
    assert "celery" in capabilities.json()


def test_v1_vehicle_create_lookup_and_history():
    headers = _auth_headers()
    create = client.post(
        "/api/v1/vehicles",
        headers=headers,
        json={
            "number_plate": "MH01ZZ1234",
            "vin": "MA1ABCD1234567890",
            "vehicle_type": "4W",
            "make": "Tata",
            "model": "Nexon",
            "year": 2022,
            "fuel_type": "Petrol",
            "is_ev": False,
            "rto": "MH01",
        },
    )
    assert create.status_code == 201
    vehicle_id = create.json()["id"]

    lookup = client.get("/api/v1/vehicles/lookup?plate=MH01ZZ1234", headers=headers)
    assert lookup.status_code == 200
    assert lookup.json()["number_plate"] == "MH01ZZ1234"

    history = client.get(f"/api/v1/vehicles/{vehicle_id}/history", headers=headers)
    assert history.status_code == 200
    assert "vehicle" in history.json()


def test_v1_garages_webhooks_and_video_job():
    headers = _auth_headers()

    garages = client.get("/api/v1/garages/nearby?lat=19.07&lng=72.87", headers=headers)
    assert garages.status_code == 200
    assert isinstance(garages.json()["items"], list)
    assert len(garages.json()["items"]) >= 1
    assert "market_comparison" in garages.json()["items"][0]
    garage_id = garages.json()["items"][0]["id"]

    pricing = client.get(f"/api/v1/garages/{garage_id}/pricing", headers=headers)
    assert pricing.status_code == 200
    assert "pricing" in pricing.json()

    centers = client.get(
        "/api/v1/garages/insurance-centers?lat=19.07&lng=72.87", headers=headers
    )
    assert centers.status_code == 200
    assert isinstance(centers.json()["items"], list)

    register = client.post(
        "/api/v1/webhooks/register",
        headers=headers,
        json={
            "target_url": "https://github.com/webhook",
            "event_type": "inspection.completed",
        },
    )
    assert register.status_code == 201
    webhook_id = register.json()["id"]

    listed = client.get("/api/v1/webhooks", headers=headers)
    assert listed.status_code == 200
    assert any(item["id"] == webhook_id for item in listed.json()["items"])

    test_hook = client.post(f"/api/v1/webhooks/test/{webhook_id}", headers=headers)
    assert test_hook.status_code == 200
    assert isinstance(test_hook.json()["delivered"], bool)

    delete_hook = client.delete(f"/api/v1/webhooks/{webhook_id}", headers=headers)
    assert delete_hook.status_code == 204

    video = client.post(
        "/api/v1/analyze/video",
        headers=headers,
        files={"file": ("sample.webm", b"FAKE_VIDEO_BYTES", "video/webm")},
    )
    assert video.status_code == 202
    assert video.json()["estimated_seconds"] is not None
    job_id = video.json()["job_id"]

    result = client.get(f"/api/v1/results/{job_id}", headers=headers)
    assert result.status_code == 200
    assert result.json()["job_id"] == job_id
