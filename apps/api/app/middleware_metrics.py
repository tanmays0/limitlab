from __future__ import annotations

import time
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.metrics_store import record

def _route_label(path: str) -> str:
    if path.startswith("/v1/policies/"):
        return "/v1/policies/{id}"
    return path

class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        started = time.perf_counter()
        response = await call_next(request)
        latency_ms = (time.perf_counter() - started) * 1000.0
        allowed: bool | None = None
        if request.url.path in ("/v1/consume", "/v1/check"):
            if response.status_code == 200:
                allowed = True
            elif response.status_code == 429:
                allowed = False
        record(
            _route_label(request.url.path),
            status_code=response.status_code,
            latency_ms=latency_ms,
            allowed=allowed,
        )
        return response
