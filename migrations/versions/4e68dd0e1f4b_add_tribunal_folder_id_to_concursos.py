"""add_tribunal_folder_id_to_concursos

Revision ID: 4e68dd0e1f4b
Revises: 75767dd1c07d
Create Date: 2025-03-17 11:00:38.325955

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4e68dd0e1f4b'
down_revision = '75767dd1c07d'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('concursos', schema=None) as batch_op:
        batch_op.add_column(sa.Column('tribunal_folder_id', sa.String(length=100), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('concursos', schema=None) as batch_op:
        batch_op.drop_column('tribunal_folder_id')

    # ### end Alembic commands ###
