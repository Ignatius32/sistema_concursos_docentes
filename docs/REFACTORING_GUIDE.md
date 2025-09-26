# Refactoring & Modularization Guide

This guide provides a prioritized roadmap to evolve the current Flask application into a more modular, testable, and maintainable system—optimized for incremental AI-driven contributions.

---
## Guiding Principles
1. Inversion of dependencies: Routes depend on services, services depend on repositories / integrations.
2. Pure core domain where possible (business rules independent of Flask / Google / Keycloak).
3. Explicit boundaries for external systems (Keycloak, Google Drive) with adapter interfaces.
4. Small, composable units: each function does one thing, minimized side effects.
5. Progressive refactor: Always maintain green tests; introduce abstractions before rewiring.

---
## Current Pain Points (Summary)
| Area | Issue | Impact |
|------|-------|--------|
| Routes | Heavy business logic inline | Hard to test, duplicate patterns |
| Document Generation | Procedural script style | Hard to extend (signatures, multi-format) |
| Placeholder Resolver | Monolithic data assembly | Difficult to plug new data sources |
| State Management | Estado/subestado mutation spread | Risk of inconsistent transitions |
| Integrations | Direct use of external libs in routes | Hard to mock / test failure modes |
| Error Handling | Mixed return types (bool, msg) | Ambiguous control flow |
| Logging | Sparse contextual logs | Low observability |
| Config Proliferation | Magic strings for template keys | Prone to typos |

---
## Target Layered Architecture
```
app/
  domain/                 # Entities (dataclasses), pure logic helpers
  repositories/           # DB access abstractions around SQLAlchemy
  services/               # Orchestrate repositories + integrations
  integrations/           # Keycloak, GoogleDrive, PDF stamping
  api/                    # Flask blueprints (thin) + request/response schemas
  workflows/              # Higher-level processes (signature flow, sync jobs)
```

---
## Phase Roadmap
| Phase | Goal | Key Deliverables |
|-------|------|------------------|
| 1 | Introduce service layer skeleton | DocumentGenerationService, PlaceholderService |
| 2 | Repository abstraction | ConcursoRepository, DocumentoRepository |
| 3 | State management centralization | StateTransitionService + history emitter |
| 4 | Error model standardization | DomainError hierarchy + error handler blueprint |
| 5 | Logging & metrics | Structured logging (JSON) + event counters |
| 6 | Auth boundary | AuthService isolating Keycloak roles, token refresh |
| 7 | Background tasks | Scheduler or celery-ready abstraction (if needed) |
| 8 | Full route slimming | All blueprints call services only |
| 9 | Legacy cleanup | Remove alias placeholders, deprecated keys |

---
## Service Layer Introductions
### DocumentGenerationService (Phase 1)
Responsibilities:
- Validate preconditions (tribunal, considerandos).
- Assemble placeholders via PlaceholderService.
- Delegate to DriveAdapter.
- Persist Documento + apply template-driven state transitions.

### PlaceholderService
- Provide canonical & legacy placeholder dict.
- Registry of dynamic providers.
- Audit capability for template placeholder usage.

### StateTransitionService
- Apply template rule sets (draft / signed events).
- Manage subestado list operations atomically.
- Emit history record.

---
## Repository Pattern
Example:
```python
class ConcursoRepository:
    def __init__(self, session):
        self.session = session
    def get(self, id: int, lock=False):
        q = self.session.query(Concurso).filter_by(id=id)
        if lock:
            q = q.with_for_update()
        return q.one()
    def add_document(self, concurso, template_key, file_id, link):
        doc = DocumentoConcurso(...)
        self.session.add(doc)
        return doc
```
Benefits: Replace direct SQLAlchemy calls in services; easier mocking.

---
## Error Handling Standardization
Define base domain exceptions:
```
class DomainError(Exception):
    code = "domain_error"
class PreconditionError(DomainError):
    code = "precondition_failed"
class NotFoundError(DomainError):
    code = "not_found"
```
Global error handler blueprint returns JSON:
```
{ "error": { "code": "precondition_failed", "message": "Tribunal required" } }
```

---
## Logging & Observability
Adopt structured logging (e.g., stdlib + JSON formatter).
Minimum fields per event:
- `event`, `concurso_id`, `user_id`, `elapsed_ms`, `success`, `error_code`.
Add timing decorator for service public methods.

Metrics (Prometheus-ready design):
- Counter: `documents_generated_total{template_key=..., success=...}`
- Histogram: `document_generation_latency_seconds`.

---
## Configuration & Constants
Introduce `constants.py` for:
- Template keys (Enum class)
- Estados / Subestados (Enum)
- Roles (Enum / Literal types)

Benefits: Autocomplete + mypy validation.

---
## PDF Signing Workflow Refactor
Current: Stamps applied sequentially with positional logic inline.
Refactor Plan:
1. `SignaturePlan` object calculates bounding boxes for each signer.
2. `PdfStampingService` receives plan + signer metadata.
3. Separate persistence (DocumentoConcurso update) from stamping.

---
## Transaction Management
Ensure atomicity on multi-resource operations (DB + Drive):
Pattern:
1. Prepare data.
2. Call Drive create.
3. On success, commit DB.
4. On failure, attempt Drive cleanup.
Consider outbox pattern if introducing async notifications later.

---
## Testing Transformation
- Write unit tests for new services (no Flask client).
- Convert existing integration tests to use service layer when possible.
- Add contract tests for DriveAdapter (mock verifying method signature & data shape).

---
## Incremental Refactor Script (Example Task List)
1. Create `services/document_generation_service.py` (pure orchestrator) + tests.
2. Move placeholder logic into `services/placeholder_service.py`.
3. Replace route calls to old functions with service calls (one blueprint at a time).
4. Introduce repositories; update services to use them.
5. Add domain exceptions + global error handler.
6. Add structured logging & metrics wrapper.
7. Extract signing logic to `services/signature_service.py`.
8. Remove deprecated direct Drive calls from routes.
9. Clean alias placeholders + update templates.

---
## Risk Mitigation
| Risk | Mitigation |
|------|------------|
| Behavior drift during extraction | High-fidelity integration tests before refactor |
| Partial rollout confusion | Feature flags / environment variable gating |
| Performance regression | Add simple latency benchmarks pre/post |
| Developer onboarding complexity | Maintain updated `ARCHITECTURE_OVERVIEW.md` diffs |

---
## Code Quality Enhancements
- Adopt `ruff` for lint + import sorting.
- Optional: Introduce gradual mypy (start with service modules).
- Pre-commit hooks for formatting (black or ruff format) & security (bandit).

---
## Data Model Improvements
| Issue | Proposal |
|-------|---------|
| `subestado` JSON array without provenance | Use associative table `ConcursoSubestadoHistory` |
| Template behavior flags proliferation | Normalize into related tables or JSON schema validated column |
| Sparse document signing metadata | Introduce `DocumentoFirma` with ordering + coordinates |

---
## Long-Term Evolutions
| Idea | Benefit |
|------|--------|
| Event sourcing for state changes | Auditable transitions |
| Async task queue (RQ/Celery) | Offload slow Drive/PDF operations |
| GraphQL read API | Flexible data retrieval for UIs |
| Frontend decoupling (React/Vue) | Improved UX & component reuse |

---
## Done Definition for Each Extraction Step
- All previous tests green.
- New unit tests for extracted service (>=80% coverage of that module).
- Routes only orchestrate HTTP concerns (parse, call service, serialize).
- No direct external API calls in routes.

---
## Tracking Progress
Maintain `TECH_DEBT_TODO.md` with checkboxes per phase deliverable (AI agent updatable).

Linked Docs: `ARCHITECTURE_OVERVIEW.md`, `DOCUMENT_GENERATION.md`, `SERVICES.md`, `TESTING.md`.
