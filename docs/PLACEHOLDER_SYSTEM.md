# Placeholder Resolution System

This document details how textual placeholders inside Google Docs templates (and related generated documents) are defined, resolved, transformed, and injected into the final document artifacts.

---
## Objectives
- Provide a single canonical source of truth for dynamic concurso / tribunal / postulante data used in documents.
- Support legacy placeholder names while migrating to a normalized naming scheme.
- Enable extension (custom per-template or per-domain placeholders) without editing core generation logic.

---
## High-Level Flow
```
Route Handler -> Generation Service -> build_placeholder_dict(concurso_id)
  -> Load Concurso, related entities (Tribunal, Postulantes, Areas, Categorias)
  -> Aggregate attributes into structured Python dict
  -> Apply formatting helpers (dates, capitalization, joiners)
  -> Inject legacy alias keys (compat layer)
  -> Return dict to document generation -> passed to Drive template fill
```

---
## Source Code References
| File | Purpose |
|------|---------|
| `services/placeholder_resolver.py` | Core assembly + formatting utilities |
| `helpers/text_formatting.py` | Lower/upper accents, normalization, date formatting |
| `document_generation/document_generator.py` | Integrates placeholders into final data payload |

---
## Placeholder Categories
| Category | Examples | Notes |
|----------|----------|-------|
| Concurso Metadata | `CONCURSO_ID`, `CARGO`, `DEDICACION`, `EXPEDIENTE` | Base attributes from Concurso model |
| Tribunal | `TRIBUNAL_PRESIDENTE_NOMBRE`, `TRIBUNAL_MIEMBROS_LIST` | Flattened & list forms |
| Postulantes | `POSTULANTES_CANTIDAD`, `POSTULANTES_LISTADO` | Ordered, filtered (active only) |
| Calendario / Fechas | `FECHA_ACTUAL`, `FECHA_APERTURA`, `FECHA_CIERRE` | Date formatting uniformity |
| Considerandos | `CONSIDERANDOS_TEXTO` | Optional; set only when builder used |
| Resolución / Procedural | `RESOLUCION_NUMERO`, `DICTAMEN_REFERENCIA` | Some may be blank until assigned |
| Institucional | `UNIVERSIDAD_NOMBRE`, `FACULTAD_NOMBRE` | Could centralize in config |
| Derived / Composite | `CARGO_EXTENDIDO`, `DESCRIPCION_LARGA` | Built using concatenation rules |

---
## Naming Convention
- Canonical placeholders: UPPERCASE_WITH_UNDERSCORES.
- Legacy placeholders may use Capitalized or camel/mixed Spanish (e.g., `Expediente`, `CargoExtendido`).
- Strategy: Provide both while templates are migrated.

```python
canonical["CONCURSO_ID"] = str(concurso.id)
legacy_aliases = {"Expediente": canonical["EXPEDIENTE"], "CargoExtendido": canonical["CARGO_EXTENDIDO"]}
placeholders = {**canonical, **legacy_aliases}
```

Deprecation Plan:
1. Emit log warning when legacy key accessed (future enhancement: template scanner).
2. After all templates updated, remove alias injection stage.

---
## Formatting Utilities
| Utility | Description |
|---------|-------------|
| `format_date(date)` | Localized Spanish date (e.g., "14 de marzo de 2025") |
| `list_to_bullets(items)` | Produces bullet string with line breaks for Doc insertion |
| `human_join(list)` | Natural join with commas + 'y' before last item |
| `uppercase_keep_accents` | Ensures uppercase without accent loss |
| `normalize_whitespace` | Collapses multiple spaces/newlines |

Edge Cases: Null dates → placeholder omitted or blank string; empty lists → placeholder blank to avoid artifacts like trailing commas.

---
## Tribunal Placeholders (Example Schema)
For each role (Presidente, Titular, Suplente, Estudiante, Graduado):
```
TRIBUNAL_{ROLE}_NOMBRE
TRIBUNAL_{ROLE}_DNI
TRIBUNAL_{ROLE}_CARGO_ACADEMICO
```
Additionally:
```
TRIBUNAL_MIEMBROS_LIST  # "Dr. Ana Perez (Presidente); Prof. Juan Gomez (Titular)"
TRIBUNAL_MIEMBROS_BULLETS  # Bullet-separated variant
```
If a role unfilled: Placeholder set to empty string (never the literal 'None').

---
## Postulantes Placeholders
```
POSTULANTES_CANTIDAD
POSTULANTES_LISTADO              # "Apellido, Nombre (DNI ####)" per line
POSTULANTES_APELLIDOS            # Comma-separated last names
POSTULANTES_LISTADO_BULLETS
```
Filtering: Only active / not withdrawn postulantes should appear (confirm with model flags; adjust resolver to exclude logically deleted entries).
Ordering: Alphabetical by last name, stable.

---
## Considerandos Integration
When considerandos builder used:
1. Raw selected paragraphs combined with blank line separators.
2. Placeholder substitution inside that text (allow nested placeholders in considerandos segments).
3. Assigned to `CONSIDERANDOS_TEXTO`.
4. If builder required and empty -> raise / return error.

---
## Extensibility Patterns
| Need | Approach |
|------|----------|
| Per-template custom placeholder | Add optional hook: `TemplatePlaceholderPlugin(interface)` registered by `document_type_key` |
| Calculated field requiring external API | Lazy evaluation wrapper (call only if placeholder present in template scan) |
| Localization | Pass `locale` to resolver; configure date/number formatting |
| Security filtering (public vs internal doc) | Provide `mode` flag trimming sensitive placeholders |

Proposed Interface:
```python
class PlaceholderProvider(Protocol):
    def provide(self, concurso, context) -> dict: ...
```
Resolver would iterate registry: `for provider in providers: data.update(provider.provide(concurso, ctx))`.

---
## Validation & Auditing
Add management command / script to:
1. Fetch all active templates from Drive.
2. Parse text for `{{PLACEHOLDER}}` patterns.
3. Diff against supported canonical set.
4. Emit report: unused, unknown, legacy.

Benefits: Early detection of typos (`{{POSTULANTE_CANTIDAD}}` vs `{{POSTULANTES_CANTIDAD}}`).

---
## Error Handling Guidelines
| Issue | Handling |
|-------|----------|
| Missing related entity (e.g., tribunal not set) | Provide empty placeholders + upstream validation in generation stage |
| Null optional field | Return empty string (avoid 'None') |
| Large list overflow | Optionally truncate with note (future) |

---
## Performance Considerations
- Single DB query expansion strategy: eager-load relationships to cut N+1 (e.g., join tribunal members, postulantes).
- Cache placeholders per (concurso_id, snapshot_hash) within request scope.
- Potential long lists (hundreds of postulantes) → join operations are still O(n) simple string building; acceptable.

---
## Testing Recommendations
| Test | Purpose |
|------|---------|
| Canonical basic set | Ensure mandatory keys always present |
| Legacy alias parity | Each legacy maps same value as canonical |
| Tribunal empty roles | Placeholders blank not 'None' |
| Postulante ordering | Deterministic alphabetical result |
| Considerandos placeholder nesting | Ensure substitution occurs inside provided paragraphs |
| Performance quick check | Resolver under threshold for N=100 postulantes |

---
## Migration Checklist (Legacy → Canonical)
1. Generate audit report of templates.
2. Update templates replacing legacy keys.
3. Enable logging of legacy access (temporary).
4. Remove alias injection stage after 100% migration.
5. Update docs (this file + DOCUMENT_GENERATION.md) to remove legacy section.

---
## Future Enhancements
- Dynamic placeholder discovery (scan template before building full dict → lazy providers).
- GraphQL-like query definition per template to drive data fetch cost.
- Jinja2-safe filter library for inline formatting (`{{ FECHA|upper }}`).
- Placeholder security classification (PUBLIC, INTERNAL) for controlled redaction.

Linked Docs: `DOCUMENT_GENERATION.md`, `INTEGRATIONS.md`, `SERVICES.md`.
