from __future__ import annotations

from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, Field

class Algorithm(StrEnum):
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"

class Policy(BaseModel):
    id: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9:_-]+$")
    limit: int = Field(ge=1)
    window_seconds: int = Field(ge=1)
    algorithm: Algorithm
    burst: Optional[int] = Field(default=None, ge=1)
    updated_at: Optional[str] = None

class Decision(BaseModel):
    allowed: bool
    limit: int
    remaining: int = Field(ge=0)
    reset: int
    algorithm: Algorithm
    retry_after: Optional[int] = None
