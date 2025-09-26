# External Integrations

This document covers integration boundaries with external systems: Keycloak (Identity & Admin), Google Drive Apps Script API, and legacy data sources replaced by local persistence. It defines responsibilities, failure modes, and improvement recommendations.

---
## Overview Matrix
| Integration | Module(s) | Protocol | Primary Use | Criticality |
|-------------|-----------|----------|-------------|-------------|
| Keycloak OIDC | `integrations/keycloak_oidc.py` | OAuth2/OIDC | Authentication (login, roles) | High |
| Keycloak Admin | `integrations/keycloak_admin_client.py` | REST via python-keycloak | User provisioning, role sync, password status | High |
| Google Drive / Email | `integrations/google_drive.py` (Apps Script endpoint) | HTTPS JSON (custom actions) | Folder + doc lifecycle, file uploads, email dispatch | High |
| Legacy Google Scripts (Deprecated) | `init_considerandos_and_deptoheads.py` | HTTPS JSON | One-time data migration | Low (post-migration) |

---
## Keycloak OIDC Client
File: `app/integrations/keycloak_oidc.py`

Responsibilities:
- Register OAuth client using dynamic OIDC discovery (authorization, token, userinfo, JWKS).
- Manage login redirect, callback token exchange, direct Resource Owner Password Credentials (ROPC) fallback.
- Extract roles from access token (realm_access + resource_access). Stores in Flask `g` context.
- Populate session with `keycloak_token` dict containing: access_token, refresh_token (if provided), id_token.

Notable Methods:
| Method | Purpose |
|--------|---------|
| `init_app(app)` | Registers client & before_request handler |
| `_load_user_info()` | Fetches userinfo + role extraction each request |
| `direct_authenticate(username, password)` | Performs ROPC; logs detailed failures |
| `logout()` | Local session clear (no federated logout currently) |
| `reset_password()` | Uses admin client to send UPDATE_PASSWORD action |

Security / Hardening:
- Ensure HTTPS; ROPC should be limited to trusted contexts only.
- Consider token refresh handling (currently not explicit) → add silent refresh or expiration check.
- Add PKCE enforcement if migrating away from confidential client patterns.

Failure Modes:
| Failure | Handling |
|---------|----------|
| Network / Timeout | Caught, logs error, session cleared |
| Invalid token / decode error | Token removed, user considered unauthenticated |
| JWKS mismatch | Roles may be empty; log warning |

---
## Keycloak Admin Client
File: `app/integrations/keycloak_admin_client.py`

Responsibilities:
- Service account authentication using client credentials (configured via `KEYCLOAK_ADMIN_CLIENT_ID/SECRET`).
- CRUD & attribute updates for users; role assignment; password resets; credential inspection.
- Email dispatch via execute-actions (tokenized account update links). Limited attempt at custom email (may require additional realm config).
- Password status inference (`get_user_password_status`) with nuanced state classification: `password_set`, `password_required`, `not_configured`, `disabled`, `uncertain`.

Important Methods:
| Category | Methods |
|----------|---------|
| User Lookup | `get_user_by_username`, `get_user_by_email`, `get_user_by_id`, `search_users` |
| User Lifecycle | `create_user`, `update_user`, `delete_user`, `disable_user` |
| Credentials | `set_user_password`, `has_user_set_password`, `get_user_password_status` |
| Roles (Realm/Client) | `assign_realm_role`, `remove_realm_role`, `assign_client_role`, `remove_client_role`, `get_user_client_roles` |
| Email | `send_execute_actions_email`, `send_execute_actions_email_with_redirect`, `send_template_email`, `send_custom_email` |

Failure Modes & Logging:
- Wraps KeycloakError exceptions; returns booleans or None for introspection.
- Some methods silently continue after failing to fetch realm info (graceful degradation). Add escalation flag for critical contexts.

Improvements:
- Introduce typed error classes (e.g., `RoleAssignmentError`).
- Cache client ID lookup (avoid repeated `get_client_id` calls).
- Add retry for transient 5xx (idempotent operations only).

---
## Google Drive & Email (Apps Script Gateway)
File: `app/integrations/google_drive.py`

Architecture:
- Single endpoint URL with JSON body specifying `action` key controlling behavior (command pattern over HTTP).
- Security: Shared bearer-like token `GOOGLE_DRIVE_SECURE_TOKEN` in request body (symmetric). Recommend rotating and migrating to header + HMAC signature.

Supported Actions (as of code):
| Action | Purpose |
|--------|---------|
| `createFolder` | Create root concurso folder |
| `createNestedFolder` | Create subfolder within parent |
| `createPostulanteFolder` | Specialized postulante folder create |
| `createDocFromTemplate` | Duplicate a Google Doc template, perform placeholder substitution (server-side) |
| `uploadFile` | Upload base64 file to folder |
| `overwriteFile` | Replace existing file content |
| `getFileContent` | Retrieve base64 file (for local PDF stamping) |
| `deleteFile` | Remove file |
| `deleteFolder` | Remove folder recursively |
| `renameFolder` | Folder rename |
| `sendEmail` | Dispatch HTML email with attachments + placeholder map |
| `addSignatureToPdf` | (Deprecated) remote signature stamping |

Local Wrapper Responsibilities:
- Base64 encoding/decoding.
- Logging & error transformation into Python exceptions.
- Loading decorators for UI feedback (progress). Pure backend variant could drop these.

Reliability & Consistency:
- No transactionality between Drive operations and DB commits: risk of orphaned references. Mitigation: design compensating cleanup job.
- Missing exponential backoff or classification of error types.
- File overwrites rely on external file ID extraction from URL parsing (fragile).

Enhancement Roadmap:
| Area | Proposal |
|------|----------|
| Security | Use signed timestamped headers; rotate token; optional IP allowlist |
| Observability | Include `correlation_id` in payload & return; log Drive latency histogram |
| Idempotency | Optional client-supplied operation key (e.g., for doc generation) |
| Error Taxonomy | Standard JSON error envelope with codes (e.g., DRIVE_QUOTA, TEMPLATE_NOT_FOUND) |
| Testing | Mock gateway layer with local in-memory store for unit tests |

---
## Legacy External Data Migration
Script: `init_considerandos_and_deptoheads.py`
- Fetched remote JSON via two Apps Script endpoints.
- Persisted to local tables (`Considerandos`, `DepartamentoHead`).
- Provides validation reports and summary.
- Post-migration: remove runtime dependency on remote endpoints; consider deleting script after archival.

---
## Interaction Sequences (Conceptual)
### Document Generation
```
User -> Flask Route -> PlaceholderResolver -> Drive.createDocFromTemplate
       -> DB persist DocumentoConcurso -> (Estado/Subestado mutation) -> Response
```

### Password Reset (Custom)
```
User submits form -> PasswordResetService.generate_reset_token
 -> Drive.sendEmail (HTML link) -> User clicks -> Keycloak change password (not fully shown yet)
```

### Persona Sync
```
Scheduler/Admin Action -> KeycloakPersonaSyncService.sync_all
 -> Keycloak Admin API (search/create/update) <-> DB Persona rows -> Summary Report
```

---
## Failure Handling Strategy (Current vs Target)
| Integration | Current Handling | Target Improvement |
|-------------|------------------|--------------------|
| Keycloak OIDC | Log & clear session on decode failure | Add token expiry pre-check & refresh path |
| Keycloak Admin | Boolean/None returns + logs | Raise typed exceptions; central retry policy |
| Drive | Raise generic Exception with response text | Structured error objects + classification |
| Migration Scripts | Print + traceback | Logging + exit codes for automation |

---
## Security Hardening Summary
| Vector | Current | Recommendation |
|--------|---------|---------------|
| Drive Auth | Static token in body | Move to header + HMAC, rotate via secret manager |
| Keycloak ROPC | Enabled | Restrict usage; prefer auth code PKCE for browser clients |
| Email Injection | Minimal placeholder substitution | Sanitize user-provided placeholder sources |
| File ID Parsing | String split on URL | Store canonical file IDs separately (already partly implemented) |

---
## Testing & Mocking Guidelines
| Integration | Mock Strategy |
|-------------|--------------|
| Keycloak OIDC | Patch network calls; supply static token payload |
| Keycloak Admin | Stub `KeycloakAdmin` methods; simulate role lists / errors |
| Drive | Replace `GoogleDriveAPI` with fake in-memory directory + content map |
| Migration | Replace `requests.get` with canned JSON fixtures |

Introduce a `gateways/` package to formalize interfaces and allow dependency injection in services.

---
## Observability Metrics (Proposed Names)
| Metric | Type | Description |
|--------|------|-------------|
| drive_request_latency_seconds | Histogram | Round-trip per action |
| drive_request_errors_total | Counter | Failures labeled by action & error_code |
| keycloak_admin_latency_seconds | Histogram | Admin API call latency |
| keycloak_user_sync_changes_total | Counter | Created/updated/linked personas |
| document_generation_total | Counter | Documents generated labeled by tipo & estado_final |

---
## Quick Reference
| Need | Where |
|------|-------|
| Add new Drive action | `google_drive.py` (switch-case style if added in script) |
| Inspect Keycloak password status | `get_user_password_status` |
| Force persona sync | Route using `KeycloakPersonaSyncService.sync_all()` |
| Adjust template Google Doc ID | Admin UI `/admin/templates` or DB row |

---
Linked Docs: `SERVICES.md`, `DOCUMENT_GENERATION.md`, `PLACEHOLDER_SYSTEM.md`, `ARCHITECTURE_OVERVIEW.md`.
