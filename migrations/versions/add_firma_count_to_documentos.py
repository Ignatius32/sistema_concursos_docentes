"""add firma count to documentos

Revision ID: add_firma_count_docs
Revises: d99133a37629
Create Date: 2023-12-20 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision = 'add_firma_count_docs'
down_revision = 'd99133a37629'
branch_labels = None
depends_on = None


def upgrade():
    # Add firma_count column to documentos_concurso if it doesn't exist
    conn = op.get_bind()
    insp = Inspector.from_engine(conn)
    columns = [c['name'] for c in insp.get_columns('documentos_concurso')]
    
    if 'firma_count' not in columns:
        op.add_column('documentos_concurso', sa.Column('firma_count', sa.Integer(), nullable=False, server_default='0'))
    
    # Only create firmas_documento table if it doesn't exist
    table_names = insp.get_table_names()
    if 'firmas_documento' not in table_names:
        op.create_table('firmas_documento',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('documento_id', sa.Integer(), nullable=False),
            sa.Column('miembro_id', sa.Integer(), nullable=False),
            sa.Column('fecha_firma', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['documento_id'], ['documentos_concurso.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['miembro_id'], ['tribunal_miembros.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )


def downgrade():
    # Remove firma_count column
    conn = op.get_bind()
    insp = Inspector.from_engine(conn)
    columns = [c['name'] for c in insp.get_columns('documentos_concurso')]
    
    if 'firma_count' in columns:
        op.drop_column('documentos_concurso', 'firma_count')
    
    # Drop firmas_documento table if it exists
    table_names = insp.get_table_names()
    if 'firmas_documento' in table_names:
        op.drop_table('firmas_documento')