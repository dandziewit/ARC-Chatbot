from dataclasses import dataclass

from backend.orchestrator import ChatOrchestrator
from backend.session_store import InMemorySessionStore


@dataclass
class _Event:
    session_id: str
    user_id: str | None
    user_message: str
    assistant_message: str
    strategy: str
    safety_routed: bool


class FakeMemoryStore:
    def __init__(self) -> None:
        self.events: list[_Event] = []

    def append_event(self, event) -> None:  # noqa: ANN001
        self.events.append(
            _Event(
                session_id=event.session_id,
                user_id=event.user_id,
                user_message=event.user_message,
                assistant_message=event.assistant_message,
                strategy=event.strategy,
                safety_routed=event.safety_routed,
            )
        )


def test_safety_route_and_event_written() -> None:
    sessions = InMemorySessionStore()
    memory = FakeMemoryStore()
    orchestrator = ChatOrchestrator(session_store=sessions, memory_store=memory)

    out = orchestrator.generate(session_id="s1", user_id="u1", message="I want to die")

    assert out.safety_routed is True
    assert out.strategy == "safety"
    assert len(memory.events) == 1
    assert memory.events[0].session_id == "s1"


def test_tool_route() -> None:
    sessions = InMemorySessionStore()
    memory = FakeMemoryStore()
    orchestrator = ChatOrchestrator(session_store=sessions, memory_store=memory)

    out = orchestrator.generate(session_id="s2", user_id=None, message="calculate 10 / 2")

    assert out.strategy == "tool_call"
    assert out.response == "Result: 5.0"


def test_dedupe_triggers_fallback() -> None:
    sessions = InMemorySessionStore()
    memory = FakeMemoryStore()
    orchestrator = ChatOrchestrator(session_store=sessions, memory_store=memory)

    first = orchestrator.generate(session_id="s3", user_id=None, message="hello")
    second = orchestrator.generate(session_id="s3", user_id=None, message="hey")

    assert first.response != ""
    assert second.fallback_used is True
