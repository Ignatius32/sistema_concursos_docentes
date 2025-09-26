# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog (https://keepachangelog.com/en/1.0.0/) and this project adheres (aspirationally) to Semantic Versioning (https://semver.org/).

## [Unreleased]
### Added
- (Placeholder) Service/repository abstraction work (to be implemented).
- Planned: Structured logging & metrics hooks.
 - Configurable required documents feature (RequiredDocumentSet model, service, admin UI, PDF & routes integration).
 - Admin UI for managing required documents per categoría/dedicación (precedence based resolution with global fallback).
 - Endpoints: /admin/required-docs (CRUD + catalog) and navigation link.
 - New model: RequiredDocumentSet with versioning metadata and precedence similar to Instructivo.

### Changed
- Pending future refactors (document when executed).
 - PDF generation now resolves required_docs via service before falling back to legacy roles_categorias.json.
 - Postulantes y Tribunal routes usan servicio para documentación requerida.

### Removed
- Legacy placeholder aliases (planned – document once removed).

### Security
- Add any security-related notes here once features land.

## [0.1.0] - 2025-09-26
### Added
- Comprehensive documentation suite:
  - ARCHITECTURE_OVERVIEW.md
  - SETUP_AND_DEPLOYMENT.md
  - MODELS.md
  - ROUTES.md
  - SERVICES.md
  - INTEGRATIONS.md
  - DOCUMENT_GENERATION.md
  - PLACEHOLDER_SYSTEM.md
  - TESTING.md
  - REFACTORING_GUIDE.md
  - AI_CONTRIBUTION_GUIDE.md
  - TECH_DEBT_TODO.md
- Document generation state/subestado coupling documentation.
- Technical debt backlog with prioritization.

### Changed
- README updated to reflect new documentation and features (estado/subestado handling).

### Deprecated
- Legacy placeholder names retained temporarily (marked for removal in future release).

### Fixed
- N/A (initial changelog entry).

### Security
- Clarified environment variable usage for sensitive tokens in documentation.

[Unreleased]: https://example.com/compare/v0.1.0...HEAD
[0.1.0]: https://example.com/releases/tag/v0.1.0
