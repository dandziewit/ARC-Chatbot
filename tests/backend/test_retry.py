import pytest

import backend.main as backend_main
from backend.orchestrator import OrchestratorOutput
from backend.retry import RetryExceeded, retry_with_backoff


def test_retry_eventually_succeeds(monkeypatch) -> None:
    monkeypatch.setattr("backend.retry.time.sleep", lambda _seconds: None)

    attempts = {"count": 0}

    def flaky() -> str:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError("transient")
        return "ok"

    assert retry_with_backoff(flaky, max_retries=3) == "ok"
    assert attempts["count"] == 3


def test_retry_raises_after_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("backend.retry.time.sleep", lambda _seconds: None)

    def always_fail() -> str:
        raise RuntimeError("still broken")

    with pytest.raises(RetryExceeded):
        retry_with_backoff(always_fail, max_retries=2)


def test_orchestrator_retries_transient_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    backend_main.rate_limiter._requests.clear()
    if hasattr(backend_main.session_store, "_sessions"):
        backend_main.session_store._sessions.clear()
    monkeypatch.setattr(backend_main.memory_store, "append_event", lambda _event: None)
    monkeypatch.setattr("backend.retry.time.sleep", lambda _seconds: None)

    original = backend_main.orchestrator._respond
    attempts = {"count": 0}

    def flaky(message: str, state):  # noqa: ANN001
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError("transient")
        return original(message, state)

    monkeypatch.setattr(backend_main.orchestrator, "_respond", flaky)

    output = backend_main.orchestrator.generate(session_id="retry-session", user_id="user", message="hello")

    assert attempts["count"] == 3
    assert output == OrchestratorOutput(
        response="Go on, I am listening.",
        strategy="ask_followup",
        safety_routed=False,
        fallback_used=False,
    )


def test_orchestrator_falls_back_after_retry_exhaustion(monkeypatch: pytest.MonkeyPatch) -> None:
    backend_main.rate_limiter._requests.clear()
    if hasattr(backend_main.session_store, "_sessions"):
        backend_main.session_store._sessions.clear()
    monkeypatch.setattr(backend_main.memory_store, "append_event", lambda _event: None)
    monkeypatch.setattr("backend.retry.time.sleep", lambda _seconds: None)
    monkeypatch.setattr(
        backend_main.orchestrator,
        "_respond",
        lambda _message, _state: (_ for _ in ()).throw(RuntimeError("persistent")),
    )

    output = backend_main.orchestrator.generate(session_id="fallback-session", user_id="user", message="hello")

    assert output == OrchestratorOutput(
        response="How can I help you today?",
        strategy="fallback",
        safety_routed=False,
        fallback_used=True,
    )


def test_orchestrator_raises_when_memory_write_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    if hasattr(backend_main.session_store, "_sessions"):
        backend_main.session_store._sessions.clear()
    monkeypatch.setattr(backend_main.memory_store, "append_event", lambda _event: (_ for _ in ()).throw(RuntimeError("db down")))

    with pytest.raises(RuntimeError, match="db down"):
        backend_main.orchestrator.generate(session_id="memory-failure", user_id="user", message="hello")


def test_orchestrator_raises_when_session_save_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    if hasattr(backend_main.session_store, "_sessions"):
        backend_main.session_store._sessions.clear()
    monkeypatch.setattr(backend_main.memory_store, "append_event", lambda _event: None)
    monkeypatch.setattr(backend_main.session_store, "save", lambda _state: (_ for _ in ()).throw(RuntimeError("save failed")))

    with pytest.raises(RuntimeError, match="save failed"):
        backend_main.orchestrator.generate(session_id="save-failure", user_id="user", message="hello")
