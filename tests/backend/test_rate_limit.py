from backend.rate_limit import InMemoryRateLimiter


def test_rate_limit_blocks_after_budget(monkeypatch) -> None:
    now = {"value": 1000.0}
    monkeypatch.setattr("backend.rate_limit.time.time", lambda: now["value"])

    limiter = InMemoryRateLimiter(requests_per_minute=2)
    assert limiter.allow("k") is True
    assert limiter.allow("k") is True
    assert limiter.allow("k") is False

    now["value"] += 61.0
    assert limiter.allow("k") is True
