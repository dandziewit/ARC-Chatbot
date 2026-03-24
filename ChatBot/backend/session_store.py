from __future__ import annotations

import json
import time
from dataclasses import dataclass, field


@dataclass
class SessionState:
    session_id: str
    current_topic: str | None = None
    last_intent: str | None = None
    recent_turns: list[dict[str, str]] = field(default_factory=list)
    last_responses: list[str] = field(default_factory=list)
    version: int = 0
    updated_at: float = field(default_factory=time.time)


class SessionStore:
    def get(self, session_id: str) -> SessionState:
        raise NotImplementedError

    def save(self, state: SessionState) -> None:
        raise NotImplementedError


class InMemorySessionStore(SessionStore):
    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}

    def get(self, session_id: str) -> SessionState:
        return self._sessions.get(session_id, SessionState(session_id=session_id))

    def save(self, state: SessionState) -> None:
        state.version += 1
        state.updated_at = time.time()
        self._sessions[state.session_id] = state


class RedisSessionStore(SessionStore):
    """Distributed session store with TTL for multi-instance deployments."""

    def __init__(
        self,
        redis_url: str,
        *,
        key_prefix: str = "arc:session:",
        ttl_seconds: int = 3600,
    ) -> None:
        try:
            import redis  # type: ignore
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError("redis package is required for RedisSessionStore") from exc

        self._key_prefix = key_prefix
        self._ttl_seconds = ttl_seconds
        self._client = redis.Redis.from_url(redis_url, decode_responses=True)

    def _key(self, session_id: str) -> str:
        return f"{self._key_prefix}{session_id}"

    def _serialize(self, state: SessionState) -> str:
        payload = {
            "session_id": state.session_id,
            "current_topic": state.current_topic,
            "last_intent": state.last_intent,
            "recent_turns": state.recent_turns,
            "last_responses": state.last_responses,
            "version": state.version,
            "updated_at": state.updated_at,
        }
        return json.dumps(payload, separators=(",", ":"))

    def _deserialize(self, payload: str) -> SessionState:
        data = json.loads(payload)
        return SessionState(
            session_id=data["session_id"],
            current_topic=data.get("current_topic"),
            last_intent=data.get("last_intent"),
            recent_turns=list(data.get("recent_turns", [])),
            last_responses=list(data.get("last_responses", [])),
            version=int(data.get("version", 0)),
            updated_at=float(data.get("updated_at", time.time())),
        )

    def get(self, session_id: str) -> SessionState:
        payload = self._client.get(self._key(session_id))
        if not payload:
            return SessionState(session_id=session_id)
        return self._deserialize(payload)

    def save(self, state: SessionState) -> None:
        state.version += 1
        state.updated_at = time.time()
        self._client.set(self._key(state.session_id), self._serialize(state), ex=self._ttl_seconds)
