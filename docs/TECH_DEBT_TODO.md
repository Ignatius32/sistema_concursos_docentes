# Technical Debt & Improvement Backlog

This backlog enumerates known technical debt items, architectural gaps, and enhancement opportunities. AI agents and human contributors should keep this file updated as changes land.

---
## Legend
| Symbol | Meaning |
|--------|---------|
| [ ] | Not started |
| [~] | In progress |
| [x] | Completed |
| (!) | High priority / risk |

---
## High Priority
- [ ] (!) Centralize state/subestado transitions in StateTransitionService.
- [ ] (!) Introduce DocumentGenerationService & PlaceholderService abstractions.
- [ ] (!) Replace tuple error returns with DomainError exceptions + error handler.
- [ ] (!) Add structured logging (JSON) + request correlation id.
- [ ] (!) Add comprehensive auth & role tests (admin vs tribunal vs public).
- [ ] (!) Repository layer to remove direct SQLAlchemy usage in routes.

---
## Medium Priority
- [ ] Implement template placeholder audit script.
- [ ] Migrate legacy placeholder aliases out of resolver (post template update).
- [ ] Add migration smoke test (Alembic upgrade head).
- [ ] Refactor PDF stamping into PdfStampingService with deterministic layout.
- [ ] Extract signature flow to SignatureService.
- [ ] Add metrics counters/histograms (Prometheus instrumentation hooks).
- [ ] Introduce constants/enums for estados, subestados, roles, template keys.
- [ ] Adopt ruff + pre-commit hooks.
- [ ] Write performance benchmark for placeholder resolution (N=200 postulantes).
- [ ] Consolidate scattered Google Drive operations into DriveAdapter interface.
- [ ] Normalize template configuration flags (schema validation / pydantic model or JSONSchema check).

---
## Low Priority
- [ ] Evaluate async job queue for bulk generation or large sync tasks.
- [ ] Investigate event sourcing for concurso state history.
- [ ] Jinja2 formatting filters for inline transformations in templates.
- [ ] Localization framework for multi-language documents.
- [ ] GraphQL read API layer exploration.
- [ ] Frontend decoupling roadmap (SPA migration feasibility study).

---
## Testing Debt
- [ ] Signature flow integration test (multi-signer sequence).
- [ ] Error path tests for Drive failure rollback.
- [ ] Placeholder legacy alias deprecation test.
- [ ] Concurso unique document type enforcement test.
- [ ] Public/tribunal visibility rule tests.

---
## Data Model / Persistence
- [ ] Replace `subestado` JSON array with normalized association table.
- [ ] Add provenance for subestado additions (history table restructuring).
- [ ] Expand FirmaDocumento model with coordinates & ordering metadata.
- [ ] Archive / soft delete pattern (deleted_at columns) for logical removals.

---
## Observability
- [ ] Introduce correlation id middleware (X-Request-ID header generation).
- [ ] Add latency logging for Drive and Keycloak calls.
- [ ] Error budget dashboard (failure rate of document generation/signatures).

---
## Security
- [ ] Centralize RBAC mapping (role -> permissions) outside route decorators.
- [ ] Periodic Keycloak sync diff report (users not in local DB, stale roles).
- [ ] Audit log for administrative actions (document deletion, force state change).

---
## Dev Experience
- [ ] Add `makefile` or task runner (format, lint, test targets).
- [ ] Provide sample env file `.env.example`.
- [ ] Include local Docker Compose for DB + Keycloak test harness.
- [ ] Add quickstart script performing initial migrations + seed.

---
## Performance
- [ ] Cache placeholder resolution per request.
- [ ] Batch tribunal + postulantes queries with eager loading.
- [ ] Optimize PDF stamping (avoid repeated full file rewrite if possible).

---
## Documentation Upkeep
- [ ] Update MODELS.md after each migration (automated check in CI).
- [ ] Auto-generate ROUTES.md via reflection script.
- [ ] Add CHANGELOG.md for notable changes.

---
## Completed Items (Move here when done)
- [x] (Example) Initial documentation suite (architecture, models, services, integrations, generation, placeholders, testing, refactor, AI guide).

---
## Contribution Workflow for Debt Items
1. Select item and create branch name: `debt/<slug>`.
2. Add or expand tests protecting current behavior.
3. Implement change behind feature flag if risky.
4. Update this file: mark item [x].
5. Link PR referencing item line.

Linked Docs: `REFACTORING_GUIDE.md`, `TESTING.md`, `AI_CONTRIBUTION_GUIDE.md`, `DOCUMENT_GENERATION.md`.
