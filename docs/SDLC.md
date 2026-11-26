# Software Development Lifecycle and Delivery Objectives

- **Status:** Working delivery plan
- **Owner:** Product owner and engineering maintainers
- **Review cadence:** At each milestone boundary and before a public hosted launch

## 1. Delivery principles

- Ship verifiable increments rather than treating the product vision as already delivered.
- Each milestone has an objective, bounded scope, acceptance evidence, and explicit exit gate.
- Requirements, code, tests, deployment instructions, and operational procedures must agree.
- Security, privacy, and user-data ownership are release requirements, not post-launch enhancements.
- Prefer a modular monolith until usage or organizational constraints justify separating services.
- Report partial completion and remaining validation gaps honestly.

## 2. Current release position

The repository is a functional prototype with MySQL-backed profile/auth data, owner-scoped persistent conversations, protected preliminary briefs, and provider-backed chat. It is not yet a completed autonomous research product:

- no external source retrieval or source verification;
- no controlled multi-step research workflow;
- no migration framework, account recovery, or signup-abuse controls;
- no measured production SLOs, quotas, or operational readiness process.

Do not label a release as evidence-backed autonomous research until the relevant requirements are implemented and evaluated.

## 3. Milestones and objectives

### M0 - Product and architecture baseline (in progress)

**Objective:** establish shared, source-checked requirements and engineering direction.

Deliverables:

- product requirements and current-vs-target status;
- architecture, system design, and scaling strategy;
- an explicit release lifecycle and contributor instructions.

Exit gate:

- documents match current behavior and clearly separate implemented features from planned work;
- unresolved product and operator decisions are visible.

### M1 - Self-hostable foundation

**Objective:** make a fresh installation reproducible, maintainable, and safe for a controlled pilot.

Candidate scope:

- supported Python/MySQL versions and repeatable setup;
- database migrations and migration/backup/restore instructions;
- environment validation and liveness/readiness separation;
- signup controls, account recovery/email-verification decision, and abuse protection;
- remove or constrain request-level provider credential and endpoint overrides for the hosted threat model;
- privacy/retention policy for any data added to MySQL;
- CI for tests, lint/type checks selected by maintainers, and dependency review.

Exit gate:

- fresh install and upgrade are tested from documented steps;
- auth failure, DB-unavailable, and restart behavior are covered;
- production secrets are configured out-of-band;
- operator can back up and restore the supported database state.

### M2 - Durable workspace

**Objective:** complete and harden the persistent workspace already introduced.

Candidate scope:

- pagination and history search for large conversation lists;
- profile completion for accounts created before profile collection;
- account-wide export/deletion and retention policy;
- robust handling for failed or interrupted chat turns;
- authorization tests proving cross-user isolation;
- UI states for empty, loading, partial, and failed operations.

Exit gate:

- no user can access another user's content through guessed identifiers or altered requests;
- conversation deletion, retention, backup behavior, and account lifecycle are documented and tested;
- browser local state is a cache, not the access-control source of truth.

### M3 - Evidence-backed research v1

**Objective:** implement a bounded, traceable research workflow that retrieves and cites external evidence.

Candidate scope:

- validated plan and run state machine;
- safe search/fetch adapters with SSRF and resource protections;
- normalized sources and evidence excerpts with provenance;
- gap analysis and bounded follow-up;
- report synthesis, citations, limitations, and partial completion;
- deterministic evaluation set for citation validity, coverage, and failure cases.

Exit gate:

- each material factual claim has source traceability or is explicitly labeled analysis/uncertainty;
- external-content injection tests do not alter system policy or invoke unauthorized tools;
- every loop and external request has configured bounds;
- partial/failing retrieval is not shown as verified success.

### M4 - Hosted-service readiness and scale

**Objective:** safely operate the product for external users and multiple installations.

Candidate scope:

- deployment automation and supported topology;
- signup/abuse policy, quotas, and provider-cost controls;
- privacy notice, support, incident response, and account lifecycle procedures;
- structured operational metrics, dependency readiness, alerts, and tested backup recovery;
- load tests based on measured workloads and operator-approved objectives;
- license decision for distribution.

Exit gate:

- measured workload meets approved objectives;
- operators can detect and respond to database, provider, and worker failures;
- upgrade, rollback, restore, and data deletion processes are exercised;
- distribution, privacy, and provider-cost terms are clear to users.

## 4. Work item workflow

1. **Discover:** state the user/operator problem, inspect current behavior, record constraints and affected users.
2. **Specify:** define acceptance criteria, API/data changes, error cases, security/privacy impact, and migration requirements.
3. **Design:** document consequential architecture decisions; keep small changes within existing patterns.
4. **Implement:** make the smallest complete change, preserving unrelated worktree changes.
5. **Verify:** run focused tests, relevant full tests, syntax/type/lint checks available in the repository, and integration checks when dependencies exist.
6. **Review:** check correctness, authorization, privacy, failure behavior, performance implications, docs, and deployment compatibility.
7. **Release:** use a reviewed version, migration procedure, rollback path, and operator communication for production-impacting changes.
8. **Learn:** compare telemetry and user feedback with objectives; update requirements and risks.

## 5. Definition of Ready

A work item is ready when:

- the user or operator outcome is clear;
- scope and exclusions are stated;
- acceptance criteria can be tested or inspected;
- relevant data ownership, privacy, and security impact is understood;
- dependencies and migration/rollout implications are identified;
- unresolved product decisions are answered or explicitly deferred.

## 6. Definition of Done

A work item is done when:

- acceptance criteria are met in code or documented deliverables;
- focused tests cover success and important failure cases;
- full relevant test suite passes, or any failure is explained with evidence;
- API, schema, and compatibility effects are reviewed;
- docs and configuration examples match behavior;
- secrets, generated files, and unrelated changes are excluded;
- deployment, migration, monitoring, and rollback implications are recorded;
- known limitations and unverified external dependencies are disclosed.

## 7. Validation strategy

### Automated checks

- Unit tests for deterministic domain logic and validation.
- API tests for status codes, response schemas, authentication, and authorization.
- Database integration tests against the supported MySQL version before database releases; SQLite test doubles alone do not certify MySQL locking, collation, or migration behavior.
- Provider tests using fakes for deterministic routing and failure handling.
- Retrieval safety tests before external fetching ships, including private/loopback address rejection, redirects, oversized responses, unsupported content, timeouts, and malicious page content.
- UI checks for authentication flow, loading/error states, keyboard use, and session expiry.

### Release checks

- Fresh-install and upgrade procedure verified.
- Secrets and production endpoints checked outside source control.
- Backup restore exercised for durable user data.
- Monitoring and rollback plan ready.
- Product claims, licensing, privacy, and hosted-service terms reviewed.

## 8. Decision and risk tracking

Use short Architecture Decision Records under `docs/decisions/` for decisions that affect data formats, authentication policy, provider trust, retrieval safety, deployment, or compatibility. Each record should include context, decision, alternatives, consequences, and status.

Maintain a risk list in the relevant design doc or issue tracker. At minimum, review:

- public signup abuse and absent account recovery;
- provider key/base overrides and outbound endpoint trust;
- browser-local auth token storage;
- no database migration framework;
- external research safety and prompt injection;
- unmeasured scale/cost and deployment-specific DB connectivity;
- missing software license and operational/privacy policies.

## 9. Change and release management

- Keep changes small enough to review and revert.
- Never run destructive production migrations without tested backup and rollback/recovery steps.
- Prefer expand-migrate-contract database changes for rolling deployments.
- Publish user-facing changes with limitations, data impact, and required operator actions.
- Do not claim a capability is production-ready solely because unit tests pass; integration, security, operational, and product acceptance are separate gates.
