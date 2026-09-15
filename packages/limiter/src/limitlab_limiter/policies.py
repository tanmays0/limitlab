from __future__ import annotations

from datetime import datetime, timezone

from redis.asyncio import Redis

from limitlab_limiter.types import Algorithm, Policy

_PREFIX = "ll:policy:"

def policy_key(policy_id: str) -> str:
    return f"{_PREFIX}{policy_id}"

async def get_policy(redis: Redis, policy_id: str) -> Policy | None:
    data = await redis.hgetall(policy_key(policy_id))
    if not data:
        return None
    burst_raw = data.get("burst")
    return Policy(
        id=policy_id,
        limit=int(data["limit"]),
        window_seconds=int(data["window_seconds"]),
        algorithm=Algorithm(data["algorithm"]),
        burst=int(burst_raw) if burst_raw not in (None, "", "None") else None,
        updated_at=data.get("updated_at"),
    )

async def upsert_policy(redis: Redis, policy: Policy) -> Policy:
    updated = policy.model_copy(
        update={"updated_at": datetime.now(timezone.utc).isoformat()}
    )
    mapping = {
        "limit": str(updated.limit),
        "window_seconds": str(updated.window_seconds),
        "algorithm": updated.algorithm.value,
        "updated_at": updated.updated_at or "",
        "burst": "" if updated.burst is None else str(updated.burst),
    }
    await redis.hset(policy_key(updated.id), mapping=mapping)
    return updated
