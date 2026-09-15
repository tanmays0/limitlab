from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field

@dataclass
class _RouteStats:
    count: int = 0
    errors: int = 0
    latency_sum_ms: float = 0.0
    latency_max_ms: float = 0.0
    buckets: dict[str, int] = field(
        default_factory=lambda: {
            "5": 0,
            "10": 0,
            "25": 0,
            "50": 0,
            "100": 0,
            "250": 0,
            "500": 0,
            "+Inf": 0,
        }
    )

_lock = threading.Lock()
_started = time.time()
_routes: dict[str, _RouteStats] = defaultdict(_RouteStats)
_outcomes: dict[str, int] = defaultdict(int)

def record(
    route: str,
    *,
    status_code: int,
    latency_ms: float,
    allowed: bool | None = None,
) -> None:
    with _lock:
        stats = _routes[route]
        stats.count += 1
        stats.latency_sum_ms += latency_ms
        if latency_ms > stats.latency_max_ms:
            stats.latency_max_ms = latency_ms
        if status_code >= 500:
            stats.errors += 1
        for edge in ("5", "10", "25", "50", "100", "250", "500"):
            if latency_ms <= float(edge):
                stats.buckets[edge] += 1
                break
        else:
            stats.buckets["+Inf"] += 1

        if allowed is True:
            _outcomes["allow"] += 1
        elif allowed is False:
            _outcomes["deny"] += 1
        else:
            _outcomes["other"] += 1

def snapshot_json() -> dict:
    with _lock:
        uptime = time.time() - _started
        routes = {}
        total = 0
        for name, s in _routes.items():
            total += s.count
            avg = (s.latency_sum_ms / s.count) if s.count else 0.0
            routes[name] = {
                "count": s.count,
                "errors": s.errors,
                "latency_avg_ms": round(avg, 3),
                "latency_max_ms": round(s.latency_max_ms, 3),
                "buckets_ms": dict(s.buckets),
            }
        rps = (total / uptime) if uptime > 0 else 0.0
        return {
            "uptime_seconds": round(uptime, 3),
            "requests_total": total,
            "approx_rps": round(rps, 3),
            "outcomes": dict(_outcomes),
            "routes": routes,
        }

def render_prometheus() -> str:
    data = snapshot_json()
    lines: list[str] = [
        "# HELP limitlab_uptime_seconds Process uptime",
        "# TYPE limitlab_uptime_seconds gauge",
        f"limitlab_uptime_seconds {data['uptime_seconds']}",
        "# HELP limitlab_requests_total Total HTTP requests",
        "# TYPE limitlab_requests_total counter",
    ]
    with _lock:
        for route, s in _routes.items():
            lines.append(
                f'limitlab_requests_total{{route="{route}"}} {s.count}'
            )
        lines.append("# HELP limitlab_request_errors_total 5xx responses")
        lines.append("# TYPE limitlab_request_errors_total counter")
        for route, s in _routes.items():
            lines.append(
                f'limitlab_request_errors_total{{route="{route}"}} {s.errors}'
            )
        lines.append("# HELP limitlab_outcomes_total allow/deny/other")
        lines.append("# TYPE limitlab_outcomes_total counter")
        for outcome, n in _outcomes.items():
            lines.append(f'limitlab_outcomes_total{{outcome="{outcome}"}} {n}')
        lines.append(
            "# HELP limitlab_request_latency_ms_sum Cumulative latency ms"
        )
        lines.append("# TYPE limitlab_request_latency_ms_sum counter")
        for route, s in _routes.items():
            lines.append(
                f'limitlab_request_latency_ms_sum{{route="{route}"}} {s.latency_sum_ms}'
            )
        lines.append("# HELP limitlab_request_latency_ms_max Max latency ms")
        lines.append("# TYPE limitlab_request_latency_ms_max gauge")
        for route, s in _routes.items():
            lines.append(
                f'limitlab_request_latency_ms_max{{route="{route}"}} {s.latency_max_ms}'
            )
    lines.append("")
    return "\n".join(lines)
