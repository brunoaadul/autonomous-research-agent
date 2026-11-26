# Product Requirements - Crokuta

- **Product:** Crokuta - Research Agent
- **Status:** Living document; scope baseline
- **Repository:** https://github.com/brunoaadul/autonomous-research-agent
- **Audience:** Product owner, engineering, operations, contributors

## 1. Product vision

Crokuta should help a user move from a research question to a structured, evidence-backed report through a controlled and reproducible workflow. The intended system will plan research, discover relevant sources, extract evidence, assess source quality, identify gaps, conduct bounded follow-up research, and synthesize a report with traceable citations.

This vision is not a claim that those capabilities are already implemented. See each requirement's status label below and [system design](system-design.md) for the as-built baseline.

## 2. Current product baseline

The current repository provides:

- A FastAPI application serving a browser workspace and API from one origin.
- MySQL-backed email/password signup, login, and session management. Registration collects full name, phone number, email, and country. Public signup is enabled.
- Owner-scoped conversations in MySQL containing the preliminary research brief and persisted user/assistant messages. Users can reopen and delete conversations.
- A protected endpoint that creates a structured **preliminary research framework** using deterministic templates. It does not retrieve or verify external sources.
- Follow-up chat through a LiteLLM-based provider gateway, with messages persisted in their conversation.
- Server-side deployment configuration for database and model-provider connections.

The product can be deployed as a hosted instance or independently self-hosted. Each installation owns its own account database. The repository currently has no `LICENSE`; redistribution terms remain a release decision.

## 3. Product objectives

1. **Trustworthy outputs:** never imply that sources were retrieved, checked, or cited unless the relevant pipeline actually ran.
2. **Useful research workflow:** turn broad questions into focused subquestions, then support source-backed investigation and synthesis.
3. **Portable deployment:** make the same application usable as a hosted service and as a self-hosted deployment with operator-controlled database and provider configuration.
4. **Safe, private accounts:** protect credentials and sessions; ensure any persisted user content is isolated by authenticated ownership.
5. **Bounded operations:** constrain research iterations, external requests, model usage, latency, and cost.
6. **Operable releases:** provide reproducible setup, schema evolution, health visibility, backup/restore guidance, and automated checks.

## 4. Users and primary jobs

### Researcher / analyst

Wants to investigate a question, explore subtopics, review supporting evidence, and produce a clear report.

### Workspace user

Wants to sign in, create briefs, revisit their work, and continue a conversation about a brief.

### Hosted-service operator

Wants to offer a reliable instance, configure providers, control signup and abuse, monitor cost and incidents, and protect user data.

### Self-hosting operator

Wants to install Crokuta on their server, connect a MySQL database and model providers, manage upgrades and backups, and keep operational control.

## 5. Functional requirements

Status labels: **Implemented** means present in the current repository; **Target** means intended but not complete; **Decision** means product or operational policy still needs approval.

### FR-01 - Account access and profile (Implemented baseline; hardening target)

Users can register with full name, phone number, email, country, and password, then sign in using email and password backed by the installation's MySQL database. Signup is currently open.

Acceptance:

- Valid registration creates a unique normalized email account and establishes a session.
- Full name, phone number, and country are required and persisted with the account.
- Phone input is format-checked but is not verified against a phone carrier or country numbering plan.
- Duplicate accounts and invalid credentials are rejected without disclosing whether a password was correct.
- Access tokens expire; refresh tokens rotate; logout revokes the session.
- Protected APIs reject missing, invalid, expired, or revoked credentials.
- Future user-owned records are authorized by server-side ownership checks.
- Before a public hosted launch, account recovery, email verification, signup abuse controls, and signup policy are explicitly addressed.

### FR-02 - Submit a research question (Implemented as preliminary framework)

An authenticated user can submit a question and receive a structured preliminary response saved as a new conversation.

Acceptance:

- Input is validated at the API boundary, including the supported length range.
- Output follows a stable Pydantic response schema.
- The response includes a durable conversation identifier and the owner can reopen it later.
- The response clearly states that external sources were not retrieved.
- Errors are returned as errors, not as successful empty reports.

### FR-03 - Follow-up chat (Implemented baseline)

An authenticated user can continue an owned conversation through a selected provider.

Acceptance:

- Provider requests are routed through the shared gateway.
- Provider failures are reported as failures.
- User messages are saved before provider execution; successful assistant messages are also saved.
- Conversation history is available after signing in again.
- A failed provider call may leave the submitted user message without an assistant response; the failure is shown to the user.
- Provider secrets are configured server-side wherever possible.
- The selected report and conversation context are correctly associated with the user.
- Before making chat persistent, define ownership, retention, deletion, and export behavior.

### FR-04 - Provider abstraction (Implemented baseline; configuration hardening target)

The application supports cloud and local/self-hosted model endpoints through LiteLLM.

Acceptance:

- Provider resolution remains isolated from research-domain logic.
- Unsupported provider/model configuration fails clearly.
- Tests can replace the provider with a deterministic fake.
- Production controls define which providers and endpoints operators permit.
- Request-level API key and API-base overrides are reviewed before public hosted use.

### FR-05 - Research planning (Target)

Decompose a broad question into explicit subquestions and a bounded plan.

Acceptance:

- The plan has a validated schema, scope, assumptions, and completion conditions.
- Limits exist for tasks, iterations, wall time, tool calls, and model usage.
- Invalid model output is rejected or repaired through a bounded, observable path.

### FR-06 - Source discovery and retrieval (Target)

Search and fetch external sources through controlled tools.

Acceptance:

- Each source records at least its URL, title when available, retrieval time, and content metadata.
- Outbound requests enforce URL/IP protections, timeouts, redirect policy, response-size limits, and allowed content types.
- Fetched content is treated as untrusted input and cannot grant tools or override system policy.
- Retrieval errors, exclusions, and partial completion are visible in the run record.

### FR-07 - Evidence extraction and source assessment (Target)

Extract evidence and assess source quality.

Acceptance:

- Evidence items link to a source and exact excerpt or location where feasible.
- Quality is represented as an assessment, not a guarantee of truth.
- Unsupported claims are not labeled verified.
- Conflicting or insufficient evidence is preserved and disclosed.

### FR-08 - Gap analysis and follow-up research (Target)

Identify unresolved subquestions and decide whether more research is justified.

Acceptance:

- Unresolved questions are structured and traceable to the plan.
- Iteration, elapsed time, tool calls, concurrency, and cost are bounded.
- The system can terminate with an explicit partial result when limits are reached.

### FR-09 - Report synthesis and history (Partially implemented)

Retain reports and messages in owner-scoped conversations; evolve preliminary reports into source-backed reports.

Acceptance:

- Material factual claims have traceable citations.
- Reports distinguish sourced evidence from analysis and recommendations.
- Current reports and messages are durable, scoped to an owner, and can be permanently deleted with their conversation.
- Retention, export, account-wide deletion, and backup-retention behavior are documented before public hosted launch.
- Responses and persisted reports are versioned or migratable when schemas evolve.

### FR-10 - Operations and observability (Target)

Operators can understand health, failures, latency, and cost without exposing sensitive data.

Acceptance:

- Logs use correlation identifiers and redact secrets and sensitive content.
- Database and provider errors have actionable categories.
- Latency, request counts, provider errors, and token usage are measurable where available.
- Health/readiness behavior distinguishes process liveness from required dependency availability.

## 6. Non-functional requirements

| Area | Requirement |
|---|---|
| Security | Password hashing, short-lived access credentials, rotating refresh credentials, server-side authorization, secret handling, safe outbound retrieval |
| Privacy | Data minimization, owner isolation, documented retention, deletion and backup behavior |
| Reliability | Explicit timeouts, bounded retries, idempotency where appropriate, recoverable database upgrades |
| Performance | Collect representative baselines before setting numerical service objectives |
| Cost control | Bound model calls, tokens, searches, fetches, concurrency, and research iterations |
| Maintainability | Typed schemas, clear module boundaries, focused tests, documented decisions |
| Portability | Deployment configuration separated from product logic; supported DB and runtime versions documented |
| Observability | Correlation IDs, latency and error categories, token/cost measurements without sensitive prompt logging |
| Accessibility | Keyboard-accessible controls, visible focus, labels, and useful error announcements |

Do not invent numeric SLAs. Set targets after establishing workload assumptions and collecting measurements.

## 7. Out of scope until approved

- Guaranteed factual correctness or a claim that AI output is authoritative.
- Unbounded autonomous browsing or execution of instructions found in retrieved content.
- Arbitrary user-supplied network endpoints in a public hosted service.
- Multi-tenant enterprise administration, SSO, billing, or organization roles.
- Semantic memory beyond saved conversation history, vector search, or personalization beyond the required account profile.
- Automatic model training or fine-tuning.
- PDF/export formats or external integrations without a scoped release requirement.

## 8. Success measures

Establish a representative evaluation set before setting targets. Track:

- Research runs completing without system errors.
- Report claims with valid source references once retrieval exists.
- Citation availability and excerpt traceability.
- User-rated usefulness, clarity, and trust.
- Median/P95 request and run duration.
- Model tokens/cost per completed run.
- Provider timeout, malformed-output, retrieval-failure, and budget-termination rates.
- Account abuse and authentication failure rates, without retaining unnecessary personal data.

## 9. Decisions to resolve before public hosted launch

- Open signup versus operator-controlled/closed signup, and abuse prevention.
- Email verification and password/account recovery.
- Data retention, export, deletion, privacy notice, and incident-response responsibilities.
- Allowed providers, per-user or per-installation usage limits, and who pays provider costs.
- License and redistribution terms.
- Supported deployment environments, backup/restore objectives, and upgrade policy.
