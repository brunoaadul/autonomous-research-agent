# Repository Guide for Coding Agents

## Mission

Build Crokuta into a trustworthy research workspace that can be operated as a hosted service or self-hosted from this repository. Implement only behavior supported by approved requirements. The current research endpoint produces a preliminary framework; do not describe it as source-backed or autonomous web research.

## Read before changing code

1. [Product requirements](docs/requirements.md) define product scope and acceptance criteria.
2. [SDLC and delivery objectives](docs/SDLC.md) define milestones, quality gates, and release expectations.
3. [Architecture](docs/architecture.md), [system design](docs/system-design.md), and [scaling](docs/scaling.md) describe the current design and planned evolution.
4. Inspect the implementation and relevant tests. Documentation describes intent; code and tests establish current behavior.

When documents disagree, do not silently make a large product or architecture decision. Record the discrepancy and ask for clarification when it changes user-visible behavior, security, data ownership, or deployment commitments.

## Current implementation facts

- FastAPI serves the browser workspace and JSON APIs from one origin.
- Authentication uses MySQL via SQLAlchemy and PyMySQL. New signups provide full name, phone number, country, email, and password. Public signup is enabled.
- Research briefs are produced by deterministic template logic in `app/research.py`; external sources are not fetched.
- Research reports and user/assistant chat messages are stored in owner-scoped MySQL conversations. Users can list, reopen, and permanently delete their conversations.
- Follow-up chat is routed through LiteLLM. The browser stores auth tokens locally; conversation history is retrieved from the API.
- The research engine is not yet a multi-step or source-backed research workflow.
- `.env.example` is illustrative. Never put real credentials in source, tests, docs, or browser assets.

## Engineering rules

- Make small, focused changes and preserve existing behavior unless a requirement explicitly changes it.
- Keep FastAPI request/response shapes typed with Pydantic schemas. Validate at the API boundary.
- Keep provider-specific behavior inside the LLM gateway. Keep research-domain behavior separate from HTTP and provider integrations.
- For any external retrieval feature, treat URLs and fetched content as untrusted. Enforce SSRF protections, timeouts, response-size/content-type limits, and bounded concurrency before release.
- Enforce authentication and ownership in the API, not only in the browser. Do not rely on local storage for authorization.
- Keep conversation ownership checks on every read, message, and delete operation. Deleting a conversation must delete its messages in the same database transaction.
- Keep secrets server-side. Do not log passwords, tokens, API keys, complete private prompts, or unnecessary personal data.
- Surface failures explicitly. Do not convert provider, database, or retrieval failures into success-shaped responses.
- Use the existing dependency manifest and test framework. Add dependencies only when required by the implementation.
- Update the relevant requirements and design documentation when behavior, schemas, storage, deployment, or operational expectations change.
- Do not add numeric service-level objectives without measurements and an approved target.

## Validation

Run the smallest relevant test selection during iteration, then the full suite before completing a cross-cutting change:

```text
python -m pytest -q
```

Use the repository's active virtual environment; on Windows, the checked-in setup uses `.venv\Scripts\python.exe`.

For changes involving authentication, database persistence, API schemas, research, or provider routing, add focused tests for successful and failing behavior. Document external integration checks that could not be run (for example, tests requiring a live MySQL server or provider account).

## Change completion checklist

- The change maps to an approved requirement or records a necessary decision.
- Tests cover new behavior and relevant failure paths.
- Protected resources remain protected and user ownership is enforced where applicable.
- User-facing errors and docs are consistent with actual behavior.
- No generated artifacts, secrets, or unrelated worktree changes are included.
- Remaining risks, operational prerequisites, and validation gaps are stated clearly.
