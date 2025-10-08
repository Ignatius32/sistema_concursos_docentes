"""
One-off safe DB schema patcher.
- Adds instructivos.concurso_tipo if missing + index
- Adds historial_estados.subestado_snapshot if missing (skips if exists)
- Adds required_document_sets.concurso_tipo if missing + index and updates unique constraint (best-effort)

Run:
    source .venv/bin/activate
    python scripts/patch_db_schema.py

Requires app factory and DATABASE_URI to point to your target DB.
"""
import os
import sys

# Ensure project root is on sys.path so `import app` works when running this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app import create_app
from app.models.models import db
from sqlalchemy import inspect, text


def column_exists(inspector, table: str, column: str) -> bool:
    try:
        cols = inspector.get_columns(table)
        return any(c['name'] == column for c in cols)
    except Exception:
        return False

def index_exists(inspector, table: str, index_name: str) -> bool:
    try:
        indexes = inspector.get_indexes(table)
        return any(ix.get('name') == index_name for ix in indexes)
    except Exception:
        return False


def main():
    app = create_app()
    with app.app_context():
        engine = db.engine
        insp = inspect(engine)

        # 1) Add instructivos.concurso_tipo if missing
        if not column_exists(insp, 'instructivos', 'concurso_tipo'):
            print('[patch] Adding column instructivos.concurso_tipo ...')
            try:
                with engine.begin() as conn:
                    conn.execute(text('ALTER TABLE instructivos ADD COLUMN concurso_tipo VARCHAR(20)'))
            except Exception as e:
                # If another process added it, continue.
                print(f'[warn] Could not add column (may already exist): {e}')
            # Refresh inspector after DDL
            insp = inspect(engine)
        else:
            print('[skip] Column instructivos.concurso_tipo already exists')

        # 1b) Add index if missing (re-check with refreshed inspector)
        if not index_exists(insp, 'instructivos', 'ix_instructivos_concurso_tipo'):
            print('[patch] Creating index ix_instructivos_concurso_tipo ...')
            try:
                with engine.begin() as conn:
                    conn.execute(text('CREATE INDEX IF NOT EXISTS ix_instructivos_concurso_tipo ON instructivos (concurso_tipo)'))
            except Exception as e:
                # Fallback for older SQLite without IF NOT EXISTS
                try:
                    with engine.begin() as conn:
                        conn.execute(text('CREATE INDEX ix_instructivos_concurso_tipo ON instructivos (concurso_tipo)'))
                except Exception as e2:
                    print(f'[warn] Could not create index (may already exist): {e2}')
        else:
            print('[skip] Index ix_instructivos_concurso_tipo already exists')

        # 2) Ensure historial_estados.subestado_snapshot exists (to avoid current migration failure)
        if not column_exists(insp, 'historial_estados', 'subestado_snapshot'):
            print('[patch] Adding column historial_estados.subestado_snapshot ...')
            try:
                with engine.begin() as conn:
                    conn.execute(text('ALTER TABLE historial_estados ADD COLUMN subestado_snapshot TEXT'))
            except Exception as e:
                print(f'[warn] Could not add column (may already exist): {e}')
        else:
            print('[skip] Column historial_estados.subestado_snapshot already exists')

        # 3) Add required_document_sets.concurso_tipo if missing and index/unique
        if not column_exists(insp, 'required_document_sets', 'concurso_tipo'):
            print('[patch] Adding column required_document_sets.concurso_tipo ...')
            try:
                with engine.begin() as conn:
                    conn.execute(text('ALTER TABLE required_document_sets ADD COLUMN concurso_tipo VARCHAR(20)'))
            except Exception as e:
                print(f'[warn] Could not add column (may already exist): {e}')
            # Refresh inspector
            insp = inspect(engine)
        else:
            print('[skip] Column required_document_sets.concurso_tipo already exists')

        # 3b) Create index for concurso_tipo
        if not index_exists(insp, 'required_document_sets', 'ix_required_document_sets_concurso_tipo'):
            print('[patch] Creating index ix_required_document_sets_concurso_tipo ...')
            try:
                with engine.begin() as conn:
                    conn.execute(text('CREATE INDEX IF NOT EXISTS ix_required_document_sets_concurso_tipo ON required_document_sets (concurso_tipo)'))
            except Exception:
                try:
                    with engine.begin() as conn:
                        conn.execute(text('CREATE INDEX ix_required_document_sets_concurso_tipo ON required_document_sets (concurso_tipo)'))
                except Exception as e2:
                    print(f'[warn] Could not create index (may already exist): {e2}')
        else:
            print('[skip] Index ix_required_document_sets_concurso_tipo already exists')

        # 3c) Attempt to replace old unique constraint with new one (best-effort; SQLite limitations apply)
        # We will attempt to create a new unique index enforcing (categoria_id, dedicacion, concurso_tipo)
        # without dropping the old constraint to avoid destructive ops in SQLite. This is safe and additive.
        if not index_exists(insp, 'required_document_sets', 'uq_req_docs_categoria_dedicacion_concurso_tipo'):
            print('[patch] Creating unique index uq_req_docs_categoria_dedicacion_concurso_tipo ...')
            try:
                with engine.begin() as conn:
                    conn.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS uq_req_docs_categoria_dedicacion_concurso_tipo ON required_document_sets (categoria_id, dedicacion, concurso_tipo)'))
            except Exception:
                try:
                    with engine.begin() as conn:
                        conn.execute(text('CREATE UNIQUE INDEX uq_req_docs_categoria_dedicacion_concurso_tipo ON required_document_sets (categoria_id, dedicacion, concurso_tipo)'))
                except Exception as e2:
                    print(f'[warn] Could not create unique index: {e2}')

        print('[done] Schema patch completed.')


if __name__ == '__main__':
    main()
