# Architecture Overview

This document provides a comprehensive architectural overview of the Sistema de Concursos Docentes Flask application to enable future feature development and systematic refactoring by an AI-assisted engineering workflow.

## High-Level Domain Summary
The system manages university academic staff selection (concursos docentes) including:
- Contest lifecycle (creation, document workflow, states & subestados)
- Tribunal (committee) member management, notification & access provisioning
- Applicant (postulante) registration and document collection
- Document template driven generation (Google Docs) + signing workflow (multi-signature stamping logic via Drive + PDF stamping utilities)
- Notification campaigns with dynamic placeholder resolution
- Sorteo (random topic draw) for evaluation phase
- Migration away from legacy Google Script APIs toward local persisted reference data (considerandos and departamento heads)
- Keycloak-based federated authentication + role/permission model (admin vs tribunal)

## Layered Structure
```
app/
  __init__.py        -> App factory, extension init, blueprint registration, login + context processors
  models/            -> SQLAlchemy ORM models (single file `models.py` currently; candidate for splitting)
  routes/            -> Flask Blueprints: auth, concursos, tribunal, postulantes, notifications, admin_* APIs, public, api
  services/          -> Business services: placeholder resolver, Keycloak sync, password reset, schedulers
  integrations/      -> External systems: Keycloak OIDC + Admin API, Google Drive macro API wrapper
  document_generation/ -> Core document generator orchestrating templates + placeholders
  helpers/           -> Helper utilities (api_services, text_formatting, pdf_utils, google_drive_loading)
  templates/         -> Jinja templates (UI + partials)
  static/            -> JS, CSS, images
```

## Runtime Components
- Flask app with Application Factory pattern (`create_app`) and post-create data bootstrap (`init_app_data`) ensuring admin and reference data existence.
- Authentication: Keycloak OIDC (Authlib) session driven plus direct ROPC fallback for tribunal/admin convenience.
- Authorization: Decorators (`admin_required`, `keycloak_login_required`) + role extraction from tokens.
- Background / Scheduled Tasks: `sync_scheduler` (periodic synchronization with Keycloak—details to be expanded in services doc).
- External Integrations:
  - Google Drive Apps Script endpoint (single API endpoint parameterized by `action`) performing: folder creation, uploads, overwrites, email dispatch, (deprecated) PDF signing.
  - Keycloak Admin REST via python-keycloak for user provisioning and password / role management.

## Data Model Highlights
(See `MODELS.md` for exhaustive details). Key functional aggregates:
- Concurso: central aggregate root; holds structural metadata, folder IDs, dynamic estado/subestado, relationships to tribunal, postulantes, documentos, sustanciacion, historial.
- DocumentTemplateConfig: dynamic configuration enabling visibility rules, role-based capabilities, and automatic estado/subestado transitions.
- DocumentoConcurso + FirmaDocumento: document lifecycle & signatures.
- NotificationCampaign + NotificationLog: outbound messaging with deterministic reconstruction of sent payloads.
- Sustanciacion + TemaSetTribunal + SorteoConfig: topic proposal + draw workflow.
- Considerandos & DepartamentoHead: localized cache of formerly remote structured data.

## State & Subestado Mechanism
Documents can trigger concurso state transitions:
- Template config fields:
  - `estado_al_generar_borrador`, `subestado_al_generar_borrador`
  - `estado_al_subir_firmado`, `subestado_al_subir_firmado`
- Subestado is an accumulating JSON array (historical markers) with automatic reversal on document deletion (implemented in route/service logic—confirm when refactoring).

## Placeholder Resolution System
Central service (`placeholder_resolver.get_core_placeholders`) synthesizes dynamic text tokens spanning:
- Concurso structural fields
- Tribunal composition (role + claustro segmentation)
- Postulantes lists
- Sustanciacion scheduling & topics (including formatted variants)
- Department head metadata
- Notification / recipient personalization (persona-specific placeholders)
Used by: document generation, notification assembly, email flows.

## Document Generation Flow
1. UI/Admin triggers generation with selected `DocumentTemplateConfig`.
2. `document_generator.generar_documento_desde_template`:
   - Loads template config
   - Gathers base + supplemental placeholders
   - (Optionally) merges considerandos builder output
   - Calls Google Drive API `createDocFromTemplate` (template ID == Google Doc ID)
   - Persists `DocumentoConcurso` (BORRADOR) with `borrador_file_id`
   - Applies estado/subestado template rules + logs HistorialEstado

Signing / progression path (overview):
- PENDIENTE DE FIRMA state when sent for signature
- Individual tribunal member signing updates `firma_count` + new stamped PDF produced (Python stamping path recommended; remote stamping deprecated)

## Authentication & Identity Synchronization
- Login: OIDC redirect or direct password Resource Owner flow (`direct_authenticate`).
- Persona synchronization orchestrated in `auth.sync_keycloak_user_with_persona` and service `KeycloakPersonaSyncService`:
  - Creates / links Persona rows with Keycloak users granted tribunal/admin roles.
  - Periodic reconciliation of roles, email, attributes.
  - Separation of authoritative fields (Keycloak for identity; local for domain specifics / assignments).

## Email & Notification Strategy
Two parallel channels:
1. Google Drive macro endpoint `sendEmail` (primary) used for:
   - Password reset / account setup (token emails) via `PasswordResetService`.
   - Login reminders.
   - Notification campaigns (where implemented—campaign service logic in routes/notifications).
2. Keycloak execute-actions emails (fallback / alternative for password setup) through admin client.

Templates leverage inline HTML with placeholder injection pre-send. Attachments supported via Drive file IDs.

## Sorteo (Topic Lottery)
- Configuration persisted in `SorteoConfig` by concurso tipo + categoría.
- Frontend: asynchronous modal-driven UX (`sorteo-manager.js`) orchestrating progress & result display.
- Backend: endpoint validates consolidation + randomly samples topics (`random.sample`). Results persisted to Sustanciacion.

## Testing Strategy Overview
- Unit-like tests for placeholder substitution (pure functions).
- Mocked integration tests for document generator & notifications ensuring placeholder mapping correctness.
- (Gap) Missing: end-to-end tests for route auth flows, Google Drive interactions (should mock), Keycloak sync edge cases, state transition regression suite.

## Identified Architectural Risks / Debt (See TECH_DEBT_TODO.md for actions)
- Monolithic `models.py` file -> high cognitive load & merge conflicts risk.
- Some duplicated logic mapping placeholders to legacy template variable names (can centralize adapter layer).
- Direct prints & mixed logging strategies (standardize on structured logging).
- Mixed responsibility in some routes (business rules in route functions instead of service layer abstractions).
- Lack of transactional boundaries around multi-step Drive + DB operations (risk of partial failure inconsistency).
- Sparse test coverage for estado/subestado reversal logic and signature workflow.

## Extension & Refactoring Guidelines
- Introduce a domain service layer boundary: concursos, documents, notifications, identity.
- Extract model modules per bounded context (e.g., `models/concurso.py`, `models/notification.py`).
- Create repository or query helper abstractions for common joins / filtering.
- Standardize error handling -> custom exceptions + error blueprint.
- Add Pydantic (or dataclasses) for DTOs between layers (especially for notification & placeholder results).
- Event sourcing / outbox pattern candidate for notification + state changes (future scalability).

## Data Flow Diagram (Conceptual)
```
User Action -> Flask Route -> Service Layer -> ORM (DB) & Integrations (Drive/Keycloak)
                                                |-> Placeholder Resolver (aggregates dynamic text)
                                                |-> Document Generation -> Drive Doc -> DB record
                                                |-> Notification Campaign -> Email API
                                                |-> State/Subestado Mutations -> HistorialEstado
```

## Security Considerations
- Keycloak tokens stored in session; ensure secure cookie & HTTPS in production (Apache front).
- Password reset tokens: custom HMAC-like signature with shared secret; consider rotating & lengthening secret + adding token replay storage if elevating security.
- Google Drive macro endpoint: single shared `GOOGLE_DRIVE_SECURE_TOKEN` (improve with per-action signatures / mTLS if risk increases).
- Attachment & URL construction must validate IDs to avoid injection of external links (sanitization pass recommended).

## Observability Recommendations
- Add structured logging (JSON) for: document generation events, notification dispatch, state changes, auth events, Keycloak sync operations.
- Introduce request ID correlation middleware.
- Add metrics: count documents per state, average generation latency, email success/failure counts, sync divergence counts.

## Deployment Topology
- Apache mod_wsgi fronting Flask app (`wsgi.py`) with APPLICATION_ROOT prefix `/selecciones-docentes`.
- Single-process assumption—evaluate scaling: externalize session storage + move to gunicorn+systemd behind Apache or nginx if concurrency grows.

## Next Documents
See also:
- `SETUP_AND_DEPLOYMENT.md`
- `MODELS.md`
- `ROUTES.md`
- `SERVICES.md`
- `INTEGRATIONS.md`
- `DOCUMENT_GENERATION.md`
- `PLACEHOLDER_SYSTEM.md`
- `TESTING.md`
- `REFACTORING_GUIDE.md`
- `AI_CONTRIBUTION_GUIDE.md`
- `TECH_DEBT_TODO.md`

---
This overview will evolve as refactors proceed; keep it authoritative by updating when introducing or deprecating subsystems.
