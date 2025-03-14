"""
Resolution document template data preparers.
Contains functions to prepare data for various resolution document templates.
"""
import os
import json
from app.models.models import Departamento
from app.helpers.text_formatting import format_cargos_text, format_descripcion_cargo
from datetime import datetime

def prepare_data_resolucion_llamado_tribunal(concurso):
    """Prepare data for the resolucion llamado tribunal template."""
    # Check if tribunal members are assigned
    tribunal_members = concurso.tribunal.all()
    if not tribunal_members:
        return None, 'No hay miembros del tribunal asignados para este concurso.'
    
    # Get related data
    departamento = Departamento.query.get(concurso.departamento_id)
    
    # Format dates for display
    current_year = datetime.now().year
    
    # Format tribunal members
    titulares = []
    suplentes = []
    
    for miembro in tribunal_members:
        member_info = f"{miembro.apellido}, {miembro.nombre} (DNI: {miembro.dni})"
        
        if miembro.rol == "Presidente":
            # Presidente always goes first in the titulares list
            titulares.insert(0, f"{member_info}")
        elif miembro.rol == "Suplente":
            suplentes.append(member_info)
        else:  # Vocal
            titulares.append(member_info)
    
    # Join lists with line breaks for the document
    tribunal_titular_text = "\n".join(titulares)
    tribunal_suplentes_text = "\n".join(suplentes)
    
    # Ensure we have the categoria_nombre
    categoria_nombre = concurso.categoria_nombre
    if not categoria_nombre:
        # Load roles_categorias.json data if needed
        json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'roles_categorias.json')
        with open(json_path, 'r', encoding='utf-8') as f:
            roles_data = json.load(f)
        
        # Find categoria name by codigo
        for rol in roles_data:
            for categoria in rol['categorias']:
                if categoria['codigo'] == concurso.categoria:
                    categoria_nombre = categoria['nombre']
                    break
            if categoria_nombre:
                break
    
    # Generate description for the cargo - make sure to include all required parameters
    descripcion_cargo = format_descripcion_cargo(
        concurso.cant_cargos,
        concurso.tipo,
        concurso.categoria,
        categoria_nombre or concurso.categoria,
        concurso.dedicacion
    )
    
    # Call format_cargos_text with all parameters to include dedication info
    cargo_texto = format_cargos_text(
        concurso.cant_cargos, 
        concurso.tipo, 
        concurso.categoria,
        categoria_nombre or concurso.categoria,
        concurso.dedicacion
    )
    
    # Prepare data for template replacements
    data = {
        'cantCargos': cargo_texto,
        'departamento': departamento.nombre,
        'area': concurso.area,
        'orientacion': concurso.orientacion,
        'tipo': concurso.tipo,
        'nombre': categoria_nombre or concurso.categoria,  # Use found name or fallback to codigo
        'codigo': concurso.categoria,
        'tribunal_titular': tribunal_titular_text,
        'tribunal_suplentes': tribunal_suplentes_text,
        'yyyy': str(current_year),
        'expediente': concurso.expediente,
        'descripcion_cargo': descripcion_cargo
    }
    
    return data, None

# Template for any future document type data preparer functions:
"""
def prepare_data_other_document_type(concurso):
    '''Prepare data for another document type template.'''
    # Add document-specific data preparation logic here
    
    # Return prepared data or error message
    data = {
        # ...document-specific fields...
    }
    
    return data, None
"""