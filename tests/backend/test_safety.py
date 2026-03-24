from backend.safety import crisis_response, is_crisis_message


def test_detects_crisis_message() -> None:
    assert is_crisis_message("I want to end my life")


def test_non_crisis_message() -> None:
    assert not is_crisis_message("Can you help me with homework?")


def test_crisis_response_contains_hotline() -> None:
    assert "988" in crisis_response()
