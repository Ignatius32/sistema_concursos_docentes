"""add_tribunal_folder_id_to_concursos

Revision ID: 75767dd1c07d
Revises: d99133a37629
Create Date: 2025-03-17 10:04:23.345060

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '75767dd1c07d'
down_revision = 'd99133a37629'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('tribunal_miembros', schema=None) as batch_op:
        batch_op.add_column(sa.Column('drive_folder_id', sa.String(length=100), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('tribunal_miembros', schema=None) as batch_op:
        batch_op.drop_column('drive_folder_id')

    # ### end Alembic commands ###
