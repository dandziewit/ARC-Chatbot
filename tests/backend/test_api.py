import pytest
from fastapi.testclient import TestClient

import backend.main as backend_main


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    backend_main.rate_limiter.requests_per_minute = 60
    backend_main.rate_limiter._requests.clear()
    if hasattr(backend_main.session_store, "_sessions"):
        backend_main.session_store._sessions.clear()
    monkeypatch.setattr(backend_main.memory_store, "append_event", lambda _event: None)
    return TestClient(backend_main.app)


def test_healthz(client: TestClient) -> None:
    r = client.get("/healthz")

    assert r.status_code == 200
    assert r.json() == {
        "status": "ok",
        "service": backend_main.settings.app_name,
        "version": "1.0.0",
    }


def test_readyz(client: TestClient) -> None:
    r = client.get("/readyz")

    assert r.status_code == 200
    assert r.json() == {
        "status": "ready",
        "service": backend_main.settings.app_name,
        "version": "1.0.0",
    }


@pytest.mark.parametrize(
    ("payload", "expected_response", "expected_strategy"),
    [
        (
            {"session_id": "casual-session", "user_id": "user-1", "message": "hello"},
            "Go on, I am listening.",
            "ask_followup",
        ),
        (
            {
                "session_id": "question-session",
                "user_id": "user-2",
                "message": "What is the capital of France?",
            },
            "I can help with that. Could you share one more detail about what you need?",
            "direct_answer",
        ),
        (
            {"session_id": "math-session", "user_id": "user-3", "message": "calculate 2 + 2"},
            "Result: 4.0",
            "tool_call",
        ),
        (
            {
                "session_id": "crisis-session",
                "user_id": "user-4",
                "message": "I want to die",
            },
            (
                "I am glad you reached out. I cannot provide crisis counseling, but you deserve immediate support. "
                "If you may act on these thoughts, call emergency services now. "
                "You can also call or text 988 (US/Canada) or your local crisis hotline right now."
            ),
            "safety",
        ),
    ],
)
def test_chat_endpoint_contract(
    client: TestClient,
    payload: dict[str, str],
    expected_response: str,
    expected_strategy: str,
) -> None:
    r = client.post("/v1/chat", json=payload)

    assert r.status_code == 200
    assert r.json() == {
        "session_id": payload["session_id"],
        "response": expected_response,
        "strategy": expected_strategy,
        "safety_routed": expected_strategy == "safety",
        "fallback_used": False,
    }


def test_chat_time_tool_response_shape(client: TestClient) -> None:
    r = client.post(
        "/v1/chat",
        json={"session_id": "time-session", "user_id": "user-time", "message": "what time is it"},
    )

    assert r.status_code == 200
    body = r.json()
    assert body["session_id"] == "time-session"
    assert body["strategy"] == "tool_call"
    assert body["safety_routed"] is False
    assert body["fallback_used"] is False
    assert body["response"].startswith("Current local time is ")
    assert body["response"].endswith(".")


@pytest.mark.parametrize(
    ("payload", "field", "error_type"),
    [
        ({"session_id": "abc", "user_id": "u1"}, "message", "missing"),
        ({"session_id": "ab", "user_id": "u1", "message": "hello"}, "session_id", "string_too_short"),
        ({"session_id": "abc", "user_id": "u1", "message": ""}, "message", "string_too_short"),
        ({"session_id": "abc", "user_id": "u1", "message": "x" * 4001}, "message", "string_too_long"),
        ({"session_id": "abc", "user_id": "u" * 129, "message": "hello"}, "user_id", "string_too_long"),
        (
            {
                "session_id": "abc",
                "user_id": "u1",
                "message": "hello",
                "idempotency_key": "k" * 129,
            },
            "idempotency_key",
            "string_too_long",
        ),
        ({"session_id": "abc", "user_id": "u1", "message": "hello", "metadata": []}, "metadata", "dict_type"),
    ],
)
def test_chat_validation_errors(
    client: TestClient,
    payload: dict[str, object],
    field: str,
    error_type: str,
) -> None:
    r = client.post("/v1/chat", json=payload)

    assert r.status_code == 422
    detail = r.json()["detail"]
    assert detail[0]["loc"][-1] == field
    assert detail[0]["type"] == error_type


def test_chat_ignores_unknown_fields(client: TestClient) -> None:
    r = client.post(
        "/v1/chat",
        json={
            "session_id": "extra-session",
            "user_id": "user-extra",
            "message": "hello",
            "extra_field": "ignored",
        },
    )

    assert r.status_code == 200
    assert r.json() == {
        "session_id": "extra-session",
        "response": "Go on, I am listening.",
        "strategy": "ask_followup",
        "safety_routed": False,
        "fallback_used": False,
    }


def test_chat_uses_fallback_on_repeated_session_prompt(client: TestClient) -> None:
    first = client.post(
        "/v1/chat",
        json={"session_id": "repeat-session", "user_id": "repeat-user", "message": "hello"},
    )
    second = client.post(
        "/v1/chat",
        json={"session_id": "repeat-session", "user_id": "repeat-user", "message": "hello"},
    )

    assert first.status_code == 200
    assert first.json()["fallback_used"] is False
    assert first.json()["response"] == "Go on, I am listening."

    assert second.status_code == 200
    assert second.json() == {
        "session_id": "repeat-session",
        "response": "How can I help you today?",
        "strategy": "ask_followup",
        "safety_routed": False,
        "fallback_used": True,
    }


def test_chat_rate_limit_returns_429(client: TestClient) -> None:
    backend_main.rate_limiter.requests_per_minute = 1

    first = client.post(
        "/v1/chat",
        json={"session_id": "rate-1", "user_id": "rate-user", "message": "hello"},
    )
    second = client.post(
        "/v1/chat",
        json={"session_id": "rate-2", "user_id": "rate-user", "message": "hello"},
    )

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json() == {"detail": "Rate limit exceeded"}


def test_chat_rate_limit_uses_forwarded_for_bucket(client: TestClient) -> None:
    backend_main.rate_limiter.requests_per_minute = 1

    first = client.post(
        "/v1/chat",
        json={"session_id": "xff-1", "user_id": "xff-user", "message": "hello"},
        headers={"X-Forwarded-For": "203.0.113.10"},
    )
    second = client.post(
        "/v1/chat",
        json={"session_id": "xff-2", "user_id": "xff-user", "message": "hello"},
        headers={"X-Forwarded-For": "198.51.100.12"},
    )

    assert first.status_code == 200
    assert second.status_code == 200
