from __future__ import annotations

import os

from limitlab_limiter import memory_store
from limitlab_limiter.policies import get_policy as redis_get_policy
from limitlab_limiter.policies import upsert_policy as redis_upsert_policy
from limitlab_limiter.engine import evaluate as redis_evaluate
from limitlab_limiter.engine import reset_subject as redis_reset
from limitlab_limiter.types import Decision, Policy
from app.redis_client import get_redis

def use_memory() -> bool:
    mode = os.getenv("LIMITLAB_STORE", "").strip().lower()
    if mode == "memory":
        return True
    if mode == "redis":
        return False
    return not os.getenv("REDIS_URL", "").strip()

async def load_policy(policy_id: str) -> Policy | None:
    if use_memory():
        return await memory_store.get_policy(policy_id)
    redis = await get_redis()
    return await redis_get_policy(redis, policy_id)

async def save_policy(policy: Policy) -> Policy:
    if use_memory():
        return await memory_store.upsert_policy(policy)
    redis = await get_redis()
    return await redis_upsert_policy(redis, policy)

async def decide(
    policy: Policy, subject: str, cost: int, *, consume: bool
) -> Decision:
    if use_memory():
        return await memory_store.evaluate(
            policy, subject, cost, consume=consume
        )
    redis = await get_redis()
    return await redis_evaluate(redis, policy, subject, cost, consume=consume)

async def reset_key(policy: Policy, subject: str) -> None:
    if use_memory():
        await memory_store.reset_subject(policy, subject)
        return
    redis = await get_redis()
    await redis_reset(redis, policy, subject)
