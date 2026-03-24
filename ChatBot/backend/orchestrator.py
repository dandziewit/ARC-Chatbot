from __future__ import annotations

from dataclasses import dataclass

from backend.memory_store import MemoryStore, build_event
from backend.observability import estimate_tokens, log_event, traced_span
from backend.retry import RetryExceeded, retry_with_backoff
from backend.safety import crisis_response, is_crisis_message
from backend.session_store import SessionState, SessionStore
from backend.tool_router import route_tool_call


@dataclass(frozen=True)
class OrchestratorOutput:
    response: str
    strategy: str
    safety_routed: bool
    fallback_used: bool


class ChatOrchestrator:
    def __init__(self, session_store: SessionStore, memory_store: MemoryStore) -> None:
        self.session_store = session_store
        self.memory_store = memory_store

    def _infer_intent(self, message: str) -> str:
        text = message.lower().strip()
        if not text:
            return "uncertainty"
        if "?" in text:
            return "question"
        if any(t in text for t in ["sad", "stressed", "anxious", "happy", "excited"]):
            return "emotional_expression"
        if any(t in text for t in ["calculate", "solve", "what time", "date"]):
            return "factual_request"
        if len(text.split()) <= 3:
            return "casual_statement"
        return "general_chat"

    def _select_strategy(self, intent: str) -> str:
        mapping = {
            "question": "direct_answer",
            "factual_request": "direct_answer",
            "emotional_expression": "reflect",
            "uncertainty": "clarify_context",
            "casual_statement": "ask_followup",
            "general_chat": "ask_followup",
        }
        return mapping.get(intent, "clarify_context")

    def _fallback_response(self, state: SessionState) -> str:
        variants = [
            "How can I help you today?",
            "Tell me a little more so I can help better.",
            "What would you like to work on next?",
        ]
        for candidate in variants:
            if candidate not in state.last_responses[-2:]:
                return candidate
        return variants[0]

    def _respond(self, message: str, state: SessionState) -> OrchestratorOutput:
        if is_crisis_message(message):
            return OrchestratorOutput(
                response=crisis_response(),
                strategy="safety",
                safety_routed=True,
                fallback_used=False,
            )

        tool = route_tool_call(message)
        if tool.used:
            return OrchestratorOutput(
                response=tool.response,
                strategy="tool_call",
                safety_routed=False,
                fallback_used=False,
            )

        intent = self._infer_intent(message)
        strategy = self._select_strategy(intent)

        if strategy == "reflect":
            response = "I hear you. Want to share a bit more so I can support you better?"
        elif strategy == "clarify_context":
            response = "Could you clarify what you mean?"
        elif strategy == "direct_answer":
            response = "I can help with that. Could you share one more detail about what you need?"
        else:
            response = "Go on, I am listening."

        if response in state.last_responses[-2:]:
            response = self._fallback_response(state)
            return OrchestratorOutput(
                response=response,
                strategy=strategy,
                safety_routed=False,
                fallback_used=True,
            )

        return OrchestratorOutput(
            response=response,
            strategy=strategy,
            safety_routed=False,
            fallback_used=False,
        )

    def generate(
        self,
        *,
        session_id: str,
        user_id: str | None,
        message: str,
        request_id: str | None = None,
    ) -> OrchestratorOutput:
        with traced_span("chat.generate", session_id=session_id):
            state = self.session_store.get(session_id)
            retry_count = 0
            retry_exhausted = False

            def _on_retry(attempt_number: int, _exc: Exception, _sleep_for: float) -> None:
                nonlocal retry_count
                retry_count = attempt_number

            try:
                output = retry_with_backoff(
                    lambda: self._respond(message, state),
                    max_retries=2,
                    on_retry=_on_retry,
                )
            except RetryExceeded:
                retry_exhausted = True
                output = OrchestratorOutput(
                    response=self._fallback_response(state),
                    strategy="fallback",
                    safety_routed=False,
                    fallback_used=True,
                )

            state.recent_turns.append({"user": message, "assistant": output.response})
            state.recent_turns = state.recent_turns[-8:]
            state.last_responses.append(output.response)
            state.last_responses = state.last_responses[-6:]
            self.session_store.save(state)
            contained_proxy = len(state.recent_turns) <= 3 and not output.fallback_used and not output.safety_routed
            estimated_tokens = estimate_tokens(message, output.response)

            self.memory_store.append_event(
                build_event(
                    session_id=session_id,
                    user_id=user_id,
                    user_message=message,
                    assistant_message=output.response,
                    strategy=output.strategy,
                    safety_routed=output.safety_routed,
                )
            )

            log_event(
                "retry.summary",
                request_id=request_id,
                session_id=session_id,
                retry_count=retry_count,
                retry_exhausted=retry_exhausted,
                final_outcome=output.strategy,
            )
            log_event(
                "chat.response",
                request_id=request_id,
                session_id=session_id,
                user_id=user_id,
                strategy=output.strategy,
                safety_routed=output.safety_routed,
                fallback_used=output.fallback_used,
                input_chars=len(message),
                output_chars=len(output.response),
                retry_count=retry_count,
                contained_proxy=contained_proxy,
                estimated_tokens=estimated_tokens,
                estimated_cost_usd=0.0,
            )
            return output
