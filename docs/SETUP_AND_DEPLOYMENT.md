# Setup & Deployment Guide

Comprehensive instructions for local development, testing, and production deployment of the Sistema de Concursos Docentes.

## 1. Technology Stack
- Python 3.9+ (prod currently references 3.9 site-packages path)
- Flask + Flask-Migrate (Alembic)
- SQLAlchemy (SQLite default; can escalate to PostgreSQL)
- Keycloak (OIDC for auth + Admin API for provisioning)
- Google Apps Script endpoint (single multiplexed API for Drive + email operations)
- Apache + mod_wsgi (production)

## 2. Repository Layout (Essentials)
```
run.py / wsgi.py              - Entrypoints (dev vs production)
app/__init__.py               - App factory & bootstrap
app/models/models.py          - ORM models (monolithic; see refactor plan)
app/routes/                   - Blueprints
app/services/                 - Business services
app/integrations/             - External system adapters (Keycloak, Google Drive)
app/document_generation/      - Document generator logic
migrations/                   - Alembic migration environment
instance/concursos.db         - Default SQLite database (ignored by VCS)
```

## 3. Environment Variables (.env)
Minimum required:
```
SECRET_KEY=change-me
APPLICATION_ROOT=/selecciones-docentes
# Database (optional override)
DATABASE_URI=sqlite:///instance/concursos.db
# Keycloak
KEYCLOAK_SERVER_URL=https://keycloak.example.com/
KEYCLOAK_REALM=your-realm
KEYCLOAK_CLIENT_ID=portal-client
KEYCLOAK_CLIENT_SECRET=client-secret
KEYCLOAK_ADMIN_CLIENT_ID=admin-cli-client
KEYCLOAK_ADMIN_CLIENT_SECRET=admin-cli-secret
KEYCLOAK_REDIRECT_URI=https://yourhost/selecciones-docentes/auth/callback
KEYCLOAK_POST_LOGOUT_REDIRECT_URI=https://yourhost/selecciones-docentes/
KEYCLOAK_TRIBUNAL_ROLE=tribunal_member
KEYCLOAK_ADMIN_ROLE=app_admin
# Google Drive
GOOGLE_DRIVE_SECURE_TOKEN=secure-drive-token
# Password reset tokens
RESET_TOKEN_SECRET=long-random-string
# Optional: Google Drive folders (created dynamically otherwise)
GOOGLE_DRIVE_CVS_FOLDER_ID=
```

## 4. Local Development
1. Create virtual environment:
```
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
2. Create `.env` (see above). For quick local auth development you may disable Keycloak (comment out init) or use a test realm.
3. Initialize DB & migrations:
```
flask db upgrade
```
4. Seed reference data (idempotent in `init_app_data`):
```
flask init-categories
flask init-departments
flask init-templates  # if using script; or rely on UI import/export
```
5. Run dev server:
```
flask run  # or python run.py
```

## 5. Alembic Migrations
Generate migration after model changes:
```
flask db migrate -m "Add field X"
flask db upgrade
```
If SQLite foreign key / type alterations needed, consider offline rebuild strategy or move to PostgreSQL.

## 6. Production Deployment (Apache + mod_wsgi)
### Directory Layout
```
/var/www/concursos-docentes/
  venv/
  wsgi.py
  app/
  instance/concursos.db
  app.log (writeable by Apache user)
```
### Apache Excerpt
```
WSGIDaemonProcess concursos_docentes_app python-home=/var/www/concursos-docentes/venv python-path=/var/www/concursos-docentes
<Location /selecciones-docentes>
    WSGIProcessGroup concursos_docentes_app
</Location>
WSGIScriptAlias /selecciones-docentes /var/www/concursos-docentes/wsgi.py
Alias /selecciones-docentes/static /var/www/concursos-docentes/app/static
```
Reload after changes:
```
sudo systemctl reload apache2
```
Verify logs at `/var/www/concursos-docentes/app.log`.

### Permissions
Ensure Apache user (www-data) can read project and write:
- `app.log`
- `instance/concursos.db` (and journal)
- Any upload/temp directories if added later

### Security Headers (Recommended)
Add in Apache vhost:
```
Header always set X-Frame-Options SAMEORIGIN
Header always set X-Content-Type-Options nosniff
Header always set Referrer-Policy strict-origin-when-cross-origin
Header always set Content-Security-Policy "default-src 'self' https://accounts.google.com https://fonts.googleapis.com https://fonts.gstatic.com; img-src 'self' data: https://*.googleusercontent.com; script-src 'self' 'unsafe-inline' https://apis.google.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;"
```
Adjust CSP when adding new CDNs.

## 7. Keycloak Configuration Checklist
Realm:
- Create client (confidential) for application (OIDC) with:
  - Valid redirect URI: `https://host/selecciones-docentes/auth/callback`
  - Web origins: `https://host`
- Create service account capable admin client for provisioning (client credentials).
- Roles:
  - `tribunal_member` (client role)
  - `app_admin` (client or realm role; must match configuration)
- Email settings configured if relying on Keycloak execute-actions emails.

## 8. Google Drive Integration
The system calls a single Apps Script endpoint with `action` parameter variants:
- `createFolder`, `createNestedFolder`
- `uploadFile`, `overwriteFile`, `getFileContent`, `deleteFile`
- `sendEmail`
Maintain the script and rotate `GOOGLE_DRIVE_SECURE_TOKEN` if exposed.

### Resilience Recommendations
- Add retry/backoff wrapper for transient 5xx / network errors.
- Log correlation ID (include concurso_id/doc_tipo in each call).

## 9. Document Template Lifecycle
1. Configure templates via UI (`/admin/templates`) or JSON import/export.
2. Each template stores Google Doc ID + behavioral flags.
3. Generate -> BORRADOR (borrador_file_id) -> progression to signing -> FIRMADO.
4. Automatic estado/subestado mutation per template rules (see `DocumentTemplateConfig`).

## 10. Password Reset & Access Provisioning
Two channels:
- Custom token email (Drive-based) via `PasswordResetService` (preferred unified branding, independent of Keycloak email config).
- Keycloak execute-actions fallback.
Tokens: base64 payload + SHA256 signature using `RESET_TOKEN_SECRET`.
Rotation: change secret + expire prior tokens (optionally implement blacklist table).

## 11. Placeholder & Notification Flow (Summary)
Documented in detail in `PLACEHOLDER_SYSTEM.md`. Core principle: a single resolver returns canonical keys consumed by documents & notifications; legacy name mapping handled in generator.

## 12. Logging & Monitoring
Current: Python logging to file + stderr (Apache). Improve by:
- JSON formatting + log rotation
- Distinguish integration failures vs business validation
- Capture Drive latency metrics

## 13. Scaling Considerations
- Session: default cookie-based; if storing larger identity objects, consider server-side (Redis) store.
- File operations: currently synchronous; heavy usage suggests task queue (RQ / Celery) for long operations (bulk notifications, mass document generation).
- Database: upgrade SQLite -> PostgreSQL for concurrency + migrations safety.

## 14. Backup & Recovery
SQLite strategy:
- Daily snapshot of `instance/concursos.db` + `migrations/` folder
- Offsite copy of templates JSON export & Drive folder tree IDs
Future: switch to managed PostgreSQL with PITR.

## 15. Deployment Automation (Future Roadmap)
- Add `Makefile` or Fabric script: test, lint, build, deploy stages
- CI pipeline: run pytest + flake8 + safety
- IaC: Ansible role for Apache + app provisioning

## 16. Quick Troubleshooting Matrix
| Symptom | Likely Cause | Action |
|---------|--------------|--------|
| 404 under /selecciones-docentes | APPLICATION_ROOT mismatch | Verify `.env` + Apache alias prefix |
| Keycloak login loop | Redirect URI mismatch | Check client redirect settings |
| Drive folder not created | Invalid secure token | Rotate / verify `GOOGLE_DRIVE_SECURE_TOKEN` |
| Templates not listed | DB empty | Run `flask init-templates` or import JSON |
| Password emails not arriving | Drive script failure or email blocked | Check script logs / fallback to execute-actions |
| Estado/subestado not updating | Template flags unset | Edit template config, confirm fields |

## 17. Migration from Legacy APIs
`init_considerandos_and_deptoheads.py` migrates remote JSON to local tables. After success:
- Disable external calls
- Manage via `/admin/api-data/` interface

## 18. Security Hardening Checklist
- Enforce HTTPS (HSTS header)
- Rotate secrets quarterly
- Principle of least privilege for Keycloak service account
- Validate file IDs against expected folder ownership (prevent arbitrary overwrite)
- Add CSRF protection (Flask-WTF already partially in use; audit coverage)

## 19. Environment Promotion Strategy
Envs: dev -> staging -> prod:
- Maintain separate Keycloak realm/clients per env
- Use template export/import JSON to migrate configuration
- Keep migrations forward-only; tag releases

---
For additional subsystem detail see: `ARCHITECTURE_OVERVIEW.md`, `INTEGRATIONS.md`, `DOCUMENT_GENERATION.md`, and related docs. Keep this guide updated with every operational or infrastructure change.
