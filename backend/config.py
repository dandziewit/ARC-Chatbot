from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("ARC_APP_NAME", "arc-backend")
    environment: str = os.getenv("ARC_ENV", "dev")
    host: str = os.getenv("ARC_HOST", "0.0.0.0")
    port: int = int(os.getenv("ARC_PORT", "8000"))

    # Feature flags for low-risk rollouts
    use_redis_sessions: bool = os.getenv("ARC_USE_REDIS_SESSIONS", "false").lower() == "true"
    use_postgres_memory: bool = os.getenv("ARC_USE_POSTGRES_MEMORY", "false").lower() == "true"
    enable_tool_router: bool = os.getenv("ARC_ENABLE_TOOL_ROUTER", "true").lower() == "true"
    enable_crisis_guardrails: bool = os.getenv("ARC_ENABLE_CRISIS_GUARDRAILS", "true").lower() == "true"

    # Connection strings
    redis_url: str = os.getenv("ARC_REDIS_URL", "redis://localhost:6379/0")
    postgres_dsn: str = os.getenv("ARC_POSTGRES_DSN", "postgresql://arc:arc@localhost:5432/arc")
    redis_session_key_prefix: str = os.getenv("ARC_REDIS_SESSION_KEY_PREFIX", "arc:session:")
    redis_session_ttl_seconds: int = int(os.getenv("ARC_REDIS_SESSION_TTL_SECONDS", "3600"))

    # Reliability controls
    request_timeout_seconds: float = float(os.getenv("ARC_REQUEST_TIMEOUT_SECONDS", "8.0"))
    model_timeout_seconds: float = float(os.getenv("ARC_MODEL_TIMEOUT_SECONDS", "6.0"))
    max_retries: int = int(os.getenv("ARC_MAX_RETRIES", "2"))

    # Rate limiting
    rate_limit_per_minute: int = int(os.getenv("ARC_RATE_LIMIT_PER_MINUTE", "60"))


settings = Settings()
