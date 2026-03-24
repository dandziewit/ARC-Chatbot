from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fastapi.testclient import TestClient

import backend.main as backend_main


@dataclass
class EvaluationResult:
    case_id: str
    passed: bool
    score: int
    message: str


def _load_cases(file_path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for line in file_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        cases.append(json.loads(line))
    return cases


def _reset_state() -> None:
    backend_main.rate_limiter.requests_per_minute = 60
    backend_main.rate_limiter._requests.clear()
    if hasattr(backend_main.session_store, "_sessions"):
        backend_main.session_store._sessions.clear()
    backend_main.memory_store.append_event = lambda _event: None


def _assert_subset(actual: Any, expected: Any, path: str = "$") -> None:
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            raise AssertionError(f"{path}: expected object, got {type(actual).__name__}")
        for key, value in expected.items():
            if key not in actual:
                raise AssertionError(f"{path}.{key}: missing key")
            _assert_subset(actual[key], value, f"{path}.{key}")
        return

    if isinstance(expected, list):
        if not isinstance(actual, list):
            raise AssertionError(f"{path}: expected list, got {type(actual).__name__}")
        if len(actual) < len(expected):
            raise AssertionError(f"{path}: expected at least {len(expected)} items, got {len(actual)}")
        for index, value in enumerate(expected):
            _assert_subset(actual[index], value, f"{path}[{index}]")
        return

    if actual != expected:
        raise AssertionError(f"{path}: expected {expected!r}, got {actual!r}")


def _apply_preconditions(case: dict[str, Any]) -> None:
    if case.get("clear_sessions"):
        if hasattr(backend_main.session_store, "_sessions"):
            backend_main.session_store._sessions.clear()
    if case.get("clear_rate_limits"):
        backend_main.rate_limiter._requests.clear()

    preconditions = case.get("preconditions", {})
    if "rate_limit_per_minute" in preconditions:
        backend_main.rate_limiter.requests_per_minute = int(preconditions["rate_limit_per_minute"])


def _run_case(client: TestClient, case: dict[str, Any]) -> EvaluationResult:
    try:
        _apply_preconditions(case)
        request_kwargs: dict[str, Any] = {}
        if "payload" in case:
            request_kwargs["json"] = case["payload"]
        if "headers" in case:
            request_kwargs["headers"] = case["headers"]
        if "raw_body" in case:
            request_kwargs["content"] = case["raw_body"]

        response = client.request(case["method"], case["path"], **request_kwargs)

        if response.status_code != case["expected_status"]:
            raise AssertionError(
                f"status: expected {case['expected_status']}, got {response.status_code}; body={response.text}"
            )

        body: Any = None
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            body = response.json()

        if "expected_json" in case:
            if body != case["expected_json"]:
                raise AssertionError(f"json: expected {case['expected_json']!r}, got {body!r}")

        if "expected_json_subset" in case:
            _assert_subset(body, case["expected_json_subset"])

        if "expected_response_prefix" in case:
            actual = body.get("response", "")
            if not actual.startswith(case["expected_response_prefix"]):
                raise AssertionError(
                    f"response prefix: expected {case['expected_response_prefix']!r}, got {actual!r}"
                )

        if "expected_response_suffix" in case:
            actual = body.get("response", "")
            if not actual.endswith(case["expected_response_suffix"]):
                raise AssertionError(
                    f"response suffix: expected {case['expected_response_suffix']!r}, got {actual!r}"
                )

        if "expected_response_regex" in case:
            actual = body.get("response", "")
            if not re.search(case["expected_response_regex"], actual):
                raise AssertionError(
                    f"response regex: expected {case['expected_response_regex']!r}, got {actual!r}"
                )

        return EvaluationResult(case_id=case["id"], passed=True, score=5, message="pass")
    except Exception as exc:  # noqa: BLE001
        return EvaluationResult(case_id=case["id"], passed=False, score=0, message=str(exc))


def _summarize(results: list[EvaluationResult]) -> tuple[int, int, float]:
    total = len(results)
    passed = sum(1 for result in results if result.passed)
    average = sum(result.score for result in results) / total if total else 0.0
    return total, passed, average


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic ARC model QA cases.")
    parser.add_argument(
        "--set",
        dest="set_path",
        default="qa_sets/v1/deterministic.jsonl",
        help="Path to the JSONL eval set to run.",
    )
    args = parser.parse_args()

    set_path = Path(args.set_path)
    cases = _load_cases(set_path)

    _reset_state()
    client = TestClient(backend_main.app)
    results = [_run_case(client, case) for case in cases]

    total, passed, average = _summarize(results)
    hard_gate_failures = [
        result.case_id
        for result, case in zip(results, cases, strict=True)
        if case.get("hard_gate") and not result.passed
    ]

    print(f"ARC deterministic QA set: {set_path}")
    print(f"Cases: {passed}/{total} passed")
    print(f"Average score: {average:.2f}/5.00")
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"- {status} {result.case_id}: {result.message}")

    if hard_gate_failures:
        print(f"Hard gate failures: {', '.join(hard_gate_failures)}")
        return 1

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())