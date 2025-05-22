"""
Migration for adding subestado field to Concurso and estado/subestado fields to DocumentTemplateConfig.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9a4e87a54d21'
down_revision = None  # Replace with your current migration revision ID
branch_labels = None
depends_on = None


def upgrade():
    # Add subestado field to Concurso table

    
    # Add subestado_snapshot field to HistorialEstado table
    op.add_column('historial_estados', sa.Column('subestado_snapshot', sa.Text(), nullable=True))


def downgrade():
    # Remove subestado field from Concurso table
    op.drop_column('concursos', 'subestado')
    
    # Remove estado_al_generar_borrador, subestado_al_generar_borrador, estado_al_subir_firmado, subestado_al_subir_firmado fields from DocumentTemplateConfig table
    op.drop_column('document_template_configs', 'estado_al_generar_borrador')
    op.drop_column('document_template_configs', 'subestado_al_generar_borrador')
    op.drop_column('document_template_configs', 'estado_al_subir_firmado')
    op.drop_column('document_template_configs', 'subestado_al_subir_firmado')
