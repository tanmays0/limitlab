from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from datetime import datetime, timezone

from limitlab_limiter.algorithms.refill import refill_tokens, try_consume
from limitlab_limiter.types import Algorithm, Decision, Policy

_lock = asyncio.Lock()
_policies: dict[str, Policy] = {}
_buckets: dict[str, tuple[float, int]] = {}
_windows: dict[str, deque[int]] = defaultdict(deque)

def _bk(policy_id: str, subject: str) -> str:
    return f"{policy_id}:{subject}"

async def get_policy(policy_id: str) -> Policy | None:
    async with _lock:
        return _policies.get(policy_id)

async def upsert_policy(policy: Policy) -> Policy:
    updated = policy.model_copy(
        update={"updated_at": datetime.now(timezone.utc).isoformat()}
    )
    async with _lock:
        _policies[updated.id] = updated
    return updated

async def evaluate(
    policy: Policy,
    subject: str,
    cost: int = 1,
    *,
    consume: bool,
) -> Decision:
    async with _lock:
        if policy.algorithm is Algorithm.TOKEN_BUCKET:
            return _eval_token_bucket(policy, subject, cost, consume=consume)
        return _eval_sliding_window(policy, subject, cost, consume=consume)

def _eval_token_bucket(
    policy: Policy, subject: str, cost: int, *, consume: bool
) -> Decision:
    key = _bk(policy.id, subject)
    capacity = float(policy.burst if policy.burst is not None else policy.limit)
    rate = float(policy.limit) / float(policy.window_seconds)
    now_ms = int(time.time() * 1000)
    tokens, last_ms = _buckets.get(key, (capacity, now_ms))
    tokens, last_ms = refill_tokens(tokens, last_ms, now_ms, capacity, rate)
    allowed, remaining, retry = try_consume(
        tokens, capacity, rate, cost, debit=consume
    )
    if consume:
        _buckets[key] = (remaining, last_ms)
    full_in = 0
    if remaining < capacity and rate > 0:
        full_in = int((capacity - remaining) / rate + 0.999999)
    reset = int(now_ms / 1000) + full_in
    return Decision(
        allowed=allowed,
        limit=policy.limit,
        remaining=max(0, int(remaining)),
        reset=reset,
        algorithm=Algorithm.TOKEN_BUCKET,
        retry_after=retry if not allowed else None,
    )

def _eval_sliding_window(
    policy: Policy, subject: str, cost: int, *, consume: bool
) -> Decision:
    key = _bk(policy.id, subject)
    now_ms = int(time.time() * 1000)
    window_ms = policy.window_seconds * 1000
    cutoff = now_ms - window_ms
    q = _windows[key]
    while q and q[0] <= cutoff:
        q.popleft()
    count = len(q)
    remaining_before = max(0, policy.limit - count)
    if count + cost <= policy.limit:
        if consume:
            for _ in range(cost):
                q.append(now_ms)
            remaining = max(0, policy.limit - len(q))
        else:
            remaining = remaining_before
        return Decision(
            allowed=True,
            limit=policy.limit,
            remaining=remaining,
            reset=int(now_ms / 1000) + policy.window_seconds,
            algorithm=Algorithm.SLIDING_WINDOW,
            retry_after=None,
        )
    retry_after = policy.window_seconds
    if q:
        oldest = q[0]
        retry_after = max(1, int((oldest + window_ms - now_ms) / 1000 + 0.999))
    return Decision(
        allowed=False,
        limit=policy.limit,
        remaining=remaining_before,
        reset=int(now_ms / 1000) + policy.window_seconds,
        algorithm=Algorithm.SLIDING_WINDOW,
        retry_after=retry_after,
    )

async def reset_subject(policy: Policy, subject: str) -> None:
    key = _bk(policy.id, subject)
    async with _lock:
        _buckets.pop(key, None)
        _windows.pop(key, None)
