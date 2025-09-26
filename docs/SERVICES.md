# Services Layer Documentation

This document describes service modules under `app/services/` and related helper utilities that encapsulate business logic separate from route controllers.

## Overview
Services centralize non-trivial logic: synchronization with Keycloak, placeholder computation, password reset workflow, scheduling, and (implicitly) document processing support. Some logic still resides in routes (to be migrated). This guide enables safe refactoring toward thinner controllers and testable service abstractions.

## Placeholder Resolver (`placeholder_resolver.py`)
Primary entry point: `get_core_placeholders(concurso_id, persona_id=None)`

Responsibilities:

Helper Functions:

Performance Notes:

Refactor Candidates:

## Keycloak Persona Sync (`keycloak_persona_sync.py`)
Class: `KeycloakPersonaSyncService`

Responsibilities:
- Bidirectional reconciliation between local `Persona` rows and Keycloak users possessing tribunal/admin roles.
- Creation of Keycloak users for local personas lacking linkage (with email requirement).
- Creation of local personas for Keycloak users missing in DB.
- Role assignment (ensures baseline `tribunal_member`; toggles `app_admin`).
- Update path (optional user data sync when `sync_user_data=True`).
- Orphan removal (`remove_orphaned_personas`) when Keycloak role revoked or user deleted.

|--------|---------|
| `sync_all(dry_run=False)` | Orchestrates full cycle (local→Keycloak, Keycloak→local, updates). |
| `sync_keycloak_to_personas(dry_run)` | Mirrors Keycloak users locally. |
| `sync_updates(dry_run, sync_user_data)` | Adjusts roles & optionally user profile fields. |
Return Structure: Dict summarizing created/updated/skipped/errors for audit & UI display.

- Add dry-run diff output formatting utility for user-facing preview.

---
## Password Reset Service (`password_reset_service.py`)
Purpose: Provide a custom email-based password reset workflow independent of Keycloak's default appearance while still ultimately requiring Keycloak credential change.

Core Features:
- Token generation with HMAC-style signature using `RESET_TOKEN_SECRET`.
- Email dispatch through Google Drive script email endpoint (HTML templates with placeholder injection if needed).
- Fallback methods for simplified notification.

Important Methods (inferred):
| Method | Purpose |
|--------|---------|
| `generate_reset_token(user_id)` | Encodes user & expiry into signed bundle. |
| `verify_reset_token(token)` | Validates signature & expiry. |
| `send_reset_email_internal(persona, keycloak_user_id)` | Composes internal email variant. |
| `notify_tribunal_member_with_reset(...)` | Bulk/individual tribunal notifications with token links. |
| `send_simple_reset_fallback(...)` | Minimalistic alternative channel. |

Security Considerations:
- Ensure token includes issued-at + expiry to mitigate replay.
- Consider logging token usage & invalidation attempts.
- Potential escalation: store hash of issued tokens in DB for revocation auditing.

---
## Sync Scheduler (`sync_scheduler.py`)
- Initializes background scheduler to periodically invoke persona/Keycloak sync tasks.
- Runs inside Flask process (not external worker) — risk of duplicate execution across multiple WSGI processes; migration to external cron / task queue recommended for horizontal scalability.

Enhancements:
- Add jitter to reduce synchronized spikes.
- Add health endpoint summarizing last run status and delta changes.

---
## (Legacy / Backup) `password_reset_service_backup.py`
- Retained for rollback or reference. Safe candidate for removal once parity confirmed.

---
## Helper Utilities (Supporting Services)
Although located in `app/helpers`, these supply core service functionality:

### `text_formatting.py`
- `format_cargos_text`, `format_descripcion_cargo` – domain-specific phrasing logic reused in placeholders; central to consistent narrative style across documents.

### `pdf_utils.py`
- Functions to stamp signatures (migrated away from remote Drive stamping) and merge PDFs.
- Current stamping design: fetch original PDF (Drive -> base64), apply PIL/PyPDF2 modifications, re-upload via `overwrite_file`.
- Ensure deterministic placement & handle multi-signature stacking (based on `firma_count`).

### `google_drive_loading.py`
- Provides contextual loading state management decorator (`with_loading`)— UI/UX integration artifact; minimal backend necessity.

### `api_services.py`
- External academic program metadata retrieval (`get_programa_by_id_materia`, `get_programas_by_materia_ids`, `get_programa_download_url`).
- Add circuit breaker or timeout/backoff parameters.

---
## Document Generation (Service Boundary)
Although implemented in `app/document_generation/document_generator.py`, function `generar_documento_desde_template` acts as a service:
- Gathers data via placeholder resolver.
- Handles considerandos conditional logic.
- Applies estado/subestado mutations & history logging.
- Persists `DocumentoConcurso` metadata.

Refactor Target: Promote to a class (e.g., `DocumentGenerationService`) encapsulating Drive adapter calls + transaction orchestration.

---
## Cross-Service Concerns
| Concern | Current State | Recommendation |
|---------|---------------|----------------|
| Error Handling | Mix of `print`, `logger`, bare `except` | Standardize custom exceptions per domain (SyncError, GenerationError) |
| Transactions | Multi-step Drive + DB not fully atomic | Use `session.begin()` + compensation strategy or two-phase commit style | 
| Authorization Leak | Services assume caller validated roles | Add assertion hooks (e.g., `assert is_admin`) when critical |
| Logging Context | Sparse correlation IDs | Introduce request-scoped UUID (middleware) propagated to all logs |
| Caching | None | Memoize placeholder resolver for same concurso within request |

---
## Refactor Roadmap (Services Layer)
1. Create `services/concurso_service.py` with operations: create_concurso + folder provisioning, update_estado, add_document.
2. Extract `NotificationService` to encapsulate campaign execution & logging (currently partly in route + Drive calls).
3. Introduce `DriveService` wrapper layering retries, error taxonomy, latency metrics.
4. Add interface boundaries (protocol classes / abstract base classes) for Keycloak & Drive enabling test mocks.
5. Implement dependency injection pattern via app factory registration dictionary.

---
## Testing Strategy Suggestions
| Service | Existing Tests | Needed |
|---------|----------------|--------|
| Placeholder Resolver | Unit & mocked integration tests present | Add performance + edge-case (empty relationships) |
| Document Generation | Mocked integration only | Add full flow with temp Drive mock, multi-sign signatures |
| Sync Service | None in provided tests | Add dry_run diff test + role assignment matrix |
| Password Reset | Not covered | Token validity, expiry, tamper detection |
| PDF Utils | Not covered | Visual regression hash or structural checks for signature layer |

---
## Example Pseudocode Refactor (Generation)
```python
class DocumentGenerationService:
    def __init__(self, drive: DriveGateway, placeholder_service: PlaceholderService, repo: ConcursoRepository):
        ...
    def generate(self, concurso_id: int, template_key: str, considerandos: str|None):
        concurso = self.repo.get_with_lock(concurso_id)
        data = self.placeholder_service.build(concurso_id)
        # map & validate
        drive_id, link = self.drive.from_template(...)
        self.repo.add_document(...)
        self.repo.apply_state_rules(...)
        self.repo.commit()
        return link
```

---
Linked Docs: `DOCUMENT_GENERATION.md`, `INTEGRATIONS.md`, `PLACEHOLDER_SYSTEM.md`, `ROUTES.md`.

---
## Instructivo Service (UI Editing Note)
La edición de instructivos ahora está disponible vía interfaz gráfica:
- Menú: Datos → Instructivos (`/admin/instructivos/ui`)
- Operaciones soportadas: listar (filtro por tipo), crear/actualizar combinación (tipo, categoría, dedicación).
- Precedencia de resolución documentada en la sección principal del servicio.
- Backend: `GET/POST /admin/instructivos/` (JSON) + `seed_from_roles_categorias` para poblar datos iniciales si la tabla está vacía.

Próximos pasos sugeridos:
- Agregar vista de historial (cuando se implemente versionado completo).
- Validaciones de longitud y sanitización si se habilita Markdown enriquecido.

---
## Required Documents Service (`required_docs_service.py`)
Centraliza la configuración dinámica de la sección "DOCUMENTACIÓN REQUERIDA" utilizada en:
- PDF de Formulario de Inscripción (`pdf_utils.generate_formulario_inscripcion_pdf`)
- Vista Postulantes
- Vista Tribunal (documentación de postulantes)

### Modelo: `RequiredDocumentSet`
Campos clave:
- `categoria_id` (nullable) → especifica categoría o global.
- `dedicacion` (nullable) → especifica dedicación o base.
- `documentos` (JSON list) → lista de códigos canónicos.
- `version`, `is_active`, timestamps, created/updated_by.

Restricción única: `(categoria_id, dedicacion)`.

### Precedencia de Resolución
1. (categoria_id, dedicacion)
2. (categoria_id, NULL)
3. (NULL, NULL) Global

### Catálogo de Códigos
Declarado en constante `DOCUMENT_CATALOG` (código → etiqueta humana):
```
DNI, CV, DOCUMENTACION_RESPALDATORIA_CV, TITULO_UNIVERSITARIO,
ANTECEDENTES_IDONEIDAD, PROPUESTA_PROGRAMA, ACTIVIDADES_PREVISTAS,
PLAN_FORMACION_RRHH, PLAN_IVE, PLAN_IVE_OPCIONAL,
PLAN_O_PROGRAMA_ACTIVIDADES, PROPUESTA_EJERCICIO_O_TP
```

### API Admin
`/admin/required-docs/catalog` → catálogo (GET)
`/admin/required-docs/` → listar sets (GET, filtrable por `categoria_id`)
`/admin/required-docs/` → crear/actualizar (POST) (upsert por combinación)
`/admin/required-docs/ui` → interfaz HTML (multi-select)

### Flujo de Persistencia
`create_or_update`:
- Busca fila existente por `(categoria_id, dedicacion)`.
- Si existe: reemplaza `documentos`, `bump_version()`.
- Si no: crea nueva fila.

### Integración en PDF / Rutas
1. Resolver vía servicio.
2. Si vacío → fallback legacy `roles_categorias.json` (migración progresiva).

### Consideraciones de Migración
- Seed opcional desde `roles_categorias.json` (método `seed_from_roles_categorias`).
- Pendiente: script/mando admin para ejecutar seed y luego marcar JSON como deprecado.
- Verificar si JSON legacy contiene claves adicionales no migradas (por ejemplo futuras secciones) → TODO listado en backlog.

### Extensiones Futuras
- Versionado histórico (tabla audit trail).
- Campos adicionales: `obligatorio` vs `opcional` por documento.
- Etiquetado / agrupación lógica (p.e. académicos, identidad, planes, otros).
- Validación server-side de códigos (rechazar códigos desconocidos).
- Endpoint para sugerir documentos faltantes a un postulante concreto.

### Testing Sugerido
| Caso | Descripción |
|------|-------------|
| Exact match | categoria + dedicación configuradas devuelven lista correcta |
| Base fallback | Sin dedicación específica usa set base |
| Global fallback | Sin set de categoría usa global |
| Vacío total | Sin filas → retorna [] y se activa fallback legacy |
| Upsert | Misma combinación incrementa versión |

### Riesgos / Mitigaciones
- JSON legacy divergente: registrar warning cuando fallback ocurra para monitorear transición.
- Crecimiento de catálogo sin control: centralizar edición del diccionario y agregar validación.
- Concurrencia mínima: transacciones simples suficientes; agregar bloqueo optimista si se añade historia.

---
## Legacy JSON Audit (Pendiente)
Revisar `roles_categorias.json` para confirmar si existen claves no migradas (ej: textos auxiliares, notas contextuales). Si se detectan, crear nuevo modelo o extender `RequiredDocumentSet` con metadata.
