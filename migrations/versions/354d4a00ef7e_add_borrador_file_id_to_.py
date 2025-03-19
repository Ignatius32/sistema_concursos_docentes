"""Add borrador_file_id to DocumentoConcurso

Revision ID: 354d4a00ef7e
Revises: 
Create Date: 2025-03-19 19:32:36.986521

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '354d4a00ef7e'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('document_type_configs')
    with op.batch_alter_table('documentos_concurso', schema=None) as batch_op:
        batch_op.add_column(sa.Column('borrador_file_id', sa.String(length=100), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('documentos_concurso', schema=None) as batch_op:
        batch_op.drop_column('borrador_file_id')

    op.create_table('document_type_configs',
    sa.Column('id', sa.INTEGER(), nullable=False),
    sa.Column('tipo', sa.VARCHAR(length=50), nullable=False),
    sa.Column('managed_by', sa.VARCHAR(length=20), nullable=True),
    sa.Column('created_at', sa.DATETIME(), nullable=True),
    sa.Column('updated_at', sa.DATETIME(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tipo')
    )
    # ### end Alembic commands ###
