# Testing Strategy

This document outlines the current test coverage, fixtures, gaps, and a forward-looking plan to build a robust automated test suite enabling safe refactors and AI-driven development.

---
## Current State Overview
| Area | Observed Coverage | Notes |
|------|-------------------|-------|
| Placeholder Resolution | Yes (unit + integration variants) | Multiple tests validating simple & complex resolution paths |
| Notifications | Integration-style test present | Likely mocks or stubs external dependencies |
| Document Generation | Basic integration test(s) | Depth limited: does not cover signature flow or error branches |
| Auth & Keycloak OIDC | None | High-risk area without regression guard |
| Routes (General CRUD) | Minimal / None | Many endpoints untested |
| State Transitions | Indirect only | No explicit assertions on concurso estado/subestado evolution |
| PDF Signing Flow | None | Missing tests for multi-signature stamping positional logic |
| Google Drive Integration | Mocked (partial) | Real network avoided (good), but error handling not asserted |
| Alembic Migrations | Not covered | No migration smoke tests |

---
## Test Directory Structure (Present)
```
/tests
  conftest.py          # Pytest fixtures (app, db, maybe client)
  fixtures.py          # Domain object builders
  test_placeholder_resolver.py
  test_placeholder_resolver_simple.py
  test_placeholder_resolver_mocked.py
  test_integration_document_generator.py
  test_integration_notifications.py
```

---
## Fixture Layer
Likely fixtures include (infer from common Flask patterns):
- `app` / `client`: Flask test client with app context.
- `db_session` or similar: Transaction-scoped DB session rollback per test.
- Factory helpers in `fixtures.py` for Concurso, Tribunal members, Postulantes.

Improvement Ideas:
- Provide factory functions returning committed objects with sensible defaults.
- Use `FactoryBoy` or light custom builders for readability.
- Introduce fixture for mocked Drive client + Keycloak client.

---
## Testing Pyramid (Target Allocation)
| Level | Purpose | Target % of Tests |
|-------|---------|-------------------|
| Unit | Fast validation of pure functions / services | 55% |
| Service (light integration) | DB + service logic interactions | 25% |
| Full Integration (routes) | End-to-end request flows (mock externals) | 15% |
| Contract / External | Schema stability of Keycloak / Drive adapters | 5% |

---
## Recommended Coverage Additions
### 1. Authentication & Authorization
- Test login-required endpoints reject anonymous users (401/302).
- Role-based endpoints (admin routes) return 403 for insufficient roles.
- Token refresh logic & session persistence (if implemented) with mocked OIDC responses.

### 2. Concurso Lifecycle
- Generate document triggering estado/subestado updates → assert DB state.
- Multi-document scenario: ensure unique constraints enforced for `is_unique_per_concurso` templates.

### 3. Document Signature Flow
- Sequential signatures: verify stamp order, `firma_count`, final state FIRMADO.
- Attempt duplicate signature by same user → rejected.
- Upload external signed PDF path (alternative flow).

### 4. Error Path Testing
- Missing tribunal or considerandos when required → 400 with message.
- Drive creation failure raises handled error & DB rollback (DocumentoConcurso absent).

### 5. Placeholder Edge Cases
- Empty postulantes list → placeholders blank not 'None'.
- 100 postulantes performance (under time threshold, e.g., < 200ms locally).
- Legacy vs canonical parity test (iterate alias map).

### 6. Notifications
- Campaign creation persists correct metadata.
- Idempotent re-send prevention / duplicate avoidance (if logic exists or planned).

### 7. Migrations
Add smoke test:
```
pytest -q tests/test_migrations.py
```
Flow:
1. Create empty temp DB.
2. Run Alembic upgrade head.
3. Assert presence of critical tables.

### 8. API Contract Tests
- JSON shape for key public endpoints (e.g., list concursos) stable snapshot (use `pytest-approvaltests` or JSON schema).

---
## Tooling & Libraries
| Need | Library |
|------|---------|
| HTTP assertions | `pytest` + Flask client |
| Mock externals | `unittest.mock` / `responses` for HTTP Keycloak |
| Time control | `freezegun` for deterministic date placeholders |
| PDF inspection | `pypdf` to assert signature stamp text presence |
| Performance | `pytest-benchmark` for hot paths |

---
## Suggested Directory Refactor
```
/tests
  /unit
    test_placeholder_*.py
    test_text_formatting.py
    test_pdf_utils.py
  /services
    test_document_generation_service.py
    test_placeholder_service.py
  /integration
    test_routes_concursos.py
    test_routes_auth.py
    test_signature_flow.py
  /migrations
    test_migrations.py
  /contracts
    test_keycloak_admin_contract.py
```

---
## Example: Document Generation Service Unit Test (Future)
```python
def test_generation_applies_template_rules(mocker, concurso_factory, template_factory, service):
    concurso = concurso_factory(estado_actual="INICIO")
    template = template_factory(estado_al_generar_borrador="APERTURA")
    mock_drive = mocker.patch.object(service.drive, 'create_from_template', return_value=("file123", "https://..."))

    link = service.generate(concurso.id, template.document_type_key)

    assert link.startswith("https://")
    assert concurso.estado_actual == "APERTURA"
    mock_drive.assert_called_once()
```

---
## CI Pipeline Recommendations
| Step | Purpose |
|------|---------|
| Lint (flake8/ruff) | Style & quick error detection |
| Type Check (mypy optional) | Interface stability (gradual) |
| Unit Tests | Fast feedback (<60s) |
| Integration Tests | Extended (>60s) – maybe parallelize |
| Coverage Report | Enforce threshold (start 55%, grow to 80%) |

Add coverage flags in `pytest.ini`:
```
[pytest]
addopts = --maxfail=1 -q --durations=10 --cov=app --cov-report=term-missing
```

---
## Metrics & Quality Gates
| Metric | Initial Target | Rationale |
|--------|----------------|-----------|
| Statement Coverage | 55% | Baseline after adding core service tests |
| Critical Modules Coverage (generation, placeholder) | 85% | High-risk refactor areas |
| Avg Unit Test Runtime | < 1s | Fast loop |
| Flaky Test Rate | 0 | Deterministic fixtures |

---
## Incremental Adoption Plan
1. Introduce service abstraction (document generation) → write focused tests.
2. Backfill placeholder edge tests (dates, empty lists, tribunals missing).
3. Add signature flow integration with fake PDF.
4. Add auth/role tests with mocked Keycloak tokens.
5. Add migration smoke test.
6. Implement template placeholder audit command; test it.
7. Raise coverage thresholds gradually.

---
## Open Gaps / TODO
- No deterministic time control in tests (add Freezegun usage).
- PDF stamping not validated anywhere.
- Error handling surfaces generic messages; could assert typed custom exceptions once implemented.
- Missing load testing / concurrency test (optional; low priority currently).

Linked Docs: `DOCUMENT_GENERATION.md`, `PLACEHOLDER_SYSTEM.md`, `REFACTORING_GUIDE.md`.
