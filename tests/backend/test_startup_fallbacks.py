from dataclasses import replace

import backend.main as backend_main
from backend.memory_store import SqliteMemoryStore
from backend.session_store import InMemorySessionStore


def test_build_session_store_falls_back_to_in_memory(monkeypatch) -> None:
    events: list[tuple[str, dict]] = []

    def capture(event: str, **fields):  # noqa: ANN001
        events.append((event, fields))

    monkeypatch.setattr(
        backend_main,
        "settings",
        replace(backend_main.settings, use_redis_sessions=True),
    )
    monkeypatch.setattr(backend_main, "log_event", capture)

    def fail(*_args, **_kwargs):  # noqa: ANN002, ANN003
        raise RuntimeError("redis unavailable")

    monkeypatch.setattr(backend_main, "RedisSessionStore", fail)

    store = backend_main._build_session_store()

    assert isinstance(store, InMemorySessionStore)
    assert ("storage.fallback", {
        "component": "session_store",
        "from_backend": "redis",
        "to_backend": "in_memory",
        "reason": "redis unavailable",
        "environment": backend_main.settings.environment,
    }) in events


def test_build_memory_store_falls_back_to_sqlite(monkeypatch) -> None:
    events: list[tuple[str, dict]] = []

    def capture(event: str, **fields):  # noqa: ANN001
        events.append((event, fields))

    monkeypatch.setattr(
        backend_main,
        "settings",
        replace(backend_main.settings, use_postgres_memory=True),
    )
    monkeypatch.setattr(backend_main, "log_event", capture)

    def fail(*_args, **_kwargs):  # noqa: ANN002, ANN003
        raise RuntimeError("postgres unavailable")

    monkeypatch.setattr(backend_main, "PostgresMemoryStore", fail)

    store = backend_main._build_memory_store()

    assert isinstance(store, SqliteMemoryStore)
    assert ("storage.fallback", {
        "component": "memory_store",
        "from_backend": "postgres",
        "to_backend": "sqlite",
        "reason": "postgres unavailable",
        "environment": backend_main.settings.environment,
    }) in events