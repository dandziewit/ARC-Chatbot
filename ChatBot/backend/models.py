from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=3, max_length=128)
    user_id: str | None = Field(default=None, max_length=128)
    message: str = Field(..., min_length=1, max_length=4000)
    idempotency_key: str | None = Field(default=None, max_length=128)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    session_id: str
    response: str
    strategy: str
    safety_routed: bool = False
    fallback_used: bool = False


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
