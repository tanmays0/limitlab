from __future__ import annotations

from pathlib import Path
from time import time

from redis.asyncio import Redis

from limitlab_limiter.types import Algorithm, Decision, Policy

_LUA: str | None = None

def _load_lua() -> str:
    global _LUA
    if _LUA is None:
        lua_path = Path(__file__).resolve().parent.parent / "lua" / "token_bucket.lua"
        _LUA = lua_path.read_text(encoding="utf-8")
    return _LUA

def bucket_key(policy_id: str, subject: str) -> str:
    return f"ll:tb:{policy_id}:{subject}"

def _capacity_and_rate(policy: Policy) -> tuple[float, float]:
    capacity = float(policy.burst if policy.burst is not None else policy.limit)
    rate = float(policy.limit) / float(policy.window_seconds)
    return capacity, rate

async def evaluate(
    redis: Redis,
    policy: Policy,
    subject: str,
    cost: int = 1,
    *,
    consume: bool,
) -> Decision:
    capacity, rate = _capacity_and_rate(policy)
    now_ms = int(time() * 1000)
    script = redis.register_script(_load_lua())
    result = await script(
        keys=[bucket_key(policy.id, subject)],
        args=[capacity, rate, now_ms, cost, 1 if consume else 0],
    )
    allowed = int(result[0]) == 1
    remaining = max(0, int(result[1]))
    reset = int(result[2])
    retry_after = int(result[3]) if not allowed else None
    return Decision(
        allowed=allowed,
        limit=policy.limit,
        remaining=remaining,
        reset=reset,
        algorithm=Algorithm.TOKEN_BUCKET,
        retry_after=retry_after,
    )

async def reset_key(redis: Redis, policy_id: str, subject: str) -> None:
    await redis.delete(bucket_key(policy_id, subject))
