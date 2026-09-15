from __future__ import annotations

import json

from fastapi import APIRouter, Query, Response

from app.metrics_store import render_prometheus, snapshot_json

router = APIRouter(tags=["metrics"])

@router.get("/metrics")
async def metrics(
    format: str = Query(default="prometheus", pattern="^(prometheus|json)$"),
) -> Response:
    if format == "json":
        return Response(
            content=json.dumps(snapshot_json()),
            media_type="application/json",
        )
    return Response(
        content=render_prometheus(),
        media_type="text/plain; version=0.0.4",
    )
