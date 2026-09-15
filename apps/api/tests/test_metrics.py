from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

@pytest.mark.asyncio
async def test_metrics_prometheus_and_json():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        await ac.get("/health")
        prom = await ac.get("/metrics")
        assert prom.status_code == 200
        assert "limitlab_requests_total" in prom.text
        js = await ac.get("/metrics", params={"format": "json"})
        assert js.status_code == 200
        body = js.json()
        assert "requests_total" in body
        assert body["requests_total"] >= 1
