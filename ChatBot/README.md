# ARC Chatbot

ARC is a modular, interview-ready chatbot project built in Python. It demonstrates a complete conversational pipeline: intent detection, memory, knowledge lookup, response strategy, personality modulation, confidence scoring, and proactive prompts. The system is intentionally lightweight (regex and rules) so the full logic is transparent and easy to explain.

## Features

- Intent detection with regex-based patterns
- Emotion detection and tone adaptation
- Multi-turn memory and topic tracking
- Knowledge and reasoning engine (facts + math)
- Response strategy selection with loop prevention
- Personality engine with persistence across turns
- Confidence metrics with exponential decay
- Proactive prompts when conversation stalls
- Teaching system with multi-level explanations
- CLI chat loop (easy to test and demo)

## Project Structure

- arc.py: All chatbot logic and the main loop
- backend/: Production backend scaffold (API, orchestrator, storage, reliability controls)
- requirements-backend.txt: Backend service dependencies
- Dockerfile.backend: Backend container image
- docker-compose.backend.yml: Local backend + Redis + Postgres stack
- .env.backend.example: Backend environment configuration template

## Requirements

- Python 3.8+

## Quick Start

1. Open a terminal in the project folder
2. Run the chatbot:

```bash
python arc.py
```

3. Type your message and press Enter
4. Type "exit" to quit

## Production Backend Quick Start

1. Install backend dependencies:

```bash
pip install -r requirements-backend.txt
```

2. Run backend API locally:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

3. Test health endpoint:

```bash
curl http://localhost:8000/healthz
```

4. Test chat endpoint:

```bash
curl -X POST http://localhost:8000/v1/chat \
	-H "Content-Type: application/json" \
	-d '{"session_id":"demo-1","user_id":"u-1","message":"hey"}'
```

5. Optional Docker Compose stack:

```bash
docker compose -f docker-compose.backend.yml up --build
```

## Render Deployment

This project is ready to deploy to Render as a web service.

Quick path:

1. Push the repo to GitHub
2. Create a new Render Blueprint deployment
3. Let Render use [render.yaml](render.yaml)
4. Open the generated public URL

Start command used by Render:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

Important note:

- The public demo path uses `/v1/chat/simple`
- That endpoint keeps session state in memory only
- On free Render instances, sleep/restart can clear that memory

See [RENDER_DEPLOYMENT.md](RENDER_DEPLOYMENT.md) for the full setup and tradeoffs.

## Performance Benchmarking & Optimization

The project includes comprehensive performance analysis tools:

### Running Performance Benchmarks

```bash
# Benchmark latency, throughput, and identify bottlenecks
python scripts/benchmark_performance.py

# Analyze parameter sensitivity (prompt size, retrieval steps, tool calls)
python scripts/analyze_bottlenecks.py

# Generate optimization roadmap with ROI analysis
python scripts/generate_optimization_report.py
```

### Output Reports

- **PERFORMANCE_BENCHMARKING_REPORT.md** - Comprehensive findings and recommendations
- **scripts/benchmark_report.json** - Raw latency measurements
- **scripts/bottleneck_analysis.json** - Parameter sensitivity analysis
- **scripts/optimization_report.json** - Prioritized optimization roadmap

### Key Findings

- **Average Latency:** 2.8ms (component level) with 10.15ms for persistent storage
- **Throughput:** 100+ req/sec baseline, 200+ req/sec with optimizations
- **Bottleneck:** Memory store persistence (41% of total latency)
- **Opportunities:** 7 optimization proposals with potential 45-70% latency reduction
- **ROI:** $1,050 annual savings with $3,900 implementation cost (11 month payback)

## How the Pipeline Works

ARC processes each message in a consistent order:

1. Detect emotion
2. Detect intent
3. Build context from memory
4. Select response strategy
5. Generate response using knowledge/memory
6. Adapt tone and personality
7. Update memory
8. Return the response

This makes the code easy to walk through and explain in interviews.

## Backend Reliability and Scale Design

The backend service is designed for low-risk migration from a single-process chatbot to a production architecture.

### Core Components

- API ingress (`backend/main.py`)
	- Stateless FastAPI endpoints
	- Per-caller rate limiting
	- Health and readiness checks
- Orchestrator (`backend/orchestrator.py`)
	- Intent and strategy routing
	- Crisis safety routing
	- Tool routing with allowlist
	- Fallback and anti-repetition behavior
- Session state (`backend/session_store.py`)
	- Session snapshots for recent turns and response dedupe
	- Supports in-memory and Redis-backed adapters (feature flag)
- Memory storage (`backend/memory_store.py`)
	- Durable event logging with SQLite and Postgres adapters (feature flag)
- Reliability controls
	- Retry with exponential backoff (`backend/retry.py`)
	- Rate limiting (`backend/rate_limit.py`)
	- Structured observability hooks (`backend/observability.py`)
- Safety guardrails (`backend/safety.py`)
	- Crisis keyword detection and emergency response routing

### Deployment Pattern

- Stateless API containers behind a load balancer
- Redis for shared session state
- Postgres for durable long-term memory and analytics
- Feature flags in `.env.backend.example` for gradual rollout

## Phased Migration Plan (Low Risk)

1. Phase 0: Instrument current system
	 - Add request IDs, structured logs, and error metrics
	 - Keep existing chatbot runtime unchanged

2. Phase 1: Introduce stateless API facade
	 - Deploy `backend/main.py`
	 - Route a small percentage of traffic to the new endpoint

3. Phase 2: Session externalization
	 - Replace in-memory session store with Redis-backed store
	 - Use feature flag to switch reads gradually

4. Phase 3: Durable memory migration
	 - Move from SQLite to Postgres event store
	 - Dual-write during migration, then flip read path

5. Phase 4: Retry, fallback, and guardrails hardening
	 - Tune retry budgets and fallback triggers
	 - Add policy alerts for crisis/safety routing

6. Phase 5: Scale out and operate
	 - Horizontal autoscaling
	 - SLO-based alerting and canary deployments

## Testing

Run backend unit/API tests:

```bash
pytest
```

Run deterministic model QA cases:

```bash
python scripts/evaluate_model_qa.py --set qa_sets/v1/deterministic.jsonl
```

Aggregate chatbot KPI logs into a report:

```bash
python scripts/aggregate_chatbot_kpis.py --input arc-backend.log --format markdown
```

Quality framework and rubric:

- `MODEL_QA_FRAMEWORK.md`
- `qa_sets/v1/deterministic.jsonl`
- `qa_sets/v1/behavioral.jsonl`
- `qa_sets/v1/adversarial.jsonl`
- `ANALYTICS_REPORTING_PLAN.md`
- `dashboard_specs/arc_kpi_dashboard.json`

## API Contract

### POST `/v1/chat`

Request body:

```json
{
	"session_id": "session-123",
	"user_id": "user-42",
	"message": "Can you calculate 2 + 2?"
}
```

Response body:

```json
{
	"session_id": "session-123",
	"response": "Result: 4.0",
	"strategy": "tool_call",
	"safety_routed": false,
	"fallback_used": false
}
```

## Notes

- The project is deliberately rule-based (no external NLP libraries) so the behavior is deterministic and easy to reason about.
- Personality and learning systems are designed for clarity over complexity.

## License

MIT
