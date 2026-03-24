import json

from fastapi.testclient import TestClient

import backend.main as backend_main
import backend.orchestrator as backend_orchestrator
from scripts.aggregate_chatbot_kpis import aggregate_events, parse_event_line


def test_chat_emits_request_and_response_telemetry(monkeypatch) -> None:
    events: list[tuple[str, dict]] = []

    def capture(event: str, **fields):  # noqa: ANN001
        events.append((event, fields))

    backend_main.rate_limiter.requests_per_minute = 60
    backend_main.rate_limiter._requests.clear()
    if hasattr(backend_main.session_store, "_sessions"):
        backend_main.session_store._sessions.clear()
    monkeypatch.setattr(backend_main.memory_store, "append_event", lambda _event: None)
    monkeypatch.setattr(backend_main, "log_event", capture)
    monkeypatch.setattr(backend_orchestrator, "log_event", capture)

    client = TestClient(backend_main.app)
    response = client.post(
        "/v1/chat",
        json={"session_id": "telemetry-session", "user_id": "telemetry-user", "message": "hello"},
    )

    assert response.status_code == 200
    request_id = response.headers["X-Request-ID"]
    assert request_id

    http_event = next(fields for event, fields in events if event == "http.request.completed")
    assert http_event["request_id"] == request_id
    assert http_event["endpoint"] == "/v1/chat"
    assert http_event["status_code"] == 200
    assert http_event["session_id"] == "telemetry-session"
    assert http_event["user_id"] == "telemetry-user"

    response_event = next(fields for event, fields in events if event == "chat.response")
    assert response_event["request_id"] == request_id
    assert response_event["strategy"] == "ask_followup"
    assert response_event["fallback_used"] is False
    assert response_event["contained_proxy"] is True
    assert response_event["estimated_tokens"] > 0

    retry_event = next(fields for event, fields in events if event == "retry.summary")
    assert retry_event["request_id"] == request_id
    assert retry_event["retry_count"] == 0
    assert retry_event["retry_exhausted"] is False


def test_parse_and_aggregate_kpi_events() -> None:
    lines = [
        "2026-03-23 16:00:00 INFO arc-backend event=http.request.completed fields={'request_id': 'r1', 'endpoint': '/v1/chat', 'method': 'POST', 'status_code': 200, 'duration_ms': 120.0, 'environment': 'dev', 'deployment_version': '1.0.0', 'session_id': 's1', 'user_id': 'u1', 'rate_limited': False}",
        "2026-03-23 16:00:01 INFO arc-backend event=chat.response fields={'request_id': 'r1', 'session_id': 's1', 'user_id': 'u1', 'strategy': 'ask_followup', 'safety_routed': False, 'fallback_used': False, 'input_chars': 5, 'output_chars': 24, 'retry_count': 0, 'contained_proxy': True, 'estimated_tokens': 8, 'estimated_cost_usd': 0.0}",
        "2026-03-23 16:00:01 INFO arc-backend event=retry.summary fields={'request_id': 'r1', 'session_id': 's1', 'retry_count': 0, 'retry_exhausted': False, 'final_outcome': 'ask_followup'}",
        "2026-03-23 16:00:02 INFO arc-backend event=http.request.completed fields={'request_id': 'r2', 'endpoint': '/v1/chat', 'method': 'POST', 'status_code': 429, 'duration_ms': 40.0, 'environment': 'dev', 'deployment_version': '1.0.0', 'session_id': 's2', 'user_id': 'u2', 'rate_limited': True}",
        "2026-03-23 16:00:03 INFO arc-backend event=storage.fallback fields={'component': 'session_store', 'from_backend': 'redis', 'to_backend': 'in_memory', 'reason': 'redis down', 'environment': 'dev'}",
        "2026-03-23 16:00:04 INFO arc-backend event=chat.feedback fields={'request_id': 'r1', 'session_id': 's1', 'user_id': 'u1', 'feedback_type': 'thumbs_up', 'rating_value': None, 'resolution_confirmed': True}"
    ]

    events = [parse_event_line(line) for line in lines]
    parsed_events = [event for event in events if event is not None]
    summary = aggregate_events(parsed_events)

    assert summary["requests_total"] == 2
    assert summary["chat_requests_total"] == 2
    assert summary["fallback_rate"] == 0.0
    assert summary["containment_rate"] == 1.0
    assert summary["rate_limit_rejection_rate"] == 0.5
    assert summary["latency_p50_ms"] == 80.0
    assert summary["latency_p95_ms"] == 120.0
    assert summary["estimated_tokens_total"] == 8
    assert summary["user_satisfaction"] == 1.0
    assert summary["storage_fallback_count"] == 1