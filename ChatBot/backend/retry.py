from __future__ import annotations

import random
import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


class RetryExceeded(Exception):
    pass


def retry_with_backoff(
    fn: Callable[[], T],
    *,
    max_retries: int = 2,
    base_delay_seconds: float = 0.15,
    max_delay_seconds: float = 1.5,
    on_retry: Callable[[int, Exception, float], None] | None = None,
) -> T:
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt == max_retries:
                break
            jitter = random.uniform(0, base_delay_seconds)
            sleep_for = min(max_delay_seconds, (2**attempt) * base_delay_seconds + jitter)
            if on_retry is not None:
                on_retry(attempt + 1, exc, sleep_for)
            time.sleep(sleep_for)
    raise RetryExceeded(str(last_error)) from last_error
