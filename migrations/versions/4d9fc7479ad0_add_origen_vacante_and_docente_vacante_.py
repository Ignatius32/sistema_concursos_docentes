"""add_origen_vacante_and_docente_vacante_to_concursos
Revision ID: 4d9fc7479ad0
Revises: caa7746b04ac
Create Date: 2025-03-12 19:23:23.152648
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '4d9fc7479ad0'
down_revision = 'caa7746b04ac'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [column['name'] for column in inspector.get_columns('concursos')]
    
    with op.batch_alter_table('concursos', schema=None) as batch_op:
        # Only add columns if they don't already exist
        if 'origen_vacante' not in columns:
            batch_op.add_column(sa.Column('origen_vacante', sa.String(length=50), nullable=True))
        if 'docente_vacante' not in columns:
            batch_op.add_column(sa.Column('docente_vacante', sa.String(length=100), nullable=True))


def downgrade():
    with op.batch_alter_table('concursos', schema=None) as batch_op:
        batch_op.drop_column('docente_vacante')
        batch_op.drop_column('origen_vacante')
