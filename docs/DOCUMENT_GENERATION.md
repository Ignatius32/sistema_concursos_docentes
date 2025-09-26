# Document Generation System

This document explains the end-to-end workflow for generating, evolving, and publishing concurso documents using Google Drive templates, placeholder resolution, and signature flows.

---
## Goals
- Centralized generation with consistent placeholders and formatting.
- Configurable behavior per document type (visibility, permissions, state transitions).
- Draft (BORRADOR) → Signing (PENDIENTE DE FIRMA) → Final (FIRMADO) life cycle.
- Automatic concurso estado/subestado updates driven by template configuration.

---
## Key Components
| Component | File | Role |
|-----------|------|------|
| Template Configuration | `DocumentTemplateConfig` (model) | Stores Google Doc ID + behavioral flags |
| Generation Orchestrator | `document_generator.py` | Core function `generar_documento_desde_template` |
| Placeholder Source | `placeholder_resolver.get_core_placeholders` | Dynamic data assembly |
| Storage / Delivery | Google Drive (Apps Script) | Creates Docs in `borradores` folder |
| Document Record | `DocumentoConcurso` | Tracks state, file IDs, signatures |
| History | `HistorialEstado` | Logs generation events |

---
## Template Configuration Fields (Behavioral)
| Field | Purpose |
|-------|---------|
| `google_doc_id` | Source template (author-editable) |
| `document_type_key` | Internal doc type key (e.g., `RESOLUCION_LLAMADO_REGULAR`) |
| `display_name` | UI-friendly label |
| `uses_considerandos_builder` | Enforces inclusion of dynamic considerandos text |
| `requires_tribunal_info` | Validates tribunal membership presence |
| `concurso_visibility` | REGULAR / INTERINO / BOTH filtering |
| `is_unique_per_concurso` | Prevent multiple documents of same type (enforced in route/service) |
| Permission Flags | Determine who can send/sign/upload |
| Estado/Subestado Triggers | Automate concurso progression on draft/signing events |
| Visibility Rules (Tribunal/Public) | Control when documents are visible in portal/public listing |

---
## Generation Workflow
Sequence (simplified):
```
User Action (Admin) -> Route (/concursos doc action) -> generar_documento_desde_template
  -> Fetch Concurso + TemplateConfig
  -> Validate preconditions (tribunal required? considerandos required?)
  -> Resolve placeholders (get_core_placeholders)
  -> Merge considerandos (if provided)
  -> Map legacy placeholder names (compatibility layer)
  -> Drive API createDocFromTemplate(template_doc_id, data) in borradores folder
  -> Persist DocumentoConcurso (estado=BORRADOR, borrador_file_id)
  -> Apply estado/subestado mutations to Concurso
  -> HistorialEstado entry
  -> Return link
```

### Data Assembly
`prepare_data_for_document` merges:
- Placeholder dict (canonical keys)
- Legacy alias mapping (e.g., `expediente` → `Expediente`)
- Considerandos content (post substitution) if required.

### Considerandos Builder
When `uses_considerandos_builder=True`:
- UI collects selected segments (list of paragraphs).
- Raw combined text passed to generation call.
- Placeholder substitution applied post-combination.
- Failure to supply considerandos aborts generation with user-facing error.

---
## Document States (DocumentoConcurso)
| State | Meaning | Transition Trigger |
|-------|---------|--------------------|
| BORRADOR | Draft in borradores folder | Initial generation via template creation |
| ENVIADO PARA FIRMAR | (Admin route only) Sent out via email for external/administrative signature collection | Admin action: /enviar-firma |
| PENDIENTE DE FIRMA | Uploaded PDF pending tribunal member signatures (internal signing workflow) | Tribunal upload (or admin direct upload setting state) |
| FIRMADO | Fully signed official version (all required tribunal signatures or admin digital signature) | Final signature applied or admin signs / direct signed upload |

Implementation note: The original table omitted ENVIADO PARA FIRMAR which is used by `enviar_firma` route, and both ENVIADO PARA FIRMAR and PENDIENTE DE FIRMA coexist. Consider normalizing to a single intermediate state or documenting their semantic difference clearly in UI.

### File ID Fields
| Field | Usage |
|-------|-------|
| `borrador_file_id` | Google Doc (editable) draft version |
| `file_id` | Uploaded signed PDF (documentos_firmados folder) |
| `url` | Backwards compatibility; updated to match active file |

`get_document_url` prioritizes by state (signed version for PENDIENTE/FIRMADO else draft ID).

Additional internal fields and behaviors observed:
- `borrador_file_id` always stores the Google Doc (editable) produced from the template.
- `file_id` for both pending and finalized PDF (tribunal or admin signed). The code overwrites or replaces the PDF during sequential signatures.
- `subida_directa` flag (on template config and DocumentoConcurso) allows skipping draft generation and creating a signed (FIRMADO) document directly via upload.
- Resolution metadata (`es_res`, `parentesco`, plus `nro_res`, `tipo_res`, `fecha_res`, `articulado`) drive concurso-level fields like `nro_res_llamado`, `nro_res_tribunal`, `nro_res_otras` via `update_concurso_resolution_number`.

---
## Signature Flow (High-Level)
1. Draft validated & content finalized.
2. Move to signing phase (state change + optionally convert to PDF locally or by user upload).
3. Each signing action:
   - Fetch PDF via `get_file_content`.
   - Apply signature stamp using `pdf_utils` (name, DNI, position, sequential placement based on `firma_count`).
   - Overwrite file via `overwrite_file` or create new revision.
   - Increment `firma_count`; add `FirmaDocumento` record.
4. Once required signatures collected → state set to FIRMADO (auto or manual) + concurso estado/subestado updated if template rules define `estado_al_subir_firmado`.

Two parallel signature modalities:
1. Email-based external signature request (state ENVIADO PARA FIRMAR) – handled by admin, attaches current draft (borrador) or signed file id.
2. In‑system tribunal stamping workflow (state PENDIENTE DE FIRMA) – tribunal members iteratively stamp PDF (`firma_count` increments) until all non‑suplente roles have signed, then auto‑transition to FIRMADO.

Admin digital signature path: `admin_firmar_documento` converts draft to signed PDF (placing signature stamp) and jumps directly to FIRMADO.

### Visibility During Signing
Controlled by `tribunal_visibility_rules` (JSON). Example structure:
```json
{
  "BORRADOR": {"roles": ["Presidente"], "claustros": ["Docente"]},
  "PENDIENTE DE FIRMA": {"roles": ["Presidente", "Titular"], "claustros": ["Docente", "Estudiante"]},
  "FIRMADO": {"roles": ["Presidente", "Titular", "Suplente"], "claustros": ["Docente", "Estudiante"]}
}
```
Fallback logic (if no config):
- Always visible to tribunal for certain whitelisted types or when state is FIRMADO / PENDIENTE and member hasn't signed.

---
## Concurso Estado/Subestado Dynamics
On generation (draft):
- If `estado_al_generar_borrador` set → `concurso.estado_actual` updated.
- If `subestado_al_generar_borrador` set → appended to JSON list in `concurso.subestado` (deduplicated).

On signed upload / finalization:
- Similar application of `estado_al_subir_firmado`, `subestado_al_subir_firmado`.
- Document deletion (not shown here) should remove subestado markers added solely by that document (confirm and centralize logic). Future improvement: store provenance in history for safe reversal.

---
## Placeholder Mapping Compatibility Layer
Reason: Historic templates reference mixed-case or Spanish-labeled variables.
Strategy: Provide both canonical and legacy keys in `data` passed to Drive template fill step.
Migration Path: New templates should use canonical placeholders only; schedule removal of legacy map after full template refresh.

---
## Error Handling & Validation
| Check | Failure Response |
|-------|------------------|
| Concurso not found | 404 (abort or False, message) |
| Required tribunal missing | Error message, no document created |
| Considerandos required but absent | Error message |
| Drive API creation failure | Rolls back DB session, returns error |
| JSON decode in state/subestado updates | Safe fallback (treat as string list) |

Improve by raising typed exceptions (e.g., `GenerationPreconditionError`).

---
## Performance Considerations
- Single placeholder computation per generation; heavy operations (tribunal + postulante iteration) O(n). Acceptable at current scale; can cache inside request.
- Drive round trip dominates latency; consider async job or queued generation for batch operations.
- Multi-signature stamping re-downloads and uploads entire PDF each signature; could optimize by layered incremental annotation buffer.

---
## Observability (Proposed Logging Fields)
| Field | Description |
|-------|-------------|
| `event=document_generated` | Static event label |
| `concurso_id` | Foreign key id |
| `document_type_key` | Template key |
| `draft_file_id` | Drive ID |
| `estado_before` / `estado_after` | State transition capture |
| `subestado_delta` | Added markers list |
| `latency_ms` | Generation elapsed time |

---
## Edge Cases & Future Enhancements
| Scenario | Enhancement |
|----------|-------------|
| Duplicate generation of unique template | Pre-check with query + guard | 
| Partial failure after Drive creation before DB commit | Compensating deletion job or saga pattern |
| Missing placeholder causing template artifacts | Add audit utility enumerating unused or unresolved placeholders |
| Large considerandos sections | Support streaming substitution (not critical now) |
| Multi-language | Add locale parameter for date formatting / month names |
| Dual interim states (ENVIADO PARA FIRMAR vs PENDIENTE DE FIRMA) | Consolidate or clearly separate semantics; maybe introduce a unified SIGNATURE_PENDING with subtype source=external|tribunal |
| Repeated template_config lookups | Cache within request or inject service to reduce duplicate queries |
| Legacy placeholder mapping maintenance burden | Emit deprecation warnings / provide script to scan templates for legacy tokens |
| Tribunal visibility fallback logic separate from config rules | Centralize in a visibility service to avoid drift |
| Lack of DB constraint for per-concurso uniqueness | Optional unique index (concurso_id, tipo) when `is_unique_per_concurso` true |

## Tribunal Workflow Summary (Observed)
| Step | Actor | Action | Resulting State | Key Code Path |
|------|-------|--------|-----------------|---------------|
| View available documents | Tribunal member | Portal lists visible docs filtered by `is_visible_to_tribunal` | varies | `DocumentoConcurso.is_visible_to_tribunal` |
| Upload PDF for signing | Tribunal (role permitted) | Upload triggers state change | PENDIENTE DE FIRMA | `tribunal` route segment (upload logic) |
| Stamp signature | Tribunal member | Adds signature stamp, increments `firma_count` | PENDIENTE DE FIRMA or FIRMADO when complete | `firmar_documento` |
| Admin direct signature | Admin | Stamps draft and uploads signed PDF | FIRMADO | `admin_firmar_documento` |

Visibility drivers:
- Template-config JSON (`tribunal_visibility_rules`, `public_visibility_rules`).
- Fallback heuristics (always visible types, FIRMADO always visible) when no rules JSON present.

## Discovered Discrepancies / Technical Debt
1. State naming inconsistency: docs originally excluded ENVIADO PARA FIRMAR; code uses both states. Harmonize or document UI distinctions.
2. Repetitive retrieval of `DocumentTemplateConfig` in multiple branches – candidate for a small caching layer.
3. Legacy placeholder mapping layer persists; schedule migration to canonical keys and removal toggle.
4. Placeholder resolver note indicates missing logic for filtering only active postulantes (comment: "very important you mention this to user"). Implement active check and populate `postulantes_activos_lista` accordingly.
5. Error handling: broad try/except with rollback in generation; introduce typed exceptions (`TemplateNotFoundError`, `DriveGenerationError`, etc.) for clearer user feedback.
6. Potential race on uniqueness (no DB constraint) if two admins generate same unique template concurrently.
7. Missing rename operation in Drive API for resolution files (placeholder function logs intention). Extend API to support rename or include the correct name at upload time after resolution metadata entry.
8. Mixed responsibility in routes (state transitions, history logging, file operations). Extract a service layer to cut duplication across admin and tribunal paths.

## Proposed Refactor Hotspots
- Service abstraction: `DocumentService` (generation, signing, uploading, state transitions)
- Visibility & permission policy object derived from `DocumentTemplateConfig`
- Placeholder caching per request context
- Consistent state enum / constants module (avoid string literals scattered)


---
## Sample Pseudocode (Refactor to Service Class)
```python
class DocumentGenerationService:
    def __init__(self, drive, placeholder_resolver, concurso_repo):
        ...
    def generate(self, concurso_id, template_key, considerandos=None):
        concurso = concurso_repo.get(concurso_id, lock=True)
        template = template_repo.get_by_key(template_key)
        self._validate(concurso, template, considerandos)
        placeholders = placeholder_resolver.build(concurso_id)
        data = self._assemble_data(concurso, template, placeholders, considerandos)
        file_id, link = drive.create_from_template(template.google_doc_id, data, concurso.borradores_folder_id)
        documento = concurso_repo.add_document(concurso, template_key, file_id, link)
        state_tracker.apply_template_rules(concurso, template, phase="draft")
        history.log_generation(concurso, template_key)
        concurso_repo.commit()
        return link
```

---
## Testing Strategy
| Test Type | Focus |
|-----------|-------|
| Unit (data assembly) | Placeholder mapping, considerandos merge |
| Integration (mock drive) | Generation success path + state mutation |
| Error scenario | Missing tribunal / missing considerandos |
| Signature accumulation | Sequential `firma_count` increments & stamping idempotency |
| Visibility logic | Config vs fallback rules across states |

---
Linked Docs: `PLACEHOLDER_SYSTEM.md`, `INTEGRATIONS.md`, `SERVICES.md`, `MODELS.md`.
