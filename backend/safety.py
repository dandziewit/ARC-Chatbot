from __future__ import annotations

import re

CRISIS_PATTERNS = [
    r"\b(kill myself|suicide|end my life|want to die|self harm|hurt myself)\b",
    r"\b(hurt someone|kill them|violent thoughts|attack someone)\b",
]


def is_crisis_message(message: str) -> bool:
    text = message.lower().strip()
    return any(re.search(pattern, text) for pattern in CRISIS_PATTERNS)


def crisis_response() -> str:
    return (
        "I am glad you reached out. I cannot provide crisis counseling, but you deserve immediate support. "
        "If you may act on these thoughts, call emergency services now. "
        "You can also call or text 988 (US/Canada) or your local crisis hotline right now."
    )
