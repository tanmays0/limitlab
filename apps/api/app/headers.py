from __future__ import annotations

from fastapi import Response

from limitlab_limiter.types import Decision

def apply_rate_limit_headers(response: Response, decision: Decision) -> None:
    response.headers["X-RateLimit-Limit"] = str(decision.limit)
    response.headers["X-RateLimit-Remaining"] = str(decision.remaining)
    response.headers["X-RateLimit-Reset"] = str(decision.reset)
    if decision.retry_after is not None and not decision.allowed:
        response.headers["Retry-After"] = str(decision.retry_after)
