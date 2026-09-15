from __future__ import annotations

def refill_tokens(
    tokens: float,
    last_ms: int,
    now_ms: int,
    capacity: float,
    rate: float,
) -> tuple[float, int]:
    """Return (tokens_after_refill, last_ms)."""
    if rate <= 0 or capacity < 1:
        return max(0.0, min(tokens, capacity)), now_ms
    elapsed = max(0, now_ms - last_ms) / 1000.0
    tokens = min(capacity, tokens + elapsed * rate)
    return tokens, now_ms

def try_consume(
    tokens: float,
    capacity: float,
    rate: float,
    cost: int,
    *,
    debit: bool,
) -> tuple[bool, float, int]:
    """
    Attempt to take `cost` tokens after refill already applied.

    Returns (allowed, remaining_tokens, retry_after_sec).
    Rejects entirely when cost > tokens (no partial debit).
    """
    if cost < 1:
        return False, max(0.0, tokens), 1
    if tokens >= cost:
        remaining = tokens - cost if debit else tokens
        return True, max(0.0, remaining), 0
    need = cost - tokens
    retry_after = max(1, int((need / rate) + 0.999999)) if rate > 0 else 1
    return False, max(0.0, tokens), retry_after
