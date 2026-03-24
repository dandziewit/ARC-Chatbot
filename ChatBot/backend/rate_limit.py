from __future__ import annotations

import time
from collections import defaultdict, deque


class InMemoryRateLimiter:
    """Simple per-key sliding window limiter for local and single-instance use."""

    def __init__(self, requests_per_minute: int = 60) -> None:
        self.requests_per_minute = requests_per_minute
        self._requests: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.time()
        window_start = now - 60.0
        q = self._requests[key]
        while q and q[0] < window_start:
            q.popleft()
        if len(q) >= self.requests_per_minute:
            return False
        q.append(now)
        return True
