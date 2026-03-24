from __future__ import annotations

import argparse
import ast
import json
import math
import re
from pathlib import Path
from statistics import median
from typing import Any

EVENT_PATTERN = re.compile(r"event=(?P<event>[\w\.\-]+) fields=(?P<fields>\{.*\})")


def parse_event_line(line: str) -> tuple[str, dict[str, Any]] | None:
    match = EVENT_PATTERN.search(line)
    if not match:
        return None
    fields = ast.literal_eval(match.group("fields"))
    if not isinstance(fields, dict):
        raise ValueError("Parsed event fields are not a dictionary")
    return match.group("event"), fields


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = math.ceil((pct / 100.0) * len(ordered)) - 1
    index = max(0, min(index, len(ordered) - 1))
    return ordered[index]


def aggregate_events(events: list[tuple[str, dict[str, Any]]]) -> dict[str, Any]:
    http_events = [fields for event, fields in events if event == "http.request.completed"]
    chat_events = [fields for event, fields in events if event == "chat.response"]
    feedback_events = [fields for event, fields in events if event == "chat.feedback"]
    retry_events = [fields for event, fields in events if event == "retry.summary"]
    storage_fallback_events = [fields for event, fields in events if event == "storage.fallback"]

    latencies = [float(fields["duration_ms"]) for fields in http_events if fields.get("duration_ms") is not None]
    positive_feedback = sum(1 for fields in feedback_events if fields.get("feedback_type") == "thumbs_up")
    negative_feedback = sum(1 for fields in feedback_events if fields.get("feedback_type") == "thumbs_down")
    rated_feedback = positive_feedback + negative_feedback
    contained_total = sum(1 for fields in chat_events if fields.get("contained_proxy") is True)
    fallback_total = sum(1 for fields in chat_events if fields.get("fallback_used") is True or fields.get("strategy") == "fallback")
    safety_total = sum(1 for fields in chat_events if fields.get("safety_routed") is True)
    retry_exhausted_total = sum(1 for fields in retry_events if fields.get("retry_exhausted") is True)
    estimated_tokens_total = sum(int(fields.get("estimated_tokens", 0)) for fields in chat_events)
    estimated_cost_total = sum(float(fields.get("estimated_cost_usd", 0.0)) for fields in chat_events)
    quality_scores = [float(fields["response_quality_sampled_score"]) for fields in chat_events if fields.get("response_quality_sampled_score") is not None]

    requests_total = len(http_events)
    chat_requests_total = sum(1 for fields in http_events if fields.get("endpoint") == "/v1/chat")
    requests_2xx = sum(1 for fields in http_events if 200 <= int(fields.get("status_code", 0)) < 300)
    requests_4xx = sum(1 for fields in http_events if 400 <= int(fields.get("status_code", 0)) < 500)
    requests_5xx = sum(1 for fields in http_events if 500 <= int(fields.get("status_code", 0)) < 600)
    rate_limited_total = sum(1 for fields in http_events if fields.get("rate_limited") is True)

    summary = {
        "requests_total": requests_total,
        "chat_requests_total": chat_requests_total,
        "requests_2xx": requests_2xx,
        "requests_4xx": requests_4xx,
        "requests_5xx": requests_5xx,
        "request_success_rate": round(requests_2xx / requests_total, 4) if requests_total else None,
        "rate_limit_rejection_rate": round(rate_limited_total / chat_requests_total, 4) if chat_requests_total else None,
        "fallback_rate": round(fallback_total / len(chat_events), 4) if chat_events else None,
        "containment_rate": round(contained_total / len(chat_events), 4) if chat_events else None,
        "safety_route_rate": round(safety_total / len(chat_events), 4) if chat_events else None,
        "retry_exhaustion_rate": round(retry_exhausted_total / len(retry_events), 4) if retry_events else None,
        "latency_p50_ms": round(median(latencies), 2) if latencies else None,
        "latency_p95_ms": round(percentile(latencies, 95) or 0.0, 2) if latencies else None,
        "latency_p99_ms": round(percentile(latencies, 99) or 0.0, 2) if latencies else None,
        "estimated_tokens_total": estimated_tokens_total,
        "estimated_cost_usd_total": round(estimated_cost_total, 6),
        "average_estimated_tokens_per_response": round(estimated_tokens_total / len(chat_events), 2) if chat_events else None,
        "response_quality_score": round(sum(quality_scores) / len(quality_scores), 2) if quality_scores else None,
        "user_satisfaction": round(positive_feedback / rated_feedback, 4) if rated_feedback else None,
        "feedback_positive_total": positive_feedback,
        "feedback_negative_total": negative_feedback,
        "storage_fallback_count": len(storage_fallback_events),
    }
    return summary


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "| KPI | Value |",
        "|---|---:|",
    ]
    ordered_keys = [
        "requests_total",
        "chat_requests_total",
        "request_success_rate",
        "fallback_rate",
        "containment_rate",
        "latency_p50_ms",
        "latency_p95_ms",
        "latency_p99_ms",
        "estimated_tokens_total",
        "estimated_cost_usd_total",
        "user_satisfaction",
        "storage_fallback_count",
    ]
    for key in ordered_keys:
        lines.append(f"| {key} | {summary.get(key)} |")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate ARC chatbot KPI events from log files.")
    parser.add_argument("--input", required=True, help="Path to the application log file.")
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    args = parser.parse_args()

    input_path = Path(args.input)
    events: list[tuple[str, dict[str, Any]]] = []
    for line in input_path.read_text(encoding="utf-8").splitlines():
        parsed = parse_event_line(line)
        if parsed is not None:
            events.append(parsed)

    summary = aggregate_events(events)
    if args.format == "markdown":
        print(render_markdown(summary))
    else:
        print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())