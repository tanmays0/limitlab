from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field
from redis.exceptions import RedisError

from app.failure_mode import on_redis_unavailable
from app.headers import apply_rate_limit_headers
from app.store import decide, load_policy, reset_key, save_policy, use_memory
from limitlab_limiter import Algorithm, Decision, Policy

router = APIRouter(prefix="/v1", tags=["v1"])

class LimitRequest(BaseModel):
    policy_id: str = Field(min_length=1, max_length=64)
    key: str = Field(min_length=1, max_length=256)
    cost: int = Field(default=1, ge=1)

class ResetRequest(BaseModel):
    policy_id: str = Field(min_length=1, max_length=64)
    key: str = Field(min_length=1, max_length=256)

class PolicyBody(BaseModel):
    limit: int = Field(ge=1)
    window_seconds: int = Field(ge=1)
    algorithm: Algorithm
    burst: Optional[int] = Field(default=None, ge=1)

async def _load_policy(policy_id: str) -> Policy:
    try:
        policy = await load_policy(policy_id)
    except RedisError as exc:
        action = on_redis_unavailable()
        raise HTTPException(status_code=action.http_status, detail=action.detail) from exc
    if policy is None:
        raise HTTPException(status_code=404, detail=f"policy not found: {policy_id}")
    return policy

async def _decide(body: LimitRequest, *, consume: bool) -> Decision:
    policy = await _load_policy(body.policy_id)
    try:
        return await decide(policy, body.key, body.cost, consume=consume)
    except RedisError as exc:
        action = on_redis_unavailable()
        if action.allow:
            return Decision(
                allowed=True,
                limit=policy.limit,
                remaining=policy.limit,
                reset=0,
                algorithm=policy.algorithm,
                retry_after=None,
            )
        raise HTTPException(status_code=action.http_status, detail=action.detail) from exc

@router.post("/check")
async def check_limit(body: LimitRequest, response: Response) -> Decision:
    decision = await _decide(body, consume=False)
    apply_rate_limit_headers(response, decision)
    return decision

@router.post("/consume")
async def consume_limit(body: LimitRequest, response: Response) -> Decision:
    decision = await _decide(body, consume=True)
    apply_rate_limit_headers(response, decision)
    if not decision.allowed:
        response.status_code = 429
    return decision

@router.post("/reset")
async def reset_limit(body: ResetRequest) -> dict[str, bool]:
    policy = await _load_policy(body.policy_id)
    try:
        await reset_key(policy, body.key)
    except RedisError as exc:
        action = on_redis_unavailable()
        raise HTTPException(status_code=action.http_status, detail=action.detail) from exc
    return {"ok": True}

@router.get("/policies/{policy_id}")
async def fetch_policy(policy_id: str) -> Policy:
    return await _load_policy(policy_id)

@router.put("/policies/{policy_id}")
async def put_policy(policy_id: str, body: PolicyBody) -> Policy:
    try:
        policy = Policy(
            id=policy_id,
            limit=body.limit,
            window_seconds=body.window_seconds,
            algorithm=body.algorithm,
            burst=body.burst,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    try:
        return await save_policy(policy)
    except RedisError as exc:
        action = on_redis_unavailable()
        raise HTTPException(status_code=action.http_status, detail=action.detail) from exc

@router.get("/store")
async def store_info() -> dict[str, str]:
    return {"store": "memory" if use_memory() else "redis"}
