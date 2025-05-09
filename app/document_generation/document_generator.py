"""
Base document generation functionality for concursos docentes application.
Contains core functions for generating documents from templates and specific document type handlers.
"""
from datetime import datetime
from flask_login import current_user
from app.models.models import db, HistorialEstado, DocumentoConcurso, Concurso, Departamento, TribunalMiembro, DocumentTemplateConfig
from app.integrations.google_drive import GoogleDriveAPI
from app.helpers.api_services import get_departamento_heads_data
from app.helpers.text_formatting import format_descripcion_cargo, format_cargos_text
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
    """
    concurso = Concurso.query.get(concurso_id)
    if not concurso:
        return None, "Concurso no encontrado"

    # Get related data
    departamento = Departamento.query.get(concurso.departamento_id)
    departamento_nombre = departamento.nombre if departamento else ""
    
    # Add department head information from the API
    departamento_heads = get_departamento_heads_data()
    dept_head = None
    if departamento_heads:
        # Find matching department head
        for head in departamento_heads:
            if head.get('departamento', '').strip().lower() == departamento_nombre.strip().lower():
                dept_head = head
                break
                
    # Basic data common to all document types
    data = {
        'concurso_id': concurso.id,
        'res_llamado_interino': concurso.nro_res_llamado_interino or '',
        'res_llamado_regular': concurso.nro_res_llamado_regular or '',
        'res_tribunal_regular': concurso.nro_res_tribunal_regular or '',
        'resp_departamento': dept_head.get('responsable', '') if dept_head else '',
        'prefijo_resp_departamento': dept_head.get('prefijo', '') if dept_head else ''
    }

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
    
    # Get related data
    departamento = Departamento.query.get(concurso.departamento_id)
    
    # Format dates for display
    current_year = datetime.now().year
    # Format tribunal members if required
    tribunal_titular_text = ""
    tribunal_suplentes_text = ""
    
    # Initialize categorized lists for different claustros
    tribunal_titular_docente = []
    tribunal_titular_estudiante = []
    tribunal_suplente_docente = []
    tribunal_suplente_estudiante = []
    
    if doc_config['requires_tribunal']:
        titulares = []
        suplentes = []
        for miembro in concurso.asignaciones_tribunal.all():
            member_info = f"{miembro.persona.apellido}, {miembro.persona.nombre} (DNI: {miembro.persona.dni})"
            
            # Categorize by role and claustro
            if miembro.rol == "Presidente":
                # Presidente always goes first in the titulares list
                titulares.insert(0, f"{member_info}")
                # Presidente is typically a docente
                tribunal_titular_docente.insert(0, f"{member_info}")
            elif miembro.rol == "Titular":
                titulares.append(member_info)
                # Categorize by claustro
                if miembro.claustro == "Estudiante":
                    tribunal_titular_estudiante.append(member_info)
                else:  # Default to Docente if not specified or is Docente
                    tribunal_titular_docente.append(member_info)
            elif miembro.rol == "Suplente":
                suplentes.append(member_info)
                # Categorize by claustro
                if miembro.claustro == "Estudiante":
                    tribunal_suplente_estudiante.append(member_info)
                else:  # Default to Docente if not specified or is Docente
                    tribunal_suplente_docente.append(member_info)
        
        # Join lists with line breaks for the document
        tribunal_titular_text = "\n".join(titulares)
        tribunal_suplentes_text = "\n".join(suplentes)
        
        # Add categorized lists to data dictionary
        data["tribunal_titular_docente"] = "\n".join(tribunal_titular_docente) if tribunal_titular_docente else ""
        data["tribunal_titular_estudiante"] = "\n".join(tribunal_titular_estudiante) if tribunal_titular_estudiante else ""
        data["tribunal_suplente_docente"] = "\n".join(tribunal_suplente_docente) if tribunal_suplente_docente else ""
        data["tribunal_suplente_estudiante"] = "\n".join(tribunal_suplente_estudiante) if tribunal_suplente_estudiante else ""
    
    # Ensure we have the categoria_nombre
    categoria_nombre = concurso.categoria_nombre or concurso.categoria
    
    # If categoria_nombre isn't set in the concurso, try to find it from roles_categorias.json
    if categoria_nombre == concurso.categoria:
        try:
            # Load roles_categorias.json data
            json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'roles_categorias.json')
            with open(json_path, 'r', encoding='utf-8') as f:
                roles_data = json.load(f)
            
            # Find categoria name by codigo
            for rol in roles_data:
                for categoria in rol['categorias']:
                    if categoria['codigo'] == concurso.categoria:
                        categoria_nombre = categoria['nombre']
                        break
                if categoria_nombre != concurso.categoria:
                    break
        except Exception as e:
            print(f"Error loading categoria_nombre from roles_categorias.json: {str(e)}")
            # If there's an error, just use the categoria code as the name
            categoria_nombre = concurso.categoria
    
    # Generate description for the cargo - make sure to include all required parameters
    descripcion_cargo = format_descripcion_cargo(
        concurso.cant_cargos,
        concurso.tipo,
        concurso.categoria,
        categoria_nombre,
        concurso.dedicacion
    )
    
    # Format cargo text with all parameters
    cargo_texto = format_cargos_text(
        concurso.cant_cargos, 
        concurso.tipo, 
        concurso.categoria,
        categoria_nombre,
        concurso.dedicacion
    )
    
    # Prepare common data for template replacements
    data.update({
        'cantCargos': cargo_texto,
        'departamento': departamento.nombre if departamento else '',
        'area': concurso.area,
        'orientacion': concurso.orientacion,
        'tipo': concurso.tipo,
        'nombre': categoria_nombre,  # Use found name or fallback to codigo
        'codigo': concurso.categoria,
        'tribunal_titular': tribunal_titular_text,
        'tribunal_suplentes': tribunal_suplentes_text,
        'yyyy': str(current_year),
        'expediente': concurso.expediente,
        'descripcion_cargo': descripcion_cargo
    })
    
    # Document type specific data could be added here if needed
    if document_type == 'ACTA_CONSTITUCION_TRIBUNAL_REGULAR':
        # Special handling for acta constitucion
        pass
    
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
            return False, validation_message, None

        # Add committee and council information to data for template
        # Format committee date
        if concurso.fecha_comision_academica:
            fecha_comision = concurso.fecha_comision_academica.strftime('%d/%m/%Y')
            data['fecha_comision_academica'] = fecha_comision
        else:
            data['fecha_comision_academica'] = ""
            
        # Format council date
        if concurso.fecha_consejo_directivo:
            fecha_consejo = concurso.fecha_consejo_directivo.strftime('%d/%m/%Y')
            data['fecha_consejo_directivo'] = fecha_consejo
        else:
            data['fecha_consejo_directivo'] = ""
            
        # Add text fields
        data['despacho_comision_academica'] = concurso.despacho_comision_academica or ""
        data['sesion_consejo_directivo'] = concurso.sesion_consejo_directivo or ""
        data['despacho_consejo_directivo'] = concurso.despacho_consejo_directivo or ""

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
            })

        # Add formatted postulantes list 
        postulantes = concurso.postulantes.all()
        if postulantes:
            postulantes_formateados = []
            for p in postulantes:
                postulantes_formateados.append(f"{p.apellido}, {p.nombre} (DNI: {p.dni})")            
                data['postulantes_lista'] = '\n'.join(postulantes_formateados)
        else:
            data['postulantes_lista'] = '-'        # Get tribunal members for placeholders - this section is causing duplication
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
            
        tribunal_presidente = ""
        tribunal_titulares = []
        
        # Initialize tribunal-related variables
        if "tribunal_titular" in data:
            # Save the existing values
            existing_tribunal_titular = data["tribunal_titular"]
        else:
            # If not already set, initialize them
            existing_tribunal_titular = ""
            
        if "tribunal_suplentes" in data:
            # Save the existing values
            existing_tribunal_suplentes = data["tribunal_suplentes"]
        else:
            # If not already set, initialize them
            existing_tribunal_suplentes = ""
            
        # Only process the tribunal members if the document type requires it and existing values are empty
        if doc_config['requires_tribunal'] and not existing_tribunal_titular and not existing_tribunal_suplentes:
            tribunal_members = concurso.asignaciones_tribunal.all()
            for miembro in tribunal_members:
                member_info = f"{miembro.persona.apellido}, {miembro.persona.nombre} (DNI: {miembro.persona.dni})"
                
                if miembro.rol == "Presidente":
                    tribunal_presidente = member_info
                    # Presidente goes first in titulares list
                    data["tribunal_titular"] = member_info                
                elif miembro.rol == "Suplente":
                    if "tribunal_suplentes" not in data:
                        data["tribunal_suplentes"] = member_info
                    else:
                        data["tribunal_suplentes"] += "\n" + member_info
                else:  # Titular
                    tribunal_titulares.append(member_info)
                    if "tribunal_titular" not in data:
                        data["tribunal_titular"] = member_info
                    else:
                        data["tribunal_titular"] += "\n" + member_info
                          # Ensure tribunal_presidente is set
            if tribunal_presidente:
                data['tribunal_presidente'] = tribunal_presidente
                  # Ensure tribunal_titulares is set
            if tribunal_titulares:
                data['tribunal_titulares'] = '\n'.join(tribunal_titulares)
        else:
            # Use the existing values
            data["tribunal_titular"] = existing_tribunal_titular
            data["tribunal_suplentes"] = existing_tribunal_suplentes

        # Process considerandos text if provided - replace placeholders with actual values
        if considerandos_text:
            # Get the departamento object from the relationship
            departamento = Departamento.query.get(concurso.departamento_id) if concurso.departamento_id else None
            departamento_nombre = departamento.nombre if departamento else ""
            
            # Define placeholders and their corresponding values from the concurso
            placeholders = {
                '<<Docente_que_genera_vacante>>': concurso.docente_vacante or '',
                '<<licencia>>': concurso.origen_vacante or '',
                '<<Origen_vacante>>': concurso.origen_vacante or '',
                '<<Expediente>>': concurso.expediente or '',
                '<<Departamento>>': departamento_nombre,
                '<<Area>>': concurso.area or '',
                '<<Orientacion>>': concurso.orientacion or '',
                '<<Categoria>>': concurso.categoria_nombre or concurso.categoria or '',
                '<<Dedicacion>>': concurso.dedicacion or '',
                '<<CantCargos>>': str(concurso.cant_cargos) if concurso.cant_cargos else '1',
                '<<fecha_comision_academica>>': data['fecha_comision_academica'],
                '<<despacho_comision_academica>>': data['despacho_comision_academica'],
                '<<sesion_consejo_directivo>>': data['sesion_consejo_directivo'],
                '<<fecha_consejo_directivo>>': data['fecha_consejo_directivo'],
                '<<despacho_consejo_directivo>>': data['despacho_consejo_directivo'],                '<<descripcion_cargo>>': data.get('descripcion_cargo', ''),
                '<<res_llamado_interino>>': concurso.nro_res_llamado_interino or '',
                '<<res_llamado_regular>>': concurso.nro_res_llamado_regular or '',
                '<<res_tribunal_regular>>': concurso.nro_res_tribunal_regular or '',
                '<<tribunal_titular>>': data.get('tribunal_titular', ''),
                '<<tribunal_suplentes>>': data.get('tribunal_suplentes', ''),
                '<<tribunal_presidente>>': data.get('tribunal_presidente', ''),
                '<<tribunal_vocales>>': data.get('tribunal_titulares', data.get('tribunal_vocales', '')),
                '<<tribunal_titular_docente>>': data.get('tribunal_titular_docente', ''),
                '<<tribunal_titular_estudiante>>': data.get('tribunal_titular_estudiante', ''),
                '<<tribunal_suplente_docente>>': data.get('tribunal_suplente_docente', ''),
                '<<tribunal_suplente_estudiante>>': data.get('tribunal_suplente_estudiante', '')
            }
            
            # Add departamento head information from the API
            departamento_heads = get_departamento_heads_data()
            if departamento_heads:
                # Find matching department head
                dept_head = None
                for head in departamento_heads:
                    if head.get('departamento') == departamento_nombre:
                        dept_head = head
                        break
                
                # Add department head placeholders if found
                if dept_head:
                    placeholders['<<resp_departamento>>'] = dept_head.get('responsable', '')
                    placeholders['<<prefijo_resp_departamento>>'] = dept_head.get('prefijo', '')
            
            # Replace placeholders in considerandos text
            processed_text = considerandos_text
            for placeholder, value in placeholders.items():
                processed_text = processed_text.replace(placeholder, value)
            
            # Add processed considerandos to data
            data['considerandos'] = processed_text
              # Add the placeholders directly to template data for direct replacement
        # This ensures all ways of replacing placeholders are covered
        departamento = Departamento.query.get(concurso.departamento_id) if concurso.departamento_id else None
        departamento_nombre = departamento.nombre if departamento else ""
        data.update({
            'Docente_que_genera_vacante': concurso.docente_vacante or '',
            'licencia': concurso.origen_vacante or '',
            'Origen_vacante': concurso.origen_vacante or '',
            'Expediente': concurso.expediente or '',
            'Departamento': departamento_nombre,
            'Area': concurso.area or '',
            'Orientacion': concurso.orientacion or '',
            'Categoria': concurso.categoria_nombre or concurso.categoria or '',
            'Dedicacion': concurso.dedicacion or '',
            'CantCargos': str(concurso.cant_cargos) if concurso.cant_cargos else '1',            'descripcion_cargo': data.get('descripcion_cargo', ''),
            'res_llamado_interino': concurso.nro_res_llamado_interino or '',
            'res_llamado_regular': concurso.nro_res_llamado_regular or '',
            'res_tribunal_regular': concurso.nro_res_tribunal_regular or '',
            'TKD': concurso.tkd or '',
            # Add claustro-based categories
            'tribunal_titular_docente': data.get('tribunal_titular_docente', ''),
            'tribunal_titular_estudiante': data.get('tribunal_titular_estudiante', ''),
            'tribunal_suplente_docente': data.get('tribunal_suplente_docente', ''),
            'tribunal_suplente_estudiante': data.get('tribunal_suplente_estudiante', '')
        })        # Generate file name with timestamp
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