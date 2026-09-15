from __future__ import annotations

from typing import assert_never

from redis.asyncio import Redis

from limitlab_limiter.algorithms import sliding_window, token_bucket
from limitlab_limiter.types import Algorithm, Decision, Policy

async def evaluate(
    redis: Redis,
    policy: Policy,
    subject: str,
    cost: int = 1,
    *,
    consume: bool,
) -> Decision:
    if policy.algorithm is Algorithm.TOKEN_BUCKET:
        return await token_bucket.evaluate(
            redis, policy, subject, cost, consume=consume
        )
    if policy.algorithm is Algorithm.SLIDING_WINDOW:
        return await sliding_window.evaluate(
            redis, policy, subject, cost, consume=consume
        )
    assert_never(policy.algorithm)

async def reset_subject(redis: Redis, policy: Policy, subject: str) -> None:
    if policy.algorithm is Algorithm.TOKEN_BUCKET:
        await token_bucket.reset_key(redis, policy.id, subject)
        return
    if policy.algorithm is Algorithm.SLIDING_WINDOW:
        await sliding_window.reset_key(redis, policy.id, subject)
        return
    assert_never(policy.algorithm)
