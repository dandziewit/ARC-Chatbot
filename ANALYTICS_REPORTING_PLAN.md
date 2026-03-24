# ARC Analytics Reporting Plan

## Purpose

This document defines a KPI dashboard and measurement plan for ARC across the backend API in [backend/main.py](backend/main.py) and the orchestration layer in [backend/orchestrator.py](backend/orchestrator.py).

The goals are:

- measure response quality over time
- detect fallback overuse and degraded containment
- monitor latency and operational reliability
- estimate token cost for future model-backed deployments
- track user satisfaction in a way that is comparable week over week
- produce a weekly report that leads to action, not just observation

## Current Instrumentation Reality

Today, ARC already emits:

- span timing through [backend/observability.py](backend/observability.py)
- `chat.response` events with:
  - `session_id`
  - `strategy`
  - `safety_routed`
  - `fallback_used`

Today, ARC does not yet emit dedicated events for:

- user satisfaction
- containment outcome
- token usage or estimated cost
- request status classification by endpoint
- retry attempt counts
- model/tool latency breakdown
- resolution outcome or escalation outcome

This means the dashboard should be split into:

- Tier 1: metrics you can derive immediately
- Tier 2: metrics that require instrumentation changes

## KPI Dashboard Design

Design the dashboard in four sections:

1. Executive summary
2. Quality and containment
3. Reliability and latency
4. Cost and user sentiment

## Dashboard Layout

### Section 1: Executive Summary

Show these headline KPIs for the last 7 days and compare them with the previous 7 days:

- total conversations
- total chat requests
- response quality score
- fallback rate
- containment rate
- p50 latency
- p95 latency
- estimated token cost
- user satisfaction score

Each tile should show:

- current value
- week-over-week delta
- target band
- traffic-light status

### Section 2: Quality and Containment

Charts:

- response quality trend by day
- fallback rate trend by day
- containment rate trend by day
- strategy mix stacked bar:
  - `tool_call`
  - `direct_answer`
  - `ask_followup`
  - `reflect`
  - `clarify_context`
  - `fallback`
  - `safety`
- safety-routed conversations count by day

Breakdowns:

- by environment
- by strategy
- by session cohort
- by new vs returning user

### Section 3: Reliability and Latency

Charts:

- request volume by endpoint
- p50, p95, and p99 latency by endpoint
- rate-limit rejection rate
- retry rate
- backend error rate
- storage fallback activation count:
  - Redis unavailable fallback to in-memory
  - Postgres unavailable fallback to SQLite

Breakdowns:

- by endpoint
- by deployment version
- by infrastructure region if introduced later

### Section 4: Cost and User Sentiment

Charts:

- estimated token cost by day
- average response length by day
- user satisfaction score by day
- thumbs up vs thumbs down distribution
- satisfaction by strategy type

If no explicit model tokens exist yet, use placeholder operational proxies until model-backed generation is introduced.

## KPI Definitions

## 1. Response Quality

Definition:
The percentage of evaluated responses that meet the quality bar defined in [MODEL_QA_FRAMEWORK.md](MODEL_QA_FRAMEWORK.md).

Recommended calculation:

$$
\text{Response Quality Rate} = \frac{\text{responses passing QA}}{\text{responses evaluated}} \times 100
$$

Operational versions:

- Offline quality score from deterministic and rubric eval runs
- Online sampled quality score from manually reviewed production conversations

Data sources:

- deterministic evaluator in [scripts/evaluate_model_qa.py](scripts/evaluate_model_qa.py)
- weekly sampled review set
- user satisfaction feedback as a secondary signal

Target:

- green: $\ge 95\%$
- yellow: $90\%$ to $94.9\%$
- red: $< 90\%$

Alert threshold:

- page or high-priority alert if quality drops by more than 5 percentage points week over week
- warning if below 92% for 2 consecutive days

## 2. Fallback Rate

Definition:
The share of chat responses where `fallback_used = true` or `strategy = fallback`.

Calculation:

$$
\text{Fallback Rate} = \frac{\text{fallback responses}}{\text{total chat responses}} \times 100
$$

Data source:

- `chat.response` event from [backend/orchestrator.py](backend/orchestrator.py)

Interpretation:

- low is generally better
- a spike usually means repetition issues, retry exhaustion, or degraded answer quality

Target:

- green: $< 8\%$
- yellow: $8\%$ to $15\%$
- red: $> 15\%$

Alert threshold:

- warning at $> 12\%$ daily fallback rate
- critical at $> 20\%$ for any rolling 6-hour window

## 3. Containment Rate

Definition:
The percentage of conversations resolved without abandonment, agent handoff, or repeated failed turns.

Because ARC currently has no explicit handoff system, define containment operationally for now.

Phase 1 proxy definition:

A session is contained if all of the following are true:

- no more than 3 chat turns in the session
- no rate-limit failure on the session
- no repeated fallback loop
- no explicit negative feedback marker in the session

Phase 2 preferred definition:

- user indicates the issue is solved, or
- user ends the conversation after a successful response, or
- no re-contact on same issue within a defined window

Phase 1 proxy formula:

$$
\text{Containment Rate} = \frac{\text{sessions meeting containment proxy}}{\text{total sessions}} \times 100
$$

Target:

- green: $\ge 70\%$
- yellow: $60\%$ to $69.9\%$
- red: $< 60\%$

Alert threshold:

- warning if containment drops below 65% week to date
- critical if containment drops below 55% on a 3-day rolling basis

## 4. Latency

Definition:
Elapsed response time for API requests and for internal generation spans.

Primary metrics:

- p50 request latency
- p95 request latency
- p99 request latency
- p95 `chat.generate` span latency

Data source:

- `span.end` records in [backend/observability.py](backend/observability.py)

Needed instrumentation addition:

- explicit request-level event with endpoint and HTTP status

Targets:

- p50 chat latency: $< 250\,ms$
- p95 chat latency: $< 800\,ms$
- p99 chat latency: $< 1500\,ms$

Alert threshold:

- warning if p95 exceeds 1000 ms for 30 minutes
- critical if p95 exceeds 2000 ms for 15 minutes
- warning if p99 doubles relative to previous week baseline

## 5. Token Cost

Definition:
Estimated or actual cost of generating chatbot responses.

Current state:

- ARC is rule-based today, so actual model token cost is effectively 0
- but this KPI should be designed now because the backend is clearly evolving toward production architecture

Phase 1 placeholder metric:

- estimate pseudo-token usage from character length or word count of request and response

Example approximation:

$$
\text{Estimated Tokens} \approx \frac{\text{input chars} + \text{output chars}}{4}
$$

Phase 2 production metric:

- use actual model provider usage fields:
  - prompt tokens
  - completion tokens
  - cached tokens if relevant
  - per-request cost in USD

Dashboard metrics:

- total daily token cost
- average cost per conversation
- average tokens per response
- cost by strategy or route

Target:

- green: within budget baseline
- yellow: 10% over weekly budget
- red: 20% over weekly budget

Alert threshold:

- warning if average cost per conversation rises 15% week over week
- critical if total daily spend exceeds budget by 20%

## 6. User Satisfaction

Definition:
Direct user feedback on whether ARC was helpful.

Preferred signals:

- thumbs up or thumbs down per conversation
- 1 to 5 satisfaction survey after session
- optional binary question: "Did ARC solve your issue?"

Fallback proxy signals if explicit feedback is absent:

- conversation ends after a non-fallback response
- no immediate repeated rephrase of same question
- no negative correction language

Primary metric:

$$
\text{CSAT} = \frac{\text{positive ratings}}{\text{total ratings}} \times 100
$$

Target:

- green: $\ge 85\%$
- yellow: $75\%$ to $84.9\%$
- red: $< 75\%$

Alert threshold:

- warning if CSAT falls below 80% in a full week
- critical if CSAT drops below 70% or declines by 10 points week over week

## Supporting Metrics

Track these alongside the headline KPIs:

- request success rate
- 4xx rate
- 5xx rate
- rate-limit rejection rate
- safety-route rate
- retry rate
- retry exhaustion rate
- average conversation turns per session
- repeated-response rate
- storage fallback activation count

## Event and Data Model Plan

To compute the full dashboard reliably, add these events.

## Event 1: `http.request.completed`

Emit once per request.

Fields:

- `request_id`
- `endpoint`
- `method`
- `status_code`
- `duration_ms`
- `environment`
- `deployment_version`
- `session_id` if present
- `user_id` if present
- `rate_limited`

## Event 2: `chat.response`

Already exists, but extend it.

Current fields:

- `session_id`
- `strategy`
- `safety_routed`
- `fallback_used`

Add:

- `request_id`
- `user_id`
- `input_chars`
- `output_chars`
- `retry_count`
- `contained_proxy`
- `response_quality_sampled_score` when available
- `estimated_tokens`
- `estimated_cost_usd`

## Event 3: `chat.feedback`

Emit when user provides feedback.

Fields:

- `request_id`
- `session_id`
- `user_id`
- `feedback_type` such as `thumbs_up`, `thumbs_down`, `rating`, `free_text`
- `rating_value` if numeric
- `resolution_confirmed` boolean

## Event 4: `storage.fallback`

Emit when adapter fallback occurs during startup or runtime.

Fields:

- `component` such as `session_store` or `memory_store`
- `from_backend`
- `to_backend`
- `reason`
- `environment`

## Event 5: `retry.summary`

Emit per chat request when retries occur.

Fields:

- `request_id`
- `session_id`
- `retry_count`
- `retry_exhausted`
- `final_outcome`

## Measurement Plan

### Data Collection Frequency

- Request metrics: real time
- Chat events: real time
- Satisfaction events: real time
- QA batch scores: daily or per PR
- Weekly KPI aggregation: every Monday morning

### Data Retention

- raw events: 90 days minimum
- daily aggregates: 13 months
- weekly executive summaries: permanent or at least 24 months

### Recommended Storage Model

- raw event stream in logs or event table
- daily aggregate table for dashboard speed
- weekly reporting table for leadership summaries

## Dashboard Queries and Aggregations

Create daily aggregates with these keys:

- `date`
- `environment`
- `deployment_version`
- `endpoint`
- `strategy`

Core aggregate columns:

- `requests_total`
- `requests_2xx`
- `requests_4xx`
- `requests_5xx`
- `rate_limited_total`
- `chat_responses_total`
- `fallback_total`
- `safety_routed_total`
- `retry_total`
- `retry_exhausted_total`
- `contained_proxy_total`
- `feedback_positive_total`
- `feedback_negative_total`
- `feedback_rated_total`
- `estimated_tokens_total`
- `estimated_cost_usd_total`
- `latency_p50_ms`
- `latency_p95_ms`
- `latency_p99_ms`

## Weekly Reporting Format

Deliver a one-page weekly report with these sections.

### 1. Executive Summary

Include:

- weekly traffic volume
- quality trend
- fallback trend
- containment trend
- latency trend
- cost trend
- satisfaction trend
- top 3 risks
- top 3 actions

### 2. KPI Table

Use this table format:

| KPI | Current Week | Previous Week | Delta | Target | Status | Owner |
|---|---:|---:|---:|---:|---|---|
| Response quality | 96.2% | 95.4% | +0.8 pts | >=95% | Green | Product |
| Fallback rate | 6.4% | 5.8% | +0.6 pts | <8% | Green | Eng |
| Containment rate | 68.1% | 71.5% | -3.4 pts | >=70% | Yellow | Product |
| P95 latency | 710 ms | 640 ms | +70 ms | <800 ms | Green | Eng |
| Est. token cost | $0 | $0 | flat | budget | Green | Eng |
| CSAT | 82% | 86% | -4 pts | >=85% | Yellow | Product |

### 3. Segment Breakdown

Include at least:

- by strategy type
- by new vs returning users
- by top intent category if available later
- by deployment version

### 4. Incidents and Anomalies

Report:

- any threshold breach
- any safety anomalies
- any fallback spikes
- any storage fallback incidents
- any sustained latency regressions

### 5. Actions for Next Week

Format:

- issue
- hypothesis
- owner
- due date
- expected KPI impact

## Alert Thresholds Summary

Use these default thresholds.

| Metric | Warning | Critical | Action |
|---|---|---|---|
| Response quality | <92% daily | <90% daily | review regressions and rollback if release-related |
| Fallback rate | >12% daily | >20% over 6 hours | inspect retry failures, repeated-response patterns, and strategy mix |
| Containment rate | <65% week to date | <55% over 3 days | review failed journeys and unresolved-session cohorts |
| P95 chat latency | >1000 ms for 30 min | >2000 ms for 15 min | inspect infrastructure, storage latency, and retry storms |
| Rate-limit rejection rate | >3% daily | >8% daily | verify abuse vs under-provisioning or bad client behavior |
| Retry exhaustion rate | >2% daily | >5% daily | inspect downstream failures and fallback path quality |
| Storage fallback count | >0 in prod day | >3 in prod day | inspect Redis/Postgres health and deployment config |
| CSAT | <80% weekly | <70% weekly | sample transcripts and prioritize quality fixes |
| Safety-route misses | any suspected miss | any confirmed miss | immediate incident review and release block |

## Action Playbooks

### If Fallback Rate Spikes

Check:

- retry exhaustion rate
- repeated prompt patterns
- tool router failures
- session dedupe logic
- recent release changes in [backend/orchestrator.py](backend/orchestrator.py)

Actions:

- inspect fallback sessions sampled from logs
- compare strategy mix to prior week
- rollback if spike correlates to a deploy

### If Containment Drops

Check:

- sessions with 4 or more turns
- repeated rephrases of same question
- fallback concentration
- satisfaction by strategy

Actions:

- review transcript samples
- add targeted eval cases for weak flows
- adjust prompts or routing logic

### If Latency Regresses

Check:

- request-level duration
- retry counts
- storage backend health
- rate-limit pressure

Actions:

- identify slow path by endpoint and strategy
- inspect adapter availability and retry storms
- tune retry budgets or infrastructure

### If CSAT Drops

Check:

- negative feedback comments
- strategy cohorts with worst ratings
- correlation with fallback or latency spikes

Actions:

- sample 20 low-rated conversations
- classify root causes into correctness, tone, latency, or safety
- turn top defects into deterministic or behavioral eval cases

## Recommended Implementation Order

1. Start dashboarding current signals:
   - chat volume
   - fallback rate
   - safety route count
   - `chat.generate` latency
2. Add request-completed events for status and latency by endpoint.
3. Add feedback events for explicit satisfaction.
4. Add retry and storage fallback events.
5. Add estimated token and cost fields even if they are zero initially.
6. Connect weekly QA batch scores from [scripts/evaluate_model_qa.py](scripts/evaluate_model_qa.py) into the dashboard as an offline quality track.

## Minimal Viable Dashboard

If you need a lean v1 dashboard, start with these six tiles and two charts.

Tiles:

- chat requests
- fallback rate
- containment proxy rate
- p95 latency
- safety-routed count
- CSAT

Charts:

- daily fallback rate trend
- daily p95 latency trend

This is enough to detect most obvious product and operational regressions before the dashboard becomes more elaborate.