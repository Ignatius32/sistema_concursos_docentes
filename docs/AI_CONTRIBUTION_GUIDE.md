# AI Contribution Guide

This guide instructs an AI coding agent on how to safely extend and refactor the project while preserving behavior, auditability, and maintainability.

---
## Operational Principles
1. Small, Reviewable Changes: Prefer incremental PRs (single concern) over large rewrites.
2. Tests First (When Refactoring): Add/expand tests locking current behavior before modifying logic.
3. Idempotent Scripts: Any data / migration script must be safe to re-run.
4. Deterministic Output: Avoid introducing non-determinism (timestamps, ordering) without explicit formatting.
5. Observability Expansion: When adding features, enhance logging/metrics hooks.

---
## Safe Workflow Loop
```
[Detect Need] -> [Create/Update Tests] -> [Introduce Abstraction] -> [Migrate Callers] -> [Remove Old Code] -> [Run Full Test Suite + Lint] -> [Document Delta]
```

---
## File Classification Heuristics
| Folder | Nature | AI Guidance |
|--------|-------|-------------|
| `app/routes` | HTTP endpoints | Keep thin; move heavy logic outward |
| `app/services` | Orchestration logic | Central point for business processes |
| `app/integrations` | External adapters | Avoid embedding business decisions |
| `app/models` | Persistence layer | Do not add logic-heavy methods; keep slim |
| `scripts/*.py` | One-off utilities | Consider relocating repeatable logic to services |
| `tests` | Validation suite | Expand to cover new modules immediately |

---
## When Adding a New Feature
Checklist:
- Define acceptance criteria in PR description.
- Add/update domain/service tests (unit) + route integration test.
- Introduce constants/enums for new estados or template keys (avoid string literals in multiple places).
- Provide doc section updates (ARCHITECTURE_OVERVIEW / relevant subsystem doc).
- Ensure placeholder additions documented in `PLACEHOLDER_SYSTEM.md`.

---
## Refactoring Decision Tree
| Situation | Action |
|-----------|--------|
| Route contains branching + data assembly | Extract service method |
| Mixed external + DB logic | Introduce adapter + repository split |
| Repeated placeholder construction fragment | Centralize in PlaceholderService |
| Direct Keycloak / Drive call in multiple spots | Create Integration method and reuse |
| Function > 40 lines or > 3 responsibilities | Decompose into private helpers |

---
## Logging & Metrics Rules
- For each new service public method, log start & completion with timing.
- On recoverable error (validation) -> structured log level=WARNING.
- On unexpected exception -> structured log level=ERROR + stack trace.
- Emit counters for repetitive operations (documents generated, placeholders resolved, signatures added).

---
## Error Handling
Use domain exceptions (see `REFACTORING_GUIDE.md`). Avoid returning `(False, "msg")` tuples from new code.
Propagate clear semantic errors to a centralized error handler.

---
## Placeholder Extensions
When adding a placeholder:
1. Add generation logic in PlaceholderService provider.
2. Add unit test verifying presence + formatting.
3. Update `PLACEHOLDER_SYSTEM.md` with description.
4. If legacy compatibility needed, add alias & mark for later removal.

---
## Document Generation Modifications
- Never mutate concurso state in multiple places; use StateTransitionService (once established).
- If adding new document type: update constants, template config, and tests ensuring uniqueness rules.

---
## Signature Flow Changes
- Maintain invariant: `firma_count` equals number of FirmaDocumento records.
- Ensure stamping deterministic vertical ordering.
- If bounding box algorithm changes, add regression test on produced coordinates.

---
## Security & Auth
- Validate role/permission at route boundary ONLY; services receive already-authorized context.
- When adding roles: centralize definitions and update tests denying access to unauthorized roles.

---
## Database Changes Procedure
1. Modify SQLAlchemy model.
2. Generate Alembic revision (manual step outside AI scope here unless tooling added).
3. Write migration upgrade/downgrade with reversible operations.
4. Add migration smoke test updating empty DB head.
5. Update `MODELS.md` diff note.

---
## Performance Guardrails
| Action | Guard |
|--------|-------|
| New query loop | Ensure O(n) without nested DB queries (use eager loading) |
| Added placeholder provider | Cache heavy calls inside request scope |
| Bulk generation feature | Consider asynchronous queue |

---
## Code Review Self-Checklist (AI)
- Are new functions < 30 lines? If not, consider splitting.
- Are all new imports used? (lint clean)
- Do tests assert both success and failure modes?
- Are side effects (DB writes, external API) isolated & mockable?
- Are docstrings / comments updated to reflect reality?

---
## Anti-Patterns to Avoid
| Anti-Pattern | Replacement |
|--------------|------------|
| Route performing complex joins + external API | Service + repository + adapter |
| Silent except: pass | Explicit exception handling + logging |
| Hard-coded state strings | Enum / constant reference |
| Copy-pasted placeholder assembly | Shared provider / helper |
| Boolean return for error | Raise structured DomainError |

---
## Communication & Documentation
Each significant change should:
- Update relevant doc(s) with rationale (why) + new structure (what) + usage (how).
- Add CHANGELOG entry (future enhancement to create file if absent).

---
## Tooling Roadmap for AI Enablement
| Tool | Purpose |
|------|---------|
| Script: placeholder_audit.py | Detect unknown placeholders in templates |
| Script: state_transition_report.py | Summarize frequency of estado changes |
| Test Data Builders | Simplify creation of domain objects |
| Logging Formatter | Enforce structured JSON logs |

---
## Escalation Policy
If uncertain about legacy behavior:
1. Generate characterization test (captures current output).
2. Run tests to confirm baseline.
3. Proceed with refactor ensuring test stays green.

---
Linked Docs: `REFACTORING_GUIDE.md`, `DOCUMENT_GENERATION.md`, `PLACEHOLDER_SYSTEM.md`, `TESTING.md`.
