"""add concurso_tipo to instructivos

Revision ID: 2b13f2f5a8f0
Revises: 9a4e87a54d21
Create Date: 2025-10-08 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2b13f2f5a8f0'
down_revision = '9a4e87a54d21'
branch_labels = None
depends_on = None


def upgrade():
    # Add nullable concurso_tipo column (REGULAR/INTERINO) to instructivos
    op.add_column('instructivos', sa.Column('concurso_tipo', sa.String(length=20), nullable=True))
    # Create index to speed up resolution queries
    op.create_index('ix_instructivos_concurso_tipo', 'instructivos', ['concurso_tipo'], unique=False)



def downgrade():
    # Drop index then column
    op.drop_index('ix_instructivos_concurso_tipo', table_name='instructivos')
    op.drop_column('instructivos', 'concurso_tipo')
