from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.memory_store import PostgresMemoryStore, SqliteMemoryStore
from backend.models import ChatRequest, ChatResponse, HealthResponse
from backend.observability import configure_logging, log_event
from backend.orchestrator import ChatOrchestrator
from backend.rate_limit import InMemoryRateLimiter
from backend.session_store import InMemorySessionStore, RedisSessionStore

# Import core engine for simpler deployments
try:
    from arc_core import ChatbotEngine, ChatState
    CORE_ENGINE_AVAILABLE = True
except ImportError:
    ChatbotEngine = None
    ChatState = None
    CORE_ENGINE_AVAILABLE = False

configure_logging()
logger = logging.getLogger("arc-backend")

app = FastAPI(title="ARC Backend", version="1.0.0")

# Enable CORS for browser requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict to your domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rate_limiter = InMemoryRateLimiter(settings.rate_limit_per_minute)


def _build_session_store():
    if settings.use_redis_sessions:
        try:
            logger.info("Using RedisSessionStore")
            return RedisSessionStore(
                settings.redis_url,
                key_prefix=settings.redis_session_key_prefix,
                ttl_seconds=settings.redis_session_ttl_seconds,
            )
        except Exception as exc:  # noqa: BLE001
            log_event(
                "storage.fallback",
                component="session_store",
                from_backend="redis",
                to_backend="in_memory",
                reason=str(exc),
                environment=settings.environment,
            )
            logger.warning("Redis session store unavailable, falling back to in-memory: %s", exc)
    return InMemorySessionStore()


def _build_memory_store():
    if settings.use_postgres_memory:
        try:
            logger.info("Using PostgresMemoryStore")
            return PostgresMemoryStore(settings.postgres_dsn)
        except Exception as exc:  # noqa: BLE001
            log_event(
                "storage.fallback",
                component="memory_store",
                from_backend="postgres",
                to_backend="sqlite",
                reason=str(exc),
                environment=settings.environment,
            )
            logger.warning("Postgres memory store unavailable, falling back to sqlite: %s", exc)
    return SqliteMemoryStore()


session_store = _build_session_store()
memory_store = _build_memory_store()
orchestrator = ChatOrchestrator(session_store=session_store, memory_store=memory_store)


@app.middleware("http")
async def request_metrics(request: Request, call_next):
    request_id = uuid.uuid4().hex
    request.state.request_id = request_id
    start = time.perf_counter()
    response = None

    try:
        response = await call_next(request)
        return response
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        status_code = response.status_code if response is not None else 500
        if response is not None:
            response.headers["X-Request-ID"] = request_id
        log_event(
            "http.request.completed",
            request_id=request_id,
            endpoint=request.url.path,
            method=request.method,
            status_code=status_code,
            duration_ms=round(duration_ms, 2),
            environment=settings.environment,
            deployment_version=app.version,
            session_id=getattr(request.state, "session_id", None),
            user_id=getattr(request.state, "user_id", None),
            rate_limited=status_code == 429,
        )


@app.get("/healthz", response_model=HealthResponse)
def healthz() -> HealthResponse:
    return HealthResponse(status="ok", service=settings.app_name, version="1.0.0")


@app.get("/readyz", response_model=HealthResponse)
def readyz() -> HealthResponse:
    return HealthResponse(status="ready", service=settings.app_name, version="1.0.0")


@app.post("/v1/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    request: Request,
    response: Response,
    x_forwarded_for: str | None = Header(default=None),
) -> ChatResponse:
    request.state.session_id = payload.session_id
    request.state.user_id = payload.user_id
    caller = x_forwarded_for or request.client.host if request.client else "unknown"
    rl_key = f"{payload.user_id or 'anon'}:{caller}"
    request_id = getattr(request.state, "request_id", None)

    if not rate_limiter.allow(rl_key):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    output = orchestrator.generate(
        session_id=payload.session_id,
        user_id=payload.user_id,
        message=payload.message,
        request_id=request_id,
    )
    if request_id is not None:
        response.headers["X-Request-ID"] = request_id

    return ChatResponse(
        session_id=payload.session_id,
        response=output.response,
        strategy=output.strategy,
        safety_routed=output.safety_routed,
        fallback_used=output.fallback_used,
    )


@app.post("/v1/chat/simple")
def chat_simple(payload: ChatRequest, request: Request, response: Response):
    """
    Simple chat endpoint using core engine.
    
    For browser deployment without Redis/Postgres dependencies.
    State is maintained per session in memory.
    
    Use this for: quick demos, website chatbots, testing
    Use /v1/chat for: production scale, distributed state
    """
    if not CORE_ENGINE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Core engine not available")

    from arc_core import ChatState as CoreChatState
    from arc_core import ChatbotEngine as CoreChatbotEngine
    
    request.state.session_id = payload.session_id
    request.state.user_id = payload.user_id
    
    # Simple in-memory state (cleared on restart)
    core_sessions = getattr(app.state, "core_sessions", None)
    if core_sessions is None:
        core_sessions = {}
        setattr(app.state, "core_sessions", core_sessions)

    session_id = payload.session_id
    if session_id not in core_sessions:
        core_sessions[session_id] = {
            "engine": CoreChatbotEngine(),
            "state": CoreChatState(session_id=session_id)
        }
    
    session_data = core_sessions[session_id]
    bot_response, state = session_data["engine"].chat(payload.message, session_data["state"])
    session_data["state"] = state  # Update stored state
    
    return {
        "session_id": session_id,
        "response": bot_response,
        "strategy": "native",
        "safety_routed": False,
        "fallback_used": False,
    }


@app.get("/")
def root():
    """Redirect root to static index"""
    static_dir = Path(__file__).parent.parent / "static"
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    raise HTTPException(status_code=404, detail="index.html not found")


# Mount static files for browser UI
try:
    static_dir = Path(__file__).parent.parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
        logger.info(f"Static files mounted from {static_dir}")
except Exception as exc:
    logger.warning(f"Could not mount static files: {exc}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level="info",
    )
