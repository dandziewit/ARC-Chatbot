from __future__ import annotations

import ast
import datetime
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ToolResult:
    used: bool
    response: str


def _safe_eval_ast(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _safe_eval_ast(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _safe_eval_ast(node.operand)
        return value if isinstance(node.op, ast.UAdd) else -value
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow)):
        left = _safe_eval_ast(node.left)
        right = _safe_eval_ast(node.right)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        if isinstance(node.op, ast.Mod):
            return left % right
        return left**right
    raise ValueError("Unsupported expression")


def safe_eval_expression(expr: str) -> float:
    candidate = expr.strip()
    if len(candidate) > 80:
        raise ValueError("Expression too long")
    if not re.fullmatch(r"[\d\s\+\-\*\/\(\)\.\%]+", candidate):
        raise ValueError("Expression contains unsupported characters")
    tree = ast.parse(candidate, mode="eval")
    return _safe_eval_ast(tree)


def route_tool_call(message: str) -> ToolResult:
    text = message.lower().strip()
    if any(token in text for token in ["what time", "current time", "what day", "date today"]):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return ToolResult(used=True, response=f"Current local time is {now}.")

    expr_match = re.search(r"(?:calculate|solve)\s+([\d\s\+\-\*\/\(\)\.\%]+)", text)
    if expr_match:
        try:
            result = safe_eval_expression(expr_match.group(1))
            return ToolResult(used=True, response=f"Result: {result}")
        except Exception:  # noqa: BLE001
            return ToolResult(used=True, response="I can only calculate basic arithmetic with numbers and operators.")

    return ToolResult(used=False, response="")
