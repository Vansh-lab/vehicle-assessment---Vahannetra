import pytest
from httpx import ASGITransport, AsyncClient

from app.database import async_engine
from app.main import app, init_seed_data


@pytest.fixture(scope="session", autouse=True)
def seed_data_once() -> None:
    init_seed_data()


@pytest.fixture
async def client() -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as test_client:
        yield test_client
    await async_engine.dispose()


async def test_login_and_dashboard_access(client: AsyncClient):
    login = await client.post(
        "/auth/login",
        json={"email": "ops@insurer.com", "password": "password123"},
    )
    assert login.status_code == 200
    payload = login.json()
    assert payload["access_token"]
    assert payload["refresh_token"]

    headers = {"Authorization": f"Bearer {payload['access_token']}"}
    dashboard = await client.get("/dashboard/overview", headers=headers)
    assert dashboard.status_code == 200
    body = dashboard.json()
    assert "fleet_health" in body
    assert "recent_inspections" in body


async def test_protected_route_requires_auth(client: AsyncClient):
    response = await client.get("/dashboard/overview")
    assert response.status_code == 401


async def test_claim_submit_flow(client: AsyncClient):
    login = await client.post(
        "/auth/login",
        json={"email": "ops@insurer.com", "password": "password123"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    claim = await client.post(
        "/claims/submit",
        headers=headers,
        json={"inspection_id": "INSP-1021", "destination": "claims-core"},
    )
    assert claim.status_code == 200
    data = claim.json()
    assert data["status"] == "Submitted"
    assert data["inspection_id"] == "INSP-1021"


async def _auth_headers(client: AsyncClient) -> dict[str, str]:
    login = await client.post(
        "/auth/login",
        json={"email": "ops@insurer.com", "password": "password123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def test_v1_health_and_stats_endpoints(client: AsyncClient):
    headers = await _auth_headers(client)
    health = await client.get("/health")
    assert health.status_code == 200
    health_payload = health.json()
    assert health_payload["database"] in {"up", "down"}
    assert "X-Request-Id" in health.headers
    assert "X-Response-Time-Ms" in health.headers

    stats = await client.get("/api/v1/dashboard/stats", headers=headers)
    assert stats.status_code == 200
    assert "total_inspections" in stats.json()

    timeline = await client.get("/api/v1/dashboard/timeline?days=7", headers=headers)
    assert timeline.status_code == 200
    assert len(timeline.json()["items"]) == 7

    capabilities = await client.get("/api/v1/system/capabilities", headers=headers)
    assert capabilities.status_code == 200
    assert len(capabilities.json()["pipeline_steps"]) == 14
    assert "integrations" in capabilities.json()
    assert "celery" in capabilities.json()

    queue_obs = await client.get("/api/v1/system/queue/observability", headers=headers)
    assert queue_obs.status_code == 200
    queue_payload = queue_obs.json()
    assert "dlq_open" in queue_payload
    assert "escalation_required" in queue_payload


async def test_v1_vehicle_create_lookup_and_history(client: AsyncClient):
    headers = await _auth_headers(client)
    create = await client.post(
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

    lookup = await client.get(
        "/api/v1/vehicles/lookup?plate=MH01ZZ1234", headers=headers
    )
    assert lookup.status_code == 200
    assert lookup.json()["number_plate"] == "MH01ZZ1234"

    history = await client.get(
        f"/api/v1/vehicles/{vehicle_id}/history", headers=headers
    )
    assert history.status_code == 200
    assert "vehicle" in history.json()


async def test_v1_garages_webhooks_and_video_job(client: AsyncClient):
    headers = await _auth_headers(client)

    garages = await client.get(
        "/api/v1/garages/nearby?lat=19.07&lng=72.87", headers=headers
    )
    assert garages.status_code == 200
    assert isinstance(garages.json()["items"], list)
    assert len(garages.json()["items"]) >= 1
    assert "market_comparison" in garages.json()["items"][0]
    garage_id = garages.json()["items"][0]["id"]

    pricing = await client.get(f"/api/v1/garages/{garage_id}/pricing", headers=headers)
    assert pricing.status_code == 200
    assert "pricing" in pricing.json()

    centers = await client.get(
        "/api/v1/garages/insurance-centers?lat=19.07&lng=72.87", headers=headers
    )
    assert centers.status_code == 200
    assert isinstance(centers.json()["items"], list)

    register = await client.post(
        "/api/v1/webhooks/register",
        headers=headers,
        json={
            "target_url": "https://github.com/webhook",
            "event_type": "inspection.completed",
        },
    )
    assert register.status_code == 201
    webhook_id = register.json()["id"]

    listed = await client.get("/api/v1/webhooks", headers=headers)
    assert listed.status_code == 200
    assert any(item["id"] == webhook_id for item in listed.json()["items"])

    dlq = await client.get("/api/v1/webhooks/dlq", headers=headers)
    assert dlq.status_code == 200
    assert isinstance(dlq.json()["items"], list)

    test_hook = await client.post(
        f"/api/v1/webhooks/test/{webhook_id}", headers=headers
    )
    assert test_hook.status_code == 200
    assert isinstance(test_hook.json()["delivered"], bool)

    delete_hook = await client.delete(f"/api/v1/webhooks/{webhook_id}", headers=headers)
    assert delete_hook.status_code == 204

    video = await client.post(
        "/api/v1/analyze/video",
        headers=headers,
        files={"file": ("sample.webm", b"FAKE_VIDEO_BYTES", "video/webm")},
    )
    assert video.status_code == 202
    assert video.json()["estimated_seconds"] is not None
    job_id = video.json()["job_id"]

    result = await client.get(f"/api/v1/results/{job_id}", headers=headers)
    assert result.status_code == 200
    assert result.json()["job_id"] == job_id
