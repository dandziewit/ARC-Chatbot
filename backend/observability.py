from __future__ import annotations

import logging
import time
from contextlib import contextmanager


logger = logging.getLogger("arc-backend")


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


@contextmanager
def traced_span(span_name: str, **fields: object):
    start = time.perf_counter()
    logger.info("span.start %s %s", span_name, fields)
    try:
        yield
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info("span.end %s duration_ms=%.2f", span_name, duration_ms)


def log_event(event: str, **fields: object) -> None:
    logger.info("event=%s fields=%s", event, fields)


def estimate_tokens(*texts: str) -> int:
    total_chars = sum(len(text or "") for text in texts)
    return max(0, (total_chars + 3) // 4)
