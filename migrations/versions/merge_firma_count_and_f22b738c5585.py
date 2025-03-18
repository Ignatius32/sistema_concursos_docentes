"""merge firma count and f22b738c5585

Revision ID: merge_firma_count_heads
Revises: add_firma_count_docs, f22b738c5585
Create Date: 2023-12-20 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'merge_firma_count_heads'
down_revision = ('add_firma_count_docs', 'f22b738c5585')
branch_labels = None
depends_on = None


def upgrade():
    # This is a merge migration, no need to make schema changes
    pass


def downgrade():
    pass