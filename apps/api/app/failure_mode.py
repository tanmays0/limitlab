from __future__ import annotations

from dataclasses import dataclass

from app.config import settings

@dataclass(frozen=True)
class FailureAction:

    allow: bool
    http_status: int
    detail: str

def on_redis_unavailable() -> FailureAction:
    mode = settings.redis_failure_mode.strip().lower()
    if mode == "fail_open":
        return FailureAction(
            allow=True,
            http_status=200,
            detail="redis_unavailable_fail_open",
        )
    return FailureAction(
        allow=False,
        http_status=503,
        detail="redis_unavailable_fail_closed",
    )
