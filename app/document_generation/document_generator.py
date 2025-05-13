"""
Base document generation functionality for concursos docentes application.
Contains core functions for generating documents from templates and specific document type handlers.
"""
from datetime import datetime
from flask_login import current_user
from app.models.models import db, HistorialEstado, DocumentoConcurso, Concurso, Departamento, TribunalMiembro, DocumentTemplateConfig
from app.integrations.google_drive import GoogleDriveAPI
from app.services.placeholder_resolver import get_core_placeholders, replace_text_with_placeholders
import json
import os
import traceback

drive_api = GoogleDriveAPI()

# Fallback document configurations for backward compatibility
DOCUMENT_CONFIG_FALLBACK = {
    'RESOLUCION_LLAMADO_TRIBUNAL': {
        'requires_tribunal': True,
    },
    'RESOLUCION_LLAMADO_REGULAR': {
        'requires_tribunal': False,
    },
    'RESOLUCION_TRIBUNAL_REGULAR': {
        'requires_tribunal': True,
    },
    'ACTA_CONSTITUCION_TRIBUNAL_REGULAR': {
        'requires_tribunal': True,
    },
    # Add more document types here with their configurations
}

def prepare_data_for_document(concurso_id, document_type):
    """
    Prepare data for document templates based on document type.
    Uses the centralized placeholder resolver to get consistent data across all documents.
    
    Args:
        concurso_id (int): ID of the concurso
        document_type (str): Type of document to prepare data for
        
    Returns:
        tuple: (data_dict, error_message) - The data dictionary to use in template or error message
    """
    concurso = Concurso.query.get(concurso_id)
    if not concurso:
        return None, "Concurso no encontrado"

    # Get document configuration from database
    template_config = DocumentTemplateConfig.query.filter_by(document_type_key=document_type).first()
    
    # If no template found in database, use fallback configuration
    if template_config:
        doc_config = {
            'requires_tribunal': template_config.requires_tribunal_info,
            'uses_considerandos_builder': template_config.uses_considerandos_builder
        }
    else:
        # Fallback to hardcoded configuration if not found in database
        doc_config = DOCUMENT_CONFIG_FALLBACK.get(document_type, {'requires_tribunal': True, 'uses_considerandos_builder': False})
    
    # Check if tribunal members are required and assigned
    if doc_config['requires_tribunal']:
        tribunal_members = concurso.asignaciones_tribunal.all()
        if not tribunal_members:
            return None, 'No hay miembros del tribunal asignados para este concurso.'
    
    # Get core placeholders from the central resolver
    placeholders_data = get_core_placeholders(concurso_id)
    
    # Add any document-type specific placeholders if needed
    if document_type == 'ACTA_CONSTITUCION_TRIBUNAL_REGULAR':
        # Special handling for acta constitucion if needed
        pass
    
    # For backward compatibility and to ensure all templates work correctly
    # Map placeholder keys to the expected template variable names
    # This mapping can be removed once all templates are updated to use the new placeholder naming convention
    data = {}
    
    # Add all placeholder data
    for key, value in placeholders_data.items():
        data[key] = value
    
    # Add additional mappings for backward compatibility
    template_key_mapping = {
        'expediente': 'Expediente',
        'departamento_nombre': 'departamento',
        'area': 'Area',
        'orientacion': 'Orientacion',
        'categoria_codigo': 'codigo',
        'categoria_nombre': 'nombre',
        'dedicacion': 'Dedicacion',
        'cant_cargos_texto': 'cantCargos',
        'tribunal_titulares_lista': 'tribunal_titular',
        'tribunal_suplentes_lista': 'tribunal_suplentes',
        'current_year': 'yyyy',
    }
    
    # Apply mappings to ensure all templates work with the new structure
    for new_key, old_key in template_key_mapping.items():
        if new_key in placeholders_data:
            data[old_key] = placeholders_data[new_key]
    
    return data, None

def generar_documento_desde_template(concurso_id, template_name, doc_tipo, prepare_data_func=None, considerandos_text=None):
    """
    Generic function to generate a document from a template.
    
    Args:
        concurso_id (int): ID of the concurso
        template_name (str): Name of the template in Google Drive (will be replaced by doc ID from database)
        doc_tipo (str): Type of document for database record
        prepare_data_func (function, optional): Function that prepares the data for the template.
                                               If None, uses the default prepare_data_for_document
        considerandos_text (str, optional): Compiled considerandos text to add to the document
        
    Returns:
        tuple: (success, message, url) - Indicates success/failure, message, and URL if successful
    """
    try:
        concurso = Concurso.query.get_or_404(concurso_id)
        
        if not concurso.borradores_folder_id:
            return False, 'El concurso no tiene una carpeta de borradores asociada.', None
            
        # Get template configuration from database
        template_config = DocumentTemplateConfig.query.filter_by(document_type_key=doc_tipo).first()
        
        # If template_config isn't found, return an error
        if not template_config:
            return False, f'No se encontró una plantilla configurada para el tipo de documento: {doc_tipo}', None
        
        # Use the Google Doc ID directly from the database
        template_doc_id = template_config.google_doc_id
        
        # If no prepare_data_function is provided, use the default one
        if prepare_data_func is None:
            prepare_data_func = prepare_data_for_document
        
        data, validation_message = prepare_data_func(concurso_id, doc_tipo)
        
        # Check if data preparation succeeded
        if not data:
            return False, validation_message, None        # Use the central placeholder resolver to get all data
        placeholders_data = get_core_placeholders(concurso_id)
        
        # Add committee and council information to placeholders data for template
        # Format committee date
        if concurso.fecha_comision_academica:
            fecha_comision = concurso.fecha_comision_academica.strftime('%d/%m/%Y')
            data['fecha_comision_academica'] = fecha_comision
            placeholders_data['fecha_comision_academica'] = fecha_comision
        else:
            data['fecha_comision_academica'] = ""
            placeholders_data['fecha_comision_academica'] = ""
            
        # Format council date
        if concurso.fecha_consejo_directivo:
            fecha_consejo = concurso.fecha_consejo_directivo.strftime('%d/%m/%Y')
            data['fecha_consejo_directivo'] = fecha_consejo
            placeholders_data['fecha_consejo_directivo'] = fecha_consejo
        else:
            data['fecha_consejo_directivo'] = ""
            placeholders_data['fecha_consejo_directivo'] = ""
            
        # Add text fields
        data['despacho_comision_academica'] = concurso.despacho_comision_academica or ""
        data['sesion_consejo_directivo'] = concurso.sesion_consejo_directivo or ""
        data['despacho_consejo_directivo'] = concurso.despacho_consejo_directivo or ""
        placeholders_data['despacho_comision_academica'] = concurso.despacho_comision_academica or ""
        placeholders_data['sesion_consejo_directivo'] = concurso.sesion_consejo_directivo or ""
        placeholders_data['despacho_consejo_directivo'] = concurso.despacho_consejo_directivo or ""

        # Add sustanciacion data to template data regardless of considerandos
        if concurso.sustanciacion:
            sustanciacion = concurso.sustanciacion
            # Format dates
            constitucion_fecha = sustanciacion.constitucion_fecha.strftime('%d/%m/%Y %H:%M') if sustanciacion.constitucion_fecha else '-'
            sorteo_fecha = sustanciacion.sorteo_fecha.strftime('%d/%m/%Y %H:%M') if sustanciacion.sorteo_fecha else '-'
            exposicion_fecha = sustanciacion.exposicion_fecha.strftime('%d/%m/%Y %H:%M') if sustanciacion.exposicion_fecha else '-'
            
            # Add to template data directly
            data.update({
                'constitucion_fecha': constitucion_fecha,
                'constitucion_lugar': sustanciacion.constitucion_lugar or '-',
                'constitucion_virtual_link': sustanciacion.constitucion_virtual_link or '-',
                'sorteo_fecha': sorteo_fecha,
                'sorteo_lugar': sustanciacion.sorteo_lugar or '-',
                'sorteo_virtual_link': sustanciacion.sorteo_virtual_link or '-',
                'exposicion_fecha': exposicion_fecha,
                'exposicion_lugar': sustanciacion.exposicion_lugar or '-',
                'exposicion_virtual_link': sustanciacion.exposicion_virtual_link or '-',
                'temas_exposicion': sustanciacion.temas_exposicion.replace('|', '\n') if sustanciacion.temas_exposicion else '-'
            })        # Use the placeholder data for postulantes, which is already provided by the resolver
        # Map to legacy field names for backward compatibility
        data['postulantes_lista'] = placeholders_data.get('postulantes_lista_completa', '-')
        data['postulantes_activos'] = placeholders_data.get('postulantes_activos_lista', '-')
          # No need to query and process tribunal members again as they're already in the placeholders
        # Just ensure backward compatibility with field names
        
        # Check if document type requires tribunal members
        # Get document config from database first, fallback to hardcoded if not found
        template_config = DocumentTemplateConfig.query.filter_by(document_type_key=doc_tipo).first()
        
        if template_config:
            doc_config = {
                'requires_tribunal': template_config.requires_tribunal_info,
                'uses_considerandos_builder': template_config.uses_considerandos_builder
            }
        else:
            doc_config = DOCUMENT_CONFIG_FALLBACK.get(doc_tipo, {'requires_tribunal': True, 'uses_considerandos_builder': False})
            
        # Map central placeholder fields to legacy field names if they don't exist already
        if 'tribunal_titular' not in data and 'tribunal_titulares_lista' in placeholders_data:
            data['tribunal_titular'] = placeholders_data['tribunal_titulares_lista']
            
        if 'tribunal_suplentes' not in data and 'tribunal_suplentes_lista' in placeholders_data:
            data['tribunal_suplentes'] = placeholders_data['tribunal_suplentes_lista']
            
        if 'tribunal_presidente' not in data and 'tribunal_presidente' in placeholders_data:
            data['tribunal_presidente'] = placeholders_data['tribunal_presidente']
            
        # Process considerandos text if provided - replace placeholders with actual values
        if considerandos_text:
            # Use the centralized placeholder resolver to replace placeholders in considerandos
            processed_considerandos = replace_text_with_placeholders(considerandos_text, placeholders_data)
            
            # Add processed considerandos to the main data dictionary
            data['considerandos'] = processed_considerandos        # Add the placeholders directly to template data for direct replacement
        # This ensures backward compatibility with existing templates
        departamento = Departamento.query.get(concurso.departamento_id) if concurso.departamento_id else None
        departamento_nombre = departamento.nombre if departamento else ""
        
        # Update template data with any specific template variables needed for compatibility
        for key, value in placeholders_data.items():
            if key not in data:
                data[key] = value
        
        # For backward compatibility, add some common keys with different capitalization
        compatibility_keys = {
            'Docente_que_genera_vacante': placeholders_data.get('docente_que_genera_vacante', ''),
            'licencia': placeholders_data.get('licencia', ''),
            'Origen_vacante': placeholders_data.get('origen_vacante', ''),
            'Expediente': placeholders_data.get('expediente', ''),
            'Departamento': departamento_nombre,
            'Area': placeholders_data.get('area', ''),
            'Orientacion': placeholders_data.get('orientacion', ''),
            'Categoria': placeholders_data.get('categoria_nombre', ''),
            'Dedicacion': placeholders_data.get('dedicacion', ''),
            'CantCargos': str(placeholders_data.get('cant_cargos_numero', '')),
            'TKD': placeholders_data.get('tkd', '')
        }
        
        # Add compatibility keys to data
        data.update(compatibility_keys)# Generate file name with timestamp
        file_name = f"{doc_tipo.replace('_', ' ').title()}_Concurso_{concurso.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
        
        # Check if the document uses considerandos builder but no considerandos were provided
        if template_config and template_config.uses_considerandos_builder and not considerandos_text:
            return False, 'Este documento requiere Considerandos. Por favor utilice el Constructor de Considerandos.', None
        
        # Print debug information about the data being sent to the template
        print(f"Debug - Template data keys: {data.keys()}")
        print(f"Debug - Tribunal data: tribunal_titular={data.get('tribunal_titular', 'MISSING')}, tribunal_suplentes={data.get('tribunal_suplentes', 'MISSING')}")
        print(f"Debug - Using template ID: {template_doc_id} for document type: {doc_tipo}")
        
        # Use API to create document from template in borradores folder - pass the template ID directly
        file_id, web_link = drive_api.create_document_from_template(
            template_doc_id,  # Now passing the Google Doc ID directly
            data,
            concurso.borradores_folder_id,
            file_name
        )
        
        # Create document record with borrador_file_id
        documento = DocumentoConcurso(
            concurso=concurso,
            tipo=doc_tipo,
            url=web_link,
            estado='BORRADOR',
            borrador_file_id=file_id  # Store as borrador_file_id instead of file_id
        )
        db.session.add(documento)
        
        # Add entry to history
        historial = HistorialEstado(
            concurso=concurso,
            estado="DOCUMENTO_GENERADO",
            observaciones=f"{doc_tipo.replace('_', ' ').title()} generado por {current_user.username}"
        )
        db.session.add(historial)
        db.session.commit()
        
        return True, f'Documento generado exitosamente.', web_link
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        db.session.rollback()
        return False, f'Error al generar el documento: {str(e)}', None