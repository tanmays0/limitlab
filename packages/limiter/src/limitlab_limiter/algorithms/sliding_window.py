from __future__ import annotations

from pathlib import Path
from time import time

from redis.asyncio import Redis

from limitlab_limiter.types import Algorithm, Decision, Policy

_LUA: str | None = None

def _load_lua() -> str:
    global _LUA
    if _LUA is None:
        lua_path = Path(__file__).resolve().parent.parent / "lua" / "sliding_window.lua"
        _LUA = lua_path.read_text(encoding="utf-8")
    return _LUA

def window_key(policy_id: str, subject: str) -> str:
    return f"ll:sw:{policy_id}:{subject}"

async def evaluate(
    redis: Redis,
    policy: Policy,
    subject: str,
    cost: int = 1,
    *,
    consume: bool,
) -> Decision:
    now_ms = int(time() * 1000)
    script = redis.register_script(_load_lua())
    result = await script(
        keys=[window_key(policy.id, subject)],
        args=[policy.limit, policy.window_seconds, now_ms, cost, 1 if consume else 0],
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
        algorithm=Algorithm.SLIDING_WINDOW,
        retry_after=retry_after,
    )

async def reset_key(redis: Redis, policy_id: str, subject: str) -> None:
    await redis.delete(window_key(policy_id, subject))
