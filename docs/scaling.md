# Scaling and Reliability Strategy

- **Status:** Baseline and staged guidance; no numeric capacity claims
- **Related:** [Architecture](architecture.md), [System design](system-design.md), [Requirements](requirements.md)

## 1. Current scaling baseline

The current app is a small synchronous FastAPI service. It has no research queue or caching layer. Account/profile data, reports, and chat messages are stored in MySQL; model-provider calls can dominate request latency. The current `/health` endpoint reports process liveness only.

No throughput, latency, or availability targets have been measured. Do not size production or promise SLAs from the current test suite.

## 2. Measure before scaling

Establish a representative workload and collect:

- request rate and concurrency by route;
- p50/p95/p99 API latency and error rate;
- auth DB query latency, pool checkout wait, active/idle connections, MySQL CPU, storage, and lock waits;
- provider latency, timeout/error rate, token use, and cost by provider/model;
- signup volume and auth failures, with privacy-preserving aggregation;
- process CPU, memory, event-loop/thread-pool saturation, and restart count.

Record workload assumptions (active users, requests per user, report/chat mix, provider latency, and expected data retention). Define numerical objectives only after operator review of these measurements.

## 3. Growth stages

### Stage 0 - Local and early pilot

- Run one FastAPI process behind a local development server.
- Use a reachable MySQL database and one configured model endpoint.
- Keep open signup limited to trusted test environments.
- Confirm backup and restore manually before retaining any valuable user data.

### Stage 1 - Single hosted instance

- Place the app behind an HTTPS reverse proxy.
- Keep MySQL private and grant a dedicated least-privilege app account.
- Configure startup/restart supervision, log collection, secret storage, and backups.
- Add signup abuse controls and a clear operator process for database/provider outages.
- Define readiness separately from liveness.

### Stage 2 - Multiple app workers or replicas

- Use a shared managed or separately operated MySQL service reachable from all replicas.
- Configure and monitor SQLAlchemy pool limits for every worker process. Total possible connections scale with the number of processes and their pool settings; keep the aggregate below the DB connection budget.
- Use a load balancer and TLS termination. Auth sessions are DB-backed, so browser stickiness is not required for session validation.
- Avoid running schema creation or migrations independently from every replica. Introduce versioned migrations and a controlled single migration job before schema evolution or multi-instance rollout.
- Verify graceful shutdown, connection draining, and behavior during DB/provider failures.

### Stage 3 - Durable, long-running research

Only after source retrieval and multi-step research are designed:

- Persist owner-scoped research runs and intermediate state.
- Move work that exceeds interactive request durations to a durable queue and worker pool.
- Define idempotency, retries, cancellation, progress reporting, dead-letter handling, and partial-result semantics.
- Bound concurrency and per-run budgets for provider calls, search/fetch tools, wall time, and cost.
- Keep short interactive API calls separate from long-running worker execution.

### Stage 4 - Optimize from evidence

Use measurements to decide whether to tune indexes, pool sizes, query patterns, provider routing, caching, or database capacity. Add read replicas or partitioning only when measured query and data-growth patterns justify them. Do not cache user-specific reports without owner-aware cache keys, invalidation, and privacy review.

## 4. Likely bottlenecks and responses

| Bottleneck | Evidence to collect | First response |
|---|---|---|
| Slow model provider | Provider latency/error/token metrics | Timeouts, clear error states, concurrency limits, provider configuration review |
| MySQL connection exhaustion | Connection counts, checkout waits, worker count | Bound pools, reduce excess workers, increase DB capacity only after budget review |
| Growing session/message tables | Row counts, message volume, query latency | Retention/cleanup policy and indexed expiry/history handling |
| Long research request | End-to-end duration and timeout rate | Persist run state and move bounded workflow to workers |
| High provider cost | Tokens and cost per user/run | Per-run limits, operator quotas, model choice and usage reporting |
| Growing conversation history | History query latency and message volume | Pagination, retention policy, and bounded context windows |

## 5. Resilience and data operations

- Define DB backup frequency, retention, encryption, and restore-test cadence with operators.
- Test upgrades against a copy of production-like data before deployment.
- Keep database migrations backward-compatible across rolling app releases where multiple versions may run simultaneously.
- Use bounded timeouts and retries; do not retry non-idempotent operations blindly.
- A provider outage should affect the dependent chat/research operation, not authentication or health reporting.
- Avoid logging raw prompts, credentials, refresh tokens, or fetched private content by default.
- Conversation deletion removes live database rows transactionally; backups may retain deleted data until their retention period expires.
- For durable runs, persist a terminal `partial` or `failed` state and enough metadata to diagnose it.

## 6. Scaling decisions that need workload evidence

- Required concurrent users and peak requests.
- Expected research and chat request mix.
- MySQL service tier, connection budget, and data-retention horizon.
- Provider rate limits and acceptable cost per account/run.
- Availability, recovery-time, and recovery-point objectives.
- Whether a hosted deployment needs signup gating, quotas, or billing.

These are operator/product decisions; this document intentionally does not invent numeric thresholds.
