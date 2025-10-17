"""add fecha_apertura_inscripcion to concursos

Revision ID: 3c7a1d9e4b10
Revises: 2b13f2f5a8f0
Create Date: 2025-10-17 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '3c7a1d9e4b10'
down_revision = '2b13f2f5a8f0'
branch_labels = None
depends_on = None


def upgrade():
    # Add nullable fecha_apertura_inscripcion column to concursos
    op.add_column('concursos', sa.Column('fecha_apertura_inscripcion', sa.Date(), nullable=True))


def downgrade():
    # Drop fecha_apertura_inscripcion column
    op.drop_column('concursos', 'fecha_apertura_inscripcion')
