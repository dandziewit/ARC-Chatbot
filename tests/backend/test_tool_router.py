from backend.tool_router import route_tool_call


def test_time_tool_route() -> None:
    result = route_tool_call("what time is it?")
    assert result.used is True
    assert "Current local time is" in result.response


def test_calculator_route() -> None:
    result = route_tool_call("calculate 2 + 2 * 3")
    assert result.used is True
    assert result.response == "Result: 8.0"


def test_invalid_calculator_expression() -> None:
    result = route_tool_call("calculate 2 + abc")
    assert result.used is True
    assert "basic arithmetic" in result.response
