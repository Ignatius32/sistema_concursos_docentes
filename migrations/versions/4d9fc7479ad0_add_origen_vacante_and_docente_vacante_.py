"""add_origen_vacante_and_docente_vacante_to_concursos

Revision ID: 4d9fc7479ad0
Revises: f83307e6cd84
Create Date: 2025-03-12 19:23:23.152648

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4d9fc7479ad0'
down_revision = 'f83307e6cd84'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('concursos', schema=None) as batch_op:
        batch_op.add_column(sa.Column('origen_vacante', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('docente_vacante', sa.String(length=100), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('concursos', schema=None) as batch_op:
        batch_op.drop_column('docente_vacante')
        batch_op.drop_column('origen_vacante')

    # ### end Alembic commands ###
