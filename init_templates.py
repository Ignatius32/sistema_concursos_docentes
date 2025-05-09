"""
Script to initialize the database with default template configurations.
Run this after rebuilding the database.
"""
from app import create_app
from app.models.models import db, DocumentTemplateConfig
import json
from datetime import datetime

def init_templates():
    """Initialize database with default template configurations."""
    app = create_app()
    
    with app.app_context():
        # Check if templates already exist
        if DocumentTemplateConfig.query.first() is not None:
            print("Templates already exist in the database. Skipping initialization.")
            return
        
        # Default templates
        templates = [
            {
                'google_doc_id': '1Sb8TI4AJM6bIu-I-xGB-44ST6AltcQwIGZyN6F-sKHc',
                'document_type_key': 'RESOLUCION_LLAMADO_TRIBUNAL',
                'display_name': 'Resolución Llamado Tribunal Interino',
                'uses_considerandos_builder': True,
                'requires_tribunal_info': True,
                'is_active': True,
                'concurso_visibility': 'INTERINO',
                'is_unique_per_concurso': True,
                'tribunal_visibility_rules': json.dumps({
                    "BORRADOR": {"roles": ["Presidente"], "claustros": ["Docente"]},
                    "PENDIENTE DE FIRMA": {"roles": ["Presidente", "Titular"], "claustros": ["Docente", "No Docente", "Estudiante", "Graduado"]},
                    "FIRMADO": {"roles": ["Presidente", "Titular", "Suplente"], "claustros": ["Docente", "No Docente", "Estudiante", "Graduado"]}
                })
            },
            {
                'google_doc_id': '1Eg0N5s4H_wGEHUZClYZs-jF4ED2pjHbT-KsUoSSLOX8',
                'document_type_key': 'RESOLUCION_LLAMADO_REGULAR',
                'display_name': 'Resolución Llamado Regular',
                'uses_considerandos_builder': True,
                'requires_tribunal_info': False,
                'is_active': True,
                'concurso_visibility': 'REGULAR',
                'is_unique_per_concurso': True,
                'tribunal_visibility_rules': json.dumps({
                    "BORRADOR": {"roles": ["Presidente"], "claustros": ["Docente"]},
                    "PENDIENTE DE FIRMA": {"roles": ["Presidente", "Titular"], "claustros": ["Docente", "No Docente", "Estudiante", "Graduado"]},
                    "FIRMADO": {"roles": ["Presidente", "Titular", "Suplente"], "claustros": ["Docente", "No Docente", "Estudiante", "Graduado"]}
                })
            },
            {
                'google_doc_id': '119a255YfBWEdqu_IEJT1vYWSLAP9KhVk4G5NHPTYD6Q',
                'document_type_key': 'RESOLUCION_TRIBUNAL_REGULAR',
                'display_name': 'Resolución Tribunal Regular',
                'uses_considerandos_builder': True,
                'requires_tribunal_info': True,
                'is_active': True,
                'concurso_visibility': 'REGULAR',
                'is_unique_per_concurso': True,
                'tribunal_visibility_rules': json.dumps({
                    "BORRADOR": {"roles": ["Presidente"], "claustros": ["Docente"]},
                    "PENDIENTE DE FIRMA": {"roles": ["Presidente", "Titular"], "claustros": ["Docente", "No Docente", "Estudiante", "Graduado"]},
                    "FIRMADO": {"roles": ["Presidente", "Titular", "Suplente"], "claustros": ["Docente", "No Docente", "Estudiante", "Graduado"]}
                })
            },
            {
                'google_doc_id': '1Gid4o-lkDfuhNb0g_QHdVvlPoQfS5lR8AtnIxtuLsdI',
                'document_type_key': 'ACTA_CONSTITUCION_TRIBUNAL_REGULAR',
                'display_name': 'Acta Constitución Tribunal Regular',
                'uses_considerandos_builder': False,
                'requires_tribunal_info': True,
                'is_active': True,
                'concurso_visibility': 'REGULAR',
                'is_unique_per_concurso': True,
                'tribunal_visibility_rules': json.dumps({
                    "BORRADOR": {"roles": ["Presidente", "Titular"], "claustros": ["Docente"]},
                    "PENDIENTE DE FIRMA": {"roles": ["Presidente", "Titular"], "claustros": ["Docente", "No Docente", "Estudiante", "Graduado"]},
                    "FIRMADO": {"roles": ["Presidente", "Titular", "Suplente"], "claustros": ["Docente", "No Docente", "Estudiante", "Graduado"]}
                })
            }
        ]
        
        for template_data in templates:
            template = DocumentTemplateConfig(**template_data)
            db.session.add(template)
        
        db.session.commit()
        print(f"Added {len(templates)} default templates to the database.")

if __name__ == "__main__":
    init_templates()
