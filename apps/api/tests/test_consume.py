from __future__ import annotations

import os

import pytest
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/15")

async def _redis_up() -> bool:
    client = Redis.from_url(REDIS_URL, decode_responses=True)
    try:
        return bool(await client.ping())
    except Exception:
        return False
    finally:
        await client.aclose()

@pytest.fixture
async def client(monkeypatch: pytest.MonkeyPatch):
    if not await _redis_up():
        pytest.skip("Redis not available")
    monkeypatch.setenv("REDIS_URL", REDIS_URL)
    from app import config, redis_client
    from app.main import app

    config.settings.redis_url = REDIS_URL
    await redis_client.close_redis()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    await redis_client.close_redis()

@pytest.mark.asyncio
async def test_consume_allow_then_429(client: AsyncClient):
    r = await client.put(
        "/v1/policies/api-demo",
        json={
            "limit": 3,
            "window_seconds": 60,
            "algorithm": "token_bucket",
            "burst": 3,
        },
    )
    assert r.status_code == 200

    key = "user:api-1"
    await client.post("/v1/reset", json={"policy_id": "api-demo", "key": key})

    for _ in range(3):
        resp = await client.post(
            "/v1/consume",
            json={"policy_id": "api-demo", "key": key, "cost": 1},
        )
        assert resp.status_code == 200
        assert resp.json()["allowed"] is True
        assert "X-RateLimit-Remaining" in resp.headers

    denied = await client.post(
        "/v1/consume",
        json={"policy_id": "api-demo", "key": key, "cost": 1},
    )
    assert denied.status_code == 429
    body = denied.json()
    assert body["allowed"] is False
    assert body["remaining"] == 0
    assert "Retry-After" in denied.headers

@pytest.mark.asyncio
async def test_check_does_not_debit(client: AsyncClient):
    await client.put(
        "/v1/policies/api-check",
        json={
            "limit": 5,
            "window_seconds": 60,
            "algorithm": "token_bucket",
            "burst": 5,
        },
    )
    key = "user:check"
    await client.post("/v1/reset", json={"policy_id": "api-check", "key": key})

    c1 = await client.post(
        "/v1/check", json={"policy_id": "api-check", "key": key}
    )
    c2 = await client.post(
        "/v1/check", json={"policy_id": "api-check", "key": key}
    )
    assert c1.status_code == 200 and c2.status_code == 200
    assert c1.json()["remaining"] == c2.json()["remaining"] == 5

    consumed = await client.post(
        "/v1/consume", json={"policy_id": "api-check", "key": key}
    )
    assert consumed.status_code == 200
    assert consumed.json()["remaining"] == 4

@pytest.mark.asyncio
async def test_reset_restores_quota(client: AsyncClient):
    await client.put(
        "/v1/policies/api-reset",
        json={
            "limit": 1,
            "window_seconds": 60,
            "algorithm": "sliding_window",
        },
    )
    key = "user:reset"
    await client.post("/v1/reset", json={"policy_id": "api-reset", "key": key})
    assert (
        await client.post(
            "/v1/consume", json={"policy_id": "api-reset", "key": key}
        )
    ).status_code == 200
    assert (
        await client.post(
            "/v1/consume", json={"policy_id": "api-reset", "key": key}
        )
    ).status_code == 429
    assert (
        await client.post("/v1/reset", json={"policy_id": "api-reset", "key": key})
    ).json()["ok"] is True
    assert (
        await client.post(
            "/v1/consume", json={"policy_id": "api-reset", "key": key}
        )
    ).status_code == 200

@pytest.mark.asyncio
async def test_unknown_policy_404(client: AsyncClient):
    resp = await client.post(
        "/v1/consume",
        json={"policy_id": "missing-xyz", "key": "k"},
    )
    assert resp.status_code == 404
