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
async def test_sliding_window_allow_then_deny():
    if not await _redis_up():
        pytest.skip("Redis not available")
    redis = Redis.from_url(REDIS_URL, decode_responses=True)
    policy = Policy(
        id="sw-demo",
        limit=5,
        window_seconds=30,
        algorithm=Algorithm.SLIDING_WINDOW,
    )
    await upsert_policy(redis, policy)
    key = "sw-user"
    await redis.delete(f"ll:sw:{policy.id}:{key}")

    for _ in range(5):
        d = await evaluate(redis, policy, key, 1, consume=True)
        assert d.allowed is True
    denied = await evaluate(redis, policy, key, 1, consume=True)
    assert denied.allowed is False
    assert denied.remaining == 0
    assert denied.retry_after is not None and denied.retry_after >= 1
    await redis.aclose()
