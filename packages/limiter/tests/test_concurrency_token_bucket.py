from __future__ import annotations

import asyncio
import os

import pytest
from redis.asyncio import Redis

from limitlab_limiter import Algorithm, Policy, evaluate, upsert_policy

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/15")

async def _redis_up() -> bool:
    client = Redis.from_url(REDIS_URL, decode_responses=True)
    try:
        return bool(await client.ping())
    except Exception:
        return False
    finally:
        await client.aclose()

@pytest.mark.asyncio
async def test_concurrent_consumes_never_over_admit():
    if not await _redis_up():
        pytest.skip("Redis not available")

    redis = Redis.from_url(REDIS_URL, decode_responses=True)
    policy = Policy(
        id="conc-tb",
        limit=20,
        window_seconds=60,
        algorithm=Algorithm.TOKEN_BUCKET,
        burst=20,
    )
    await upsert_policy(redis, policy)
    subject = "burst-user"
    await redis.delete(f"ll:tb:{policy.id}:{subject}")

    async def one() -> bool:
        d = await evaluate(redis, policy, subject, 1, consume=True)
        return d.allowed

    results = await asyncio.gather(*[one() for _ in range(40)])
    assert sum(1 for r in results if r) == 20
    assert sum(1 for r in results if not r) == 20
    await redis.aclose()
