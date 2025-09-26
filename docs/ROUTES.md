# Routes & Endpoints

This document catalogs all Blueprints and their primary endpoints, including purpose, auth requirements, and key side-effects. Use it when extending APIs, adding tests, or enforcing consistent authorization.

> NOTE: Exact parameter names inferred from code; when adding new endpoints consider producing an OpenAPI spec.

## Legend
- Auth: `Public`, `Keycloak(Login)`, `Admin` (requires admin role), `Tribunal` (future specialization), `Mixed` (dynamic branching)
- Side Effects: DB write, Drive API, Keycloak Admin API, Email Send, State Change

---
## Blueprint: auth (`/auth`)
| Method & Path | Auth | Purpose | Side Effects |
|---------------|------|---------|--------------|
| GET/POST `/auth/login` | Public | Login form + direct ROPC or trigger OIDC | Session mutation, possible persona sync |
| GET `/auth/keycloak-login` | Public | Initiate OIDC redirect | None |
| GET `/auth/callback` | Public (OIDC redirect) | Handle OIDC exchange, persona sync | DB write (Persona), session |
| GET `/auth/logout` | Authenticated | Clear session (local) optionally Keycloak logout | Session clear |
| GET `/auth/debug` | Admin (implicit) | Diagnostic HTML block for roles/session | None |
| GET `/auth/clear-session` | Authenticated | Force local session clear | Session clear |
| GET/POST `/auth/reset-password` | Public | Start password reset (Drive-based email) | Email send, Keycloak user lookup |

Persona sync logic is embedded in auth routes; consider moving to service-only calls.

---
## Blueprint: api (`/api`)
| Path | Method | Auth | Purpose | Side Effects |
|------|--------|------|---------|--------------|
| `/api/programa/<id_materia>` | GET | Public | Fetch single programa metadata via helper service | External API call |
| `/api/programas-bulk` | POST | Public | Bulk fetch multiple programas | External API call |
| `/api/buscar-personas` | GET | Admin | Search personas by partial | DB read |

---
## Blueprint: admin_templates (`/admin/templates`)
| Path | Method(s) | Auth | Purpose |
|------|-----------|------|---------|
| `/` | GET | Admin | List all template configs |
| `/export` | GET | Admin | Download JSON export |
| `/import` | GET/POST | Admin | Upload JSON + bulk insert/update |
| `/nuevo` | GET/POST | Admin | Create template |
| `/editar/<id>` | GET/POST | Admin | Edit template |
| `/eliminar/<id>` | POST | Admin | Delete template |

Side Effects: DB modifications, flash messaging.

---
## Blueprint: admin_api_data (`/admin/api-data`)
Manages local cached data replacing legacy Google Script endpoints.

| Path | Method(s) | Auth | Purpose | Side Effects |
|------|-----------|------|---------|--------------|
| `/considerandos` | GET | Admin | List active considerandos | DB read |
| `/considerandos/new` | GET/POST | Admin | Create new considerando | DB write |
| `/considerandos/<id>/edit` | GET/POST | Admin | Update considerando | DB write |
| `/considerandos/<id>/delete` | POST | Admin | Soft delete | DB write |
| `/departamento-heads` | GET | Admin | List heads | DB read |
| `/departamento-heads/new` | GET/POST | Admin | Create head | DB write |
| `/departamento-heads/<id>/edit` | GET/POST | Admin | Update head | DB write |
| `/departamento-heads/<id>/delete` | POST | Admin | Soft delete | DB write |
| `/api/considerandos` | GET | Admin | JSON list considerandos | DB read |
| `/api/departamento-heads` | GET | Admin | JSON list heads | DB read |
| `/placeholders` | GET | Admin | Static placeholder documentation view | None |

---
## Blueprint: postulantes (`/postulantes`)
Administration of applicants per concurso.

| Path | Method(s) | Auth | Purpose | Side Effects |
|------|-----------|------|---------|--------------|
| `/concurso/<concurso_id>` | GET | Admin | View applicants list | DB read |
| `/concurso/<concurso_id>/agregar` | GET/POST | Admin | Add applicant | DB + Drive folder create |
| `/<postulante_id>` | GET | Admin | View applicant detail | DB read |
| `/<postulante_id>/editar` | GET/POST | Admin | Update applicant | DB write, optional Drive rename |
| `/<postulante_id>/eliminar` | POST | Admin | Delete applicant | DB + Drive delete |
| `/<postulante_id>/documentos/agregar` | GET/POST | Admin | Upload/convert (image->PDF) | Drive upload, DB write |
| `/documentos/<documento_id>/eliminar` | POST | Admin | Remove individual document | Drive delete, DB write |
| `/<postulante_id>/impugnar` | GET/POST | Admin | Create impugnation | DB write |

---
## Blueprint: tribunal (`/tribunal`)
Large file (was modularized partially). Handles tribunal portal operations: document access, signing, notifications, topic proposals, etc. (Exact endpoints not fully enumerated here; a future extraction should auto-generate documentation).

Recommended Action: generate a route index programmatically to populate missing table here.

---
## Blueprint: concursos (`/concursos`)
(Original file not shown in provided extracts; typically handles listing, creation, editing, document actions, sorteo trigger, state transitions.)

Key functional clusters:
- CRUD of Concurso
- Folder creation (Drive)
- Document generation triggers (calls document_generator)
- Estado/Subestado management
- Sorteo endpoints (`/realizar-sorteo` etc.)

Add precise path inventory during refactor.

---
## Blueprint: notifications (`/notifications`)
Manages NotificationCampaign creation & dispatch:
- Campaign configuration forms
- Recipient resolution & placeholder injection
- Email dispatch via Drive API
- Log listing / filtering

Missing explicit path mapping here—should be appended after automated scan.

---
## Blueprint: admin_personas (`/admin/personas`)
Persona management (linking to Keycloak, role toggling, possibly forcing sync). Add route inventory once file parsed (future automation).

---
## Blueprint: admin_sync (`/admin/sync`)
Triggers Keycloak↔Persona synchronization flows:
- Full sync
- Dry run preview
- Orphan cleanup
Outputs JSON or HTML summary.

---
## Blueprint: public (`/public` or root fallback)
Public-facing read-only views (probably concurso listings, published documents filtered by `is_visible_to_public`).

---
## Authentication / Authorization Decorators
- `keycloak_login_required`: Ensures OIDC session present.
- `admin_required`: Validates admin role membership.
- Future: consider `tribunal_required` decorator for clarity.

### Role Extraction Flow
Token decoded at request time, roles aggregated from realm + client scopes, stored in `g.user_roles`.

---
## Cross-Cutting Route Behaviors
### Document Generation
Triggered via concursos/admin templates actions -> calls `generar_documento_desde_template` which performs: placeholder data fetch, Drive doc creation, DB persistence, estado/subestado mutation, historial log.

### File & Folder Operations (Drive)
Performed in routes for concursos, postulantes, tribunal, and signing flows.
- Potential risk: missing retry logic / partial failure rollback.

### Notifications
Routes resolve recipients through NotificationCampaign.destinatarios_config (tribunal roles + static addresses + dynamic sets) then call placeholder resolver and Drive email API.

---
## Gaps & TODO for Route Layer
| Gap | Impact | Suggested Action |
|-----|--------|------------------|
| Missing enumerated endpoints for large blueprints (tribunal, concursos, notifications) | Incomplete docs | Implement introspection script to dump url_map filtered by blueprint name |
| Business rules embedded directly in route functions | Hard to test/extend | Move to service layer with thin controllers |
| Inconsistent error handling (flash vs JSON) | Mixed UX/API reliability | Standardize via helper responses & error blueprint |
| No rate limiting on sensitive actions (password reset, notifications) | Abuse vector | Add simple rate limiter (Redis or in-memory token bucket) |
| Lack of OpenAPI spec | Hard automation | Generate minimal spec via flask-smorest or apispec integration |

---
## Suggested Automation Snippet (Future)
Pseudo-code to list routes:
```python
for rule in app.url_map.iter_rules():
    if rule.endpoint.startswith('tribunal.'):
        print(rule.methods, rule.rule)
```
Integrate into management command to regenerate this doc section automatically.

---
## Extension Guidelines
When adding a new route:
1. Decide blueprint (respect domain boundaries).
2. Add decorator(s) for auth early.
3. Keep function under 40–50 LOC; move logic to a service.
4. Emit structured logs (action, entity_id, user_id).
5. Update tests: authorization, success path, at least one error path.
6. Update this doc (or trigger auto-generation).

---
Linked Documents: `SERVICES.md`, `INTEGRATIONS.md`, `DOCUMENT_GENERATION.md`, `PLACEHOLDER_SYSTEM.md`.
