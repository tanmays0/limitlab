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
async def test_put_get_policy(client: AsyncClient):
    put = await client.put(
        "/v1/policies/ui-demo",
        json={
            "limit": 10,
            "window_seconds": 10,
            "algorithm": "token_bucket",
            "burst": 10,
        },
    )
    assert put.status_code == 200
    got = await client.get("/v1/policies/ui-demo")
    assert got.status_code == 200
    body = got.json()
    assert body["limit"] == 10
    assert body["algorithm"] == "token_bucket"

@pytest.mark.asyncio
async def test_invalid_limit_422(client: AsyncClient):
    resp = await client.put(
        "/v1/policies/bad",
        json={"limit": 0, "window_seconds": 10, "algorithm": "token_bucket"},
    )
    assert resp.status_code == 422
