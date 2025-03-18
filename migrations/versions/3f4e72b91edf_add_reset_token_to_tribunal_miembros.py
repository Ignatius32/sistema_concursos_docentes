"""add_reset_token_to_tribunal_miembros

Revision ID: 3f4e72b91edf
Revises: bf8de14c15e0
Create Date: 2023-07-21 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3f4e72b91edf'
down_revision = 'bf8de14c15e0'
branch_labels = None
depends_on = None


def upgrade():
    # Add reset_token column to tribunal_miembros table
    with op.batch_alter_table('tribunal_miembros', schema=None) as batch_op:
        batch_op.add_column(sa.Column('reset_token', sa.String(length=100), nullable=True))


def downgrade():
    # Remove reset_token column from tribunal_miembros table
    with op.batch_alter_table('tribunal_miembros', schema=None) as batch_op:
        batch_op.drop_column('reset_token')