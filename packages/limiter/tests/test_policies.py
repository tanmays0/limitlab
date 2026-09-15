import os

import pytest
from redis.asyncio import Redis

from limitlab_limiter import Algorithm, Policy, get_policy, upsert_policy

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/15")

async def _redis_up() -> bool:
    client = Redis.from_url(REDIS_URL, decode_responses=True)
    try:
        return bool(await client.ping())
    except Exception:
        return False
    finally:
        await client.aclose()

def test_policy_rejects_bad_id():
    with pytest.raises(Exception):
        Policy(
            id="bad id!",
            limit=10,
            window_seconds=10,
            algorithm=Algorithm.TOKEN_BUCKET,
        )

@pytest.mark.asyncio
async def test_upsert_and_get_roundtrip():
    if not await _redis_up():
        pytest.skip("Redis not available")
    redis = Redis.from_url(REDIS_URL, decode_responses=True)
    policy = Policy(
        id="demo-pol",
        limit=10,
        window_seconds=10,
        algorithm=Algorithm.SLIDING_WINDOW,
        burst=None,
    )
    stored = await upsert_policy(redis, policy)
    got = await get_policy(redis, "demo-pol")
    assert got is not None
    assert got.limit == 10
    assert got.algorithm == Algorithm.SLIDING_WINDOW
    assert stored.updated_at is not None
    await redis.aclose()
