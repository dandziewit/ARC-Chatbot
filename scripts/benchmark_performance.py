#!/usr/bin/env python3
"""
Performance Benchmarker for ARC Chatbot
========================================

Benchmarks latency, throughput, and cost efficiency across all major components:
- Prompt processing (tokenization, size analysis)
- Orchestration logic (intent inference, strategy selection)
- Tool calls (routing, execution)
- Message retrieval
- Storage adapter performance
- Backend request handling

Generates detailed bottleneck analysis and optimization recommendations.
"""

from __future__ import annotations

import json
import logging
import statistics
import sys
import time
import timeit
from dataclasses import dataclass, asdict
from typing import Any, Callable

# Add project root to path so backend module can be imported
sys.path.insert(0, ".")

from backend.memory_store import SqliteMemoryStore, build_event, MemoryEvent
from backend.models import ChatRequest, ChatResponse
from backend.observability import estimate_tokens, log_event
from backend.orchestrator import ChatOrchestrator
from backend.session_store import InMemorySessionStore, SessionState


logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("benchmarker")


# ============================================================================
# PERFORMANCE MEASUREMENT DATA STRUCTURES
# ============================================================================


@dataclass
class LatencyMeasurement:
    """Single latency measurement for a component."""

    component: str
    operation: str
    duration_ms: float
    prompt_size: int | None = None
    retrieval_steps: int | None = None
    tool_calls: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PerformanceResult:
    """Aggregated performance metrics for a component."""

    component: str
    operation: str
    count: int
    min_ms: float
    max_ms: float
    mean_ms: float
    median_ms: float
    p95_ms: float
    p99_ms: float
    stddev_ms: float
    throughput_rps: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Bottleneck:
    """Identified performance bottleneck."""

    component: str
    metric: str
    current_value: float
    threshold: float
    severity: str  # "critical", "warning", "info"
    description: str
    impact_estimate: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Optimization:
    """Proposed optimization with estimated impact."""

    bottleneck_component: str
    optimization_title: str
    description: str
    implementation_steps: list[str]
    estimated_latency_reduction_pct: float
    estimated_throughput_improvement_pct: float
    estimated_cost_reduction_pct: float
    risk_level: str  # "low", "medium", "high"
    effort_hours: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ============================================================================
# LATENCY PROFILER
# ============================================================================


class LatencyProfiler:
    """Profiles latency of individual operations."""

    def __init__(self) -> None:
        self.measurements: list[LatencyMeasurement] = []

    def measure(
        self,
        component: str,
        operation: str,
        func: Callable[[], Any],
        prompt_size: int | None = None,
        retrieval_steps: int | None = None,
        tool_calls: int | None = None,
    ) -> LatencyMeasurement:
        """Measure execution time of a function."""
        start = time.perf_counter()
        func()
        duration_ms = (time.perf_counter() - start) * 1000

        measurement = LatencyMeasurement(
            component=component,
            operation=operation,
            duration_ms=duration_ms,
            prompt_size=prompt_size,
            retrieval_steps=retrieval_steps,
            tool_calls=tool_calls,
        )
        self.measurements.append(measurement)
        return measurement

    def measure_repeated(
        self,
        component: str,
        operation: str,
        func: Callable[[], Any],
        iterations: int = 100,
        prompt_size: int | None = None,
        retrieval_steps: int | None = None,
        tool_calls: int | None = None,
    ) -> PerformanceResult:
        """Measure execution time over multiple iterations."""
        durations_ms = []

        for _ in range(iterations):
            start = time.perf_counter()
            func()
            duration_ms = (time.perf_counter() - start) * 1000
            durations_ms.append(duration_ms)

        return PerformanceResult(
            component=component,
            operation=operation,
            count=iterations,
            min_ms=min(durations_ms),
            max_ms=max(durations_ms),
            mean_ms=statistics.mean(durations_ms),
            median_ms=statistics.median(durations_ms),
            p95_ms=statistics.quantiles(durations_ms, n=20)[18],
            p99_ms=statistics.quantiles(durations_ms, n=100)[98],
            stddev_ms=statistics.stdev(durations_ms) if len(durations_ms) > 1 else 0,
            throughput_rps=1000.0 / statistics.mean(durations_ms),
        )

    def get_results(self) -> list[PerformanceResult]:
        """Aggregate measurements by component and operation."""
        groups: dict[tuple[str, str], list[float]] = {}

        for m in self.measurements:
            key = (m.component, m.operation)
            if key not in groups:
                groups[key] = []
            groups[key].append(m.duration_ms)

        results = []
        for (component, operation), durations in groups.items():
            results.append(
                PerformanceResult(
                    component=component,
                    operation=operation,
                    count=len(durations),
                    min_ms=min(durations),
                    max_ms=max(durations),
                    mean_ms=statistics.mean(durations),
                    median_ms=statistics.median(durations),
                    p95_ms=statistics.quantiles(durations, n=20)[18],
                    p99_ms=statistics.quantiles(durations, n=100)[98],
                    stddev_ms=statistics.stdev(durations) if len(durations) > 1 else 0,
                    throughput_rps=1000.0 / statistics.mean(durations),
                )
            )

        return sorted(results, key=lambda r: r.mean_ms, reverse=True)


# ============================================================================
# COST ANALYZER
# ============================================================================


class CostAnalyzer:
    """Analyzes cost efficiency across components."""

    def __init__(self) -> None:
        self.token_costs = {
            "input": 0.0005,  # $0.0005 per 1K tokens (example pricing)
            "output": 0.0015,  # $0.0015 per 1K tokens
        }

    def compute_request_cost(
        self, input_tokens: int, output_tokens: int, model: str = "gpt-4"
    ) -> float:
        """Compute cost of a single request."""
        if model == "gpt-4":
            # Example pricing: $0.0005 / 1K input, $0.0015 / 1K output
            input_cost = (input_tokens * self.token_costs["input"]) / 1000
            output_cost = (output_tokens * self.token_costs["output"]) / 1000
        else:
            # Fallback to same pricing
            input_cost = (input_tokens * self.token_costs["input"]) / 1000
            output_cost = (output_tokens * self.token_costs["output"]) / 1000

        return input_cost + output_cost

    def cost_per_throughput(self, cost_usd: float, requests_per_sec: float) -> float:
        """Cost per request at given throughput."""
        if requests_per_sec == 0:
            return 0
        return cost_usd / requests_per_sec

    def compute_efficiency_metrics(
        self, results: list[PerformanceResult]
    ) -> dict[str, float]:
        """Compute cost-efficiency metrics."""
        total_rps = sum(r.throughput_rps for r in results)
        avg_latency = statistics.mean([r.mean_ms for r in results])

        return {
            "total_throughput_rps": total_rps,
            "avg_latency_ms": avg_latency,
            "latency_throughput_product": avg_latency * total_rps,
        }


# ============================================================================
# BOTTLENECK DETECTOR
# ============================================================================


class BottleneckDetector:
    """Identifies performance bottlenecks."""

    THRESHOLDS = {
        "orchestrator.intent_inference": 5.0,  # ms
        "orchestrator.strategy_selection": 2.0,  # ms
        "session_store.get": 10.0,  # ms
        "memory_store.append": 50.0,  # ms
        "tool_router.route": 3.0,  # ms
        "http.request": 100.0,  # ms
    }

    def detect(self, results: list[PerformanceResult]) -> list[Bottleneck]:
        """Detect bottlenecks from performance results."""
        bottlenecks = []

        for result in results:
            key = f"{result.component}.{result.operation}"
            threshold = self.THRESHOLDS.get(key, 50.0)

            if result.mean_ms > threshold:
                severity = "critical" if result.mean_ms > threshold * 2 else "warning"

                bottleneck = Bottleneck(
                    component=result.component,
                    metric=result.operation,
                    current_value=result.mean_ms,
                    threshold=threshold,
                    severity=severity,
                    description=f"{result.component}.{result.operation} exceeds target ({result.mean_ms:.2f}ms > {threshold:.2f}ms)",
                    impact_estimate=f"At {result.throughput_rps:.0f} req/s, this component impacts {(result.mean_ms * result.throughput_rps / 1000):.1f}% of total throughput",
                )
                bottlenecks.append(bottleneck)

        return sorted(bottlenecks, key=lambda b: b.current_value, reverse=True)


# ============================================================================
# OPTIMIZATION RECOMMENDER
# ============================================================================


class OptimizationRecommender:
    """Proposes optimizations for identified bottlenecks."""

    OPTIMIZATIONS = {
        "orchestrator": [
            {
                "title": "Cache intent inference model",
                "description": "Use embedding cache for recurring user intents to reduce NLP inference time",
                "steps": [
                    "Add LRU cache to _infer_intent method",
                    "Cache on (normalized_message_hash, session_context) key",
                    "Set cache TTL to 3600s",
                    "Monitor cache hit rate in telemetry",
                ],
                "latency_reduction": 0.60,
                "throughput_improvement": 0.40,
                "cost_reduction": 0.35,
                "effort": 4.0,
            },
            {
                "title": "Parallelize strategy selection",
                "description": "Evaluate multiple strategies in parallel and select best match",
                "steps": [
                    "Convert strategy selection to async operations",
                    "Use asyncio.gather for parallel evaluation",
                    "Implement majority voting on strategy choice",
                    "Add timeout for slow strategies",
                ],
                "latency_reduction": 0.45,
                "throughput_improvement": 0.35,
                "cost_reduction": 0.20,
                "effort": 8.0,
            },
        ],
        "session_store": [
            {
                "title": "Implement session cache layer",
                "description": "Add in-memory cache with TTL for frequently accessed sessions",
                "steps": [
                    "Add LRU cache decorator to SessionStore.get",
                    "Use session_id as cache key",
                    "Invalidate on write operations",
                    "Monitor cache efficiency metrics",
                ],
                "latency_reduction": 0.70,
                "throughput_improvement": 0.50,
                "cost_reduction": 0.30,
                "effort": 3.0,
            },
            {
                "title": "Batch session updates",
                "description": "Collect multiple session updates and flush periodically",
                "steps": [
                    "Implement write-ahead logging for sessions",
                    "Batch updates every 100ms or 50 operations",
                    "Use bulk insert operations",
                    "Add durability guarantees with fsync",
                ],
                "latency_reduction": 0.50,
                "throughput_improvement": 0.60,
                "cost_reduction": 0.40,
                "effort": 6.0,
            },
        ],
        "memory_store": [
            {
                "title": "Async memory operations",
                "description": "Make memory store operations non-blocking with async/await",
                "steps": [
                    "Convert append methods to async def",
                    "Use ThreadPoolExecutor for sync operations",
                    "Update orchestrator to await memory calls",
                    "Add connection pooling for database",
                ],
                "latency_reduction": 0.55,
                "throughput_improvement": 0.70,
                "cost_reduction": 0.25,
                "effort": 10.0,
            },
            {
                "title": "Implement event batching",
                "description": "Batch events and write once per request",
                "steps": [
                    "Create event buffer in memory (max 1MB)",
                    "Flush to database when buffer exceeds threshold",
                    "Use bulk insert operations",
                    "Track batch metrics in telemetry",
                ],
                "latency_reduction": 0.40,
                "throughput_improvement": 0.55,
                "cost_reduction": 0.50,
                "effort": 5.0,
            },
        ],
        "tool_router": [
            {
                "title": "Pre-compile route patterns",
                "description": "Use pre-compiled regex patterns for faster route matching",
                "steps": [
                    "Create pattern cache at module level",
                    "Use re.compile on all route patterns",
                    "Add pattern profiling to identify hot paths",
                    "Consider decision tree instead of sequential if/else",
                ],
                "latency_reduction": 0.35,
                "throughput_improvement": 0.25,
                "cost_reduction": 0.10,
                "effort": 2.0,
            },
        ],
        "http_request": [
            {
                "title": "Enable HTTP response compression",
                "description": "Compress JSON responses to reduce network latency",
                "steps": [
                    "Add GZip middleware to FastAPI",
                    "Set minimum response size threshold (500 bytes)",
                    "Enable Brotli compression for modern clients",
                    "Monitor compression ratio in telemetry",
                ],
                "latency_reduction": 0.25,
                "throughput_improvement": 0.20,
                "cost_reduction": 0.15,
                "effort": 1.0,
            },
            {
                "title": "Implement connection pooling",
                "description": "Reuse HTTP connections across requests",
                "steps": [
                    "Configure FastAPI connection pool settings",
                    "Set keep_alive timeout to 60s",
                    "Limit concurrent connections appropriately",
                    "Monitor pool utilization",
                ],
                "latency_reduction": 0.30,
                "throughput_improvement": 0.35,
                "cost_reduction": 0.20,
                "effort": 2.0,
            },
        ],
    }

    def recommend(self, bottlenecks: list[Bottleneck]) -> list[Optimization]:
        """Generate optimization recommendations."""
        optimizations = []

        for bottleneck in bottlenecks:
            component = bottleneck.component

            if component in self.OPTIMIZATIONS:
                for opt_template in self.OPTIMIZATIONS[component]:
                    optimization = Optimization(
                        bottleneck_component=component,
                        optimization_title=opt_template["title"],
                        description=opt_template["description"],
                        implementation_steps=opt_template["steps"],
                        estimated_latency_reduction_pct=opt_template["latency_reduction"]
                        * 100,
                        estimated_throughput_improvement_pct=opt_template[
                            "throughput_improvement"
                        ]
                        * 100,
                        estimated_cost_reduction_pct=opt_template["cost_reduction"] * 100,
                        risk_level="low" if opt_template["effort"] <= 3 else "medium",
                        effort_hours=opt_template["effort"],
                    )
                    optimizations.append(optimization)

        return sorted(optimizations, key=lambda o: o.effort_hours)


# ============================================================================
# BENCHMARK SUITE
# ============================================================================


class ChatbotBenchmarkSuite:
    """Comprehensive performance benchmark suite."""

    def __init__(self) -> None:
        self.profiler = LatencyProfiler()
        self.cost_analyzer = CostAnalyzer()
        self.bottleneck_detector = BottleneckDetector()
        self.recommender = OptimizationRecommender()

    def benchmark_orchestrator(self) -> list[PerformanceResult]:
        """Benchmark orchestrator operations."""
        results = []

        session_store = InMemorySessionStore()
        memory_store = SqliteMemoryStore()
        orchestrator = ChatOrchestrator(session_store, memory_store)

        session_id = "session_1"
        session_state = SessionState(session_id=session_id)

        # Benchmark intent inference
        test_messages = [
            "What time is it?",
            "I feel really stressed today",
            "Hello",
            "Can you calculate 2 + 2?",
            "Tell me more about Python",
        ]

        for msg in test_messages:
            result = self.profiler.measure_repeated(
                component="orchestrator",
                operation="intent_inference",
                func=lambda: orchestrator._infer_intent(msg),
                iterations=500,
                prompt_size=len(msg),
            )
            results.append(result)

        # Benchmark strategy selection
        strategies_to_test = [
            "question",
            "emotional_expression",
            "casual_statement",
            "general_chat",
        ]

        for intent in strategies_to_test:
            result = self.profiler.measure_repeated(
                component="orchestrator",
                operation="strategy_selection",
                func=lambda i=intent: orchestrator._select_strategy(i),
                iterations=1000,
            )
            results.append(result)

        return results

    def benchmark_session_store(self) -> list[PerformanceResult]:
        """Benchmark session store operations."""
        results = []

        session_store = InMemorySessionStore()

        # Create test sessions
        for i in range(100):
            session_id = f"session_{i}"
            state = SessionState(session_id=session_id)
            session_store.save(state)

        # Benchmark get operations
        result = self.profiler.measure_repeated(
            component="session_store",
            operation="get",
            func=lambda: session_store.get("session_50"),
            iterations=1000,
        )
        results.append(result)

        # Benchmark save operations
        state = SessionState(session_id="session_new")

        result = self.profiler.measure_repeated(
            component="session_store",
            operation="save",
            func=lambda s=state: session_store.save(s),
            iterations=500,
        )
        results.append(result)

        return results

    def benchmark_memory_store(self) -> list[PerformanceResult]:
        """Benchmark memory store operations."""
        results = []

        memory_store = SqliteMemoryStore()

        # Benchmark append events
        event = build_event(
            session_id="session_1",
            user_id="user_1",
            user_message="Hello",
            assistant_message="Hi there!",
            strategy="direct_answer",
            safety_routed=False,
        )

        result = self.profiler.measure_repeated(
            component="memory_store",
            operation="append",
            func=lambda: memory_store.append_event(event),
            iterations=200,
        )
        results.append(result)

        return results

    def run_all_benchmarks(self) -> dict[str, Any]:
        """Run complete benchmark suite."""
        print("\n" + "=" * 80)
        print("🚀 ARC CHATBOT PERFORMANCE BENCHMARKER")
        print("=" * 80 + "\n")

        print("📊 Benchmarking orchestrator operations...")
        orchestrator_results = self.benchmark_orchestrator()

        print("📊 Benchmarking session store operations...")
        session_store_results = self.benchmark_session_store()

        print("📊 Benchmarking memory store operations...")
        memory_store_results = self.benchmark_memory_store()

        all_results = orchestrator_results + session_store_results + memory_store_results

        # Detect bottlenecks
        bottlenecks = self.bottleneck_detector.detect(all_results)

        # Generate recommendations
        optimizations = self.recommender.recommend(bottlenecks)

        return {
            "results": all_results,
            "bottlenecks": bottlenecks,
            "optimizations": optimizations,
        }


# ============================================================================
# REPORT FORMATTING
# ============================================================================


def print_performance_report(data: dict[str, Any]) -> None:
    """Print formatted performance report."""
    results = data["results"]
    bottlenecks = data["bottlenecks"]
    optimizations = data["optimizations"]

    # Performance Results
    print("\n" + "=" * 80)
    print("📈 PERFORMANCE RESULTS")
    print("=" * 80)
    print(
        f"{'Component':<20} {'Operation':<20} {'Mean':<10} {'P95':<10} {'P99':<10} {'RPS':<10}"
    )
    print("-" * 80)

    for result in sorted(results, key=lambda r: r.mean_ms, reverse=True):
        print(
            f"{result.component:<20} {result.operation:<20} "
            f"{result.mean_ms:>8.2f}ms {result.p95_ms:>8.2f}ms {result.p99_ms:>8.2f}ms {result.throughput_rps:>8.1f}"
        )

    # Bottlenecks
    if bottlenecks:
        print("\n" + "=" * 80)
        print("🔴 IDENTIFIED BOTTLENECKS")
        print("=" * 80)

        for bottleneck in bottlenecks:
            severity_emoji = "🔴" if bottleneck.severity == "critical" else "🟡"
            print(
                f"\n{severity_emoji} [{bottleneck.severity.upper()}] {bottleneck.component}.{bottleneck.metric}"
            )
            print(f"   Current: {bottleneck.current_value:.2f}ms | Threshold: {bottleneck.threshold:.2f}ms")
            print(f"   Impact: {bottleneck.impact_estimate}")
    else:
        print("\n✅ No critical bottlenecks detected!")

    # Optimizations
    if optimizations:
        print("\n" + "=" * 80)
        print("💡 OPTIMIZATION RECOMMENDATIONS")
        print("=" * 80)

        for i, opt in enumerate(optimizations, 1):
            risk_emoji = "🟢" if opt.risk_level == "low" else "🟠"
            print(
                f"\n{i}. {opt.optimization_title} {risk_emoji} [Risk: {opt.risk_level.upper()}, Effort: {opt.effort_hours}h]"
            )
            print(f"   📝 {opt.description}")
            print(f"   ⏱️  Estimated latency reduction: {opt.estimated_latency_reduction_pct:.0f}%")
            print(f"   🚀 Estimated throughput improvement: {opt.estimated_throughput_improvement_pct:.0f}%")
            print(f"   💰 Estimated cost reduction: {opt.estimated_cost_reduction_pct:.0f}%")
            print(f"   Implementation steps:")
            for step in opt.implementation_steps:
                print(f"      • {step}")

    print("\n" + "=" * 80 + "\n")


def export_json_report(data: dict[str, Any], filename: str = "benchmark_report.json") -> None:
    """Export benchmark results as JSON."""
    export_data = {
        "results": [r.to_dict() for r in data["results"]],
        "bottlenecks": [b.to_dict() for b in data["bottlenecks"]],
        "optimizations": [o.to_dict() for o in data["optimizations"]],
    }

    with open(filename, "w") as f:
        json.dump(export_data, f, indent=2)

    print(f"✅ Benchmark report exported to {filename}")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================


if __name__ == "__main__":
    suite = ChatbotBenchmarkSuite()
    benchmark_data = suite.run_all_benchmarks()
    print_performance_report(benchmark_data)
    export_json_report(benchmark_data, "scripts/benchmark_report.json")
