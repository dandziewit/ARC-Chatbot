from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass


@dataclass
class MemoryEvent:
    session_id: str
    user_id: str | None
    user_message: str
    assistant_message: str
    strategy: str
    safety_routed: bool
    created_at: float


class MemoryStore:
    def append_event(self, event: MemoryEvent) -> None:
        raise NotImplementedError


class SqliteMemoryStore(MemoryStore):
    """Durable local store; can be swapped with Postgres in production."""

    def __init__(self, db_path: str = "arc_memory.db") -> None:
        self._db_path = db_path
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    user_id TEXT,
                    user_message TEXT NOT NULL,
                    assistant_message TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    safety_routed INTEGER NOT NULL,
                    created_at REAL NOT NULL
                )
                """
            )
            conn.commit()

    def append_event(self, event: MemoryEvent) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO conversation_events (
                    session_id, user_id, user_message, assistant_message,
                    strategy, safety_routed, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.session_id,
                    event.user_id,
                    event.user_message,
                    event.assistant_message,
                    event.strategy,
                    1 if event.safety_routed else 0,
                    event.created_at,
                ),
            )
            conn.commit()


class PostgresMemoryStore(MemoryStore):
    """Production memory/event store backed by Postgres."""

    def __init__(self, dsn: str) -> None:
        try:
            import psycopg  # type: ignore
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError("psycopg package is required for PostgresMemoryStore") from exc

        self._psycopg = psycopg
        self._dsn = dsn
        self._ensure_schema()

    def _connect(self):
        return self._psycopg.connect(self._dsn)

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS conversation_events (
                        id BIGSERIAL PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        user_id TEXT,
                        user_message TEXT NOT NULL,
                        assistant_message TEXT NOT NULL,
                        strategy TEXT NOT NULL,
                        safety_routed BOOLEAN NOT NULL,
                        created_at DOUBLE PRECISION NOT NULL
                    )
                    """
                )
            conn.commit()

    def append_event(self, event: MemoryEvent) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO conversation_events (
                        session_id, user_id, user_message, assistant_message,
                        strategy, safety_routed, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        event.session_id,
                        event.user_id,
                        event.user_message,
                        event.assistant_message,
                        event.strategy,
                        event.safety_routed,
                        event.created_at,
                    ),
                )
            conn.commit()


def build_event(
    session_id: str,
    user_id: str | None,
    user_message: str,
    assistant_message: str,
    strategy: str,
    safety_routed: bool,
) -> MemoryEvent:
    return MemoryEvent(
        session_id=session_id,
        user_id=user_id,
        user_message=user_message,
        assistant_message=assistant_message,
        strategy=strategy,
        safety_routed=safety_routed,
        created_at=time.time(),
    )
