# Data Models Documentation

This document enumerates all ORM models defined in `app/models/models.py`, their fields, relationships, and functional intent. Use this as the authoritative contract for refactoring, API design, and automated migrations.

> NOTE: The file is currently monolithic; future refactor should split by bounded context (e.g., concursos, tribunal, notifications, templates, support).

## Conventions
- All timestamps are UTC (`datetime.utcnow`), unless explicitly a `Date` (no time component).
- Foreign keys use explicit table names with naming in constraints for clarity where present.
- Lazy loading strategy varies (some `dynamic`, some default). Evaluate consistency during refactor.

---
## User (Authentication Admin User)
`users`
Used only for internal admin (legacy) bootstrap; Keycloak now primary identity provider for personas. Retained to own NotificationCampaign author relationship.

| Field | Type | Notes |
|-------|------|------|
| id | Integer PK |
| username | String(64) unique |
| password_hash | String(128) | PBKDF2 via Werkzeug |
| role | String(20) | Default 'admin' |
| is_active | Boolean | Soft active flag |
| created_at | DateTime |

Methods: `set_password`, `check_password`, property `is_admin`.

---
## Departamento / Area / Orientacion (Academic Structure)
Represents hierarchical academic classification. Loaded from JSON seed.

### Departamento
`departamentos`
- id, nombre, responsable (optional), correo
- relationships: `areas`, `concursos`

### Area
`areas`
- id, nombre
- FK: `departamento_id -> departamentos.id`
- relationship: `orientaciones`

### Orientacion
`orientaciones`
- id, nombre
- FK: `area_id -> areas.id`

---
## Categoria
`categorias`
Defines academic rank/category metadata and instruction JSON blobs.

| Field | Type | Notes |
| codigo | String(10) |
| nombre | String(100) |
| rol | String(50) | 'Profesor' or 'Auxiliar' (domain) |
| instructivo_postulantes | JSON nullable |
| instructivo_tribunal | JSON nullable |

---
## Instructivo (New Editable Content)
`instructivos`
Dynamic, versioned (light) storage for textual instructive content replacing legacy JSON blobs in `Categoria` and static `roles_categorias.json`.

| Field | Type | Notes |
|-------|------|------|
| id | Integer PK |
| tipo | String(20) | POSTULANTES / TRIBUNAL / GENERAL |
| categoria_id | FK -> categorias.id nullable | NULL for global/general fallback |
| dedicacion | String(20) nullable | Simple / Parcial / Exclusiva / NULL (base) |
| titulo | String(150) nullable | UI label |
| contenido | Text | Markdown / plain text |
| version | Integer | Incremented on update |
| is_active | Boolean | Soft disable instead of delete |
| created_at / updated_at | DateTime | Auto timestamps |
| created_by_persona_id | FK personas.id nullable | Audit |
| updated_by_persona_id | FK personas.id nullable | Audit |

Resolution precedence (POSTULANTES/TRIBUNAL):
1. (tipo, categoria_id, dedicacion)
2. (tipo, categoria_id, dedicacion IS NULL)
3. (GENERAL, NULL, NULL) fallback.

Refactor Notes:
- Legacy columns in `Categoria` retained temporarily (deprecation path documented in REFACTORING_GUIDE).
- Future: full version history table if rollback needed.

---
## Persona
`personas`
Represents a Keycloak-synchronized human (tribunal member or admin). Password fields deprecated after Keycloak migration.

Key Fields:
- dni (unique), nombre, apellido, correo, telefono
- username (can mirror DNI)
- keycloak_user_id (UUID string, unique)
- cv_drive_file_id / cv_drive_web_link (external resource anchors)
- is_admin (local flag; mirrors Keycloak role sync)

Relationships: `asignaciones` (TribunalMiembro dynamic).
Helper: `get_concursos()` to fetch concursos via tribunal membership.

---
## Concurso (Central Aggregate)
`concursos`
Represents a competitive selection process.

Core Fields:
- tipo (Regular/Interino), cerrado_abierto (lifecycle), cant_cargos
- departamento_id (FK)
- area, orientacion, categoria (+ categoria_nombre verbose)
- dedicacion, localizacion
- expediente, origen_vacante, docente_vacante, categoria_vacante, dedicacion_vacante
- id_designacion_mocovi (external ID)
- fechas: cierre_inscripcion, vencimiento
- estado_actual (string), subestado (Text storing JSON array of markers)
- Google Drive folder IDs: root + subfolders (borradores, postulantes, documentos_firmados, tribunal)
- Document specific drive file IDs (nota_solicitud_sac_file_id, etc.)
- Legacy resolution number fields (deprecated) + new consolidated `nro_res_llamado`, `nro_res_tribunal`, `nro_res_otras`
- Committee / council metadata (fechas + despachos)
- TKD linking + doc IDs

Relationships:
- `asignaciones_tribunal` (TribunalMiembro)
- `postulantes` (Postulante)
- `documentos` (DocumentoConcurso)
- `historial_estados` (HistorialEstado)
- `sustanciacion` (one-to-one Sustanciacion)
- `impugnaciones` (Impugnacion)
- `recusaciones` (Recusacion)

---
## TribunalMiembro
`tribunal_miembros`
Associates a Persona to a Concurso with a role.

Fields: concurso_id, persona_id, rol (Presidente, Titular, Suplente, Veedor), claustro (Docente/Estudiante), Drive folder ID.
Permission flags (fine-grained future use): can_add_tema, can_upload_file, can_sign_file, can_view_postulante_docs.
Notification flags: notificado, notificado_sustanciacion + timestamp fields.
Unique Constraint: (persona_id, concurso_id).
Relationships: persona, recusaciones, documentos (DocumentoTribunal), firmas (FirmaDocumento).

---
## DocumentoTribunal
`documentos_tribunal`
Supports per-tribunal-member document uploads (CV, DNI etc.). Simple type + URL + created timestamp.

---
## Postulante
`postulantes`
Applicant for a Concurso.
Fields: concurso_id, identity (dni, nombre, apellido), contacto, drive_folder_id, domicilio, estado.
Relationships: documentos (DocumentoPostulante), impugnaciones.

### DocumentoPostulante
`documentos_postulante`: postulante_id, tipo, URL, created.

---
## DocumentoConcurso
`documentos_concurso`
Documents generated or uploaded in the Concurso workflow.

Fields: concurso_id, tipo (enum-like string key), url (back compat), estado (BORRADOR, PENDIENTE DE FIRMA, FIRMADO), firma_count, borrador_file_id, file_id (signed/uploaded), resolution metadata (nro_res, tipo_res, fecha_res, articulado), subida_directa flag.

Relationships: `firmas` (FirmaDocumento cascade delete).

Key Methods:
- `ya_firmado_por(miembro_id)`
- Visibility logic: `is_visible_to_tribunal(miembro_tribunal)` & `is_visible_to_public()` consult `DocumentTemplateConfig` rules or fallbacks.
- `get_friendly_name()` / `get_template_display_name()`
- Drive linking helpers (`drive_file_id`, `get_document_url`, `update_url_from_file_ids`).

---
## FirmaDocumento
`firmas_documento`
Signature audit record for `DocumentoConcurso`.
Fields: documento_id, miembro_id, fecha_firma.
Relationships: documento_concurso, miembro.

---
## HistorialEstado
`historial_estados`
State transition & audit log.
Fields: concurso_id, estado, subestado_snapshot (JSON string), fecha, observaciones.
Used to reconstruct progression or debug complex transitions.

---
## Sustanciacion
`sustanciacion`
Holds procedural timeline for the evaluation phase (constitution, sorteo, exposicion, dictamen, resolucion) plus topics.
Fields: concurso_id, multiple *_fecha (DateTime), *_lugar, *_observaciones, *_virtual_link, temas_exposicion (pipe-delimited), tema_sorteado, temas_cerrados flag.

---
## Impugnacion / Recusacion
`impugnaciones` & `recusaciones`
Formal challenges.
Shared structure: concurso linkage, target entity (postulante or miembro), motivo, estado, resolucion, fechas.

---
## NotificationCampaign
`notification_campaigns`
Configurable bulk notification definitions.
Fields:
- nombre_campana, asunto_email, cuerpo_email_html
- destinatarios_config (Text JSON structure distinguishing tribunal roles, static emails, other dynamic groups)
- documentos_adjuntos_config (JSON array detailing document references)
- adjuntos_personalizados (list of Drive file IDs)
- estado_al_enviar / subestado_al_enviar (optional workflow triggers)
- creado_por (FK users.id)
Timestamps: creado_en, actualizado_en.
Relationships: `logs` (NotificationLog).
Helpers: `destinatarios_json` property (serialization convenience).

### NotificationLog
`notification_logs`
Delivery record.
Fields: campaign_id, concurso_id, destinatario_email, asunto_enviado, cuerpo_enviado_html, fecha_envio, estado_envio, error_envio.

---
## TemaSetTribunal
`temas_set_tribunal`
Per-member topic proposals for Sustanciacion.
Fields: sustanciacion_id, miembro_id, temas_propuestos (pipe-delimited), propuesta_cerrada, fecha_propuesta.
Unique Constraint: (sustanciacion_id, miembro_id).

---
## DocumentTemplateConfig
`document_template_configs`
Drives dynamic document behavior.

Fields (selected highlights):
- google_doc_id, document_type_key (unique), display_name
- uses_considerandos_builder, requires_tribunal_info
- concurso_visibility (REGULAR/INTERINO/BOTH)
- is_unique_per_concurso
- tribunal_visibility_rules (Text JSON: state -> {roles, claustros})
- public_visibility_rules (state -> bool)
- Permission flags: admin_can_send_for_signature, tribunal_can_sign, tribunal_can_upload_signed, admin_can_sign
- Estado/Subestado triggers: estado_al_generar_borrador, subestado_al_generar_borrador, estado_al_subir_firmado, subestado_al_subir_firmado
- subida_directa (upload without draft), es_res (resolution), parentesco (context linkage)
Timestamps: created_at, updated_at.

Helper methods parse and set JSON rule fields & perform concurso type visibility check via `is_visible_for_concurso_tipo`.

---
## SorteoConfig
`sorteo_config`
Rule table mapping (concurso_tipo, categoria_codigo) -> numero_temas_sorteados.
Unique Constraint ensures one rule per combination.

---
## Considerandos
`considerandos`
Local structured canonical paragraph sets per document type (replaces remote API). Fields: document_type (unique), visibility, considerandos_data (JSON), flags + timestamps.

---
## DepartamentoHead
`departamento_heads`
Local cache of department leadership metadata to support placeholders. Unique by departamento.

---
## Initialization Helpers
### init_db_from_json(app, json_data)
Seeds Departamento/Area/Orientacion hierarchy.
### init_categories_from_json(app, json_data)
Seeds Categoria records with instructivo JSON.

---
## Cross-Cutting Concerns
### Estado / Subestado Strategy
- `Concurso.estado_actual` a scalar string.
- `Concurso.subestado` accumulates JSON array of markers; modifications triggered by document template lifecycle. Maintain referential integrity when deleting documents (ensure reversals—logic should be centralized in future service).

### Visibility & Permissions
- Document visibility logic layered: configuration-first fallback to hardcoded defaults for tribunal & public.
- Permission booleans in `DocumentTemplateConfig` + per-member ability flags (currently not fully enforced across all routes).

### Placeholder Source Mapping
The placeholder resolver composes values from multiple models; any schema change must reflect in `placeholder_resolver.get_core_placeholders` for consistency.

---
## Refactor Recommendations (Model Layer)
1. Split models by domain module: `concurso.py`, `documents.py`, `tribunal.py`, `notifications.py`, `reference.py`.
2. Introduce BaseModel mixin for timestamps & soft-delete if required later.
3. Replace raw string enums (estado, tipo, rol) with Python `Enum` + validation.
4. Encapsulate subestado mutations in domain method (e.g., `Concurso.add_subestado(marker)` / `remove_subestado(marker)`).
5. Add repository/query objects for complex fetch patterns (e.g., concursos with active documents & pending signatures).
6. Normalize some denormalized textual duplicates (e.g., both `categoria` & `categoria_nombre`). Retain materialized field only if required for performance.
7. Add DB constraints for estados where invariant is known (CHECK constraints or enumerations if underlying DB supports).

---
## Dependency Graph (Simplified)
```
Concurso
 ├─ DocumentoConcurso ─┬─ FirmaDocumento
 │                     └─ HistorialEstado
 ├─ TribunalMiembro ────┬─ DocumentoTribunal
 │                      └─ TemaSetTribunal (via Sustanciacion)
 ├─ Postulante ─────────┬─ DocumentoPostulante
 │                      └─ Impugnacion
 ├─ Sustanciacion
 ├─ Impugnacion
 └─ Recusacion

NotificationCampaign ──> NotificationLog
DocumentTemplateConfig ─> DocumentoConcurso (behavior)
SorteoConfig ──────────> Sustanciacion (topic draw rules)
Considerandos / DepartamentoHead ─> PlaceholderResolver
Persona ──> TribunalMiembro (role assignment)
User (legacy) ─> NotificationCampaign.creado_por
```

---
Keep this document updated when:
- Adding or removing tables/fields
- Changing lifecycle semantics (estado/subestado)
- Modifying visibility or permission resolution logic
