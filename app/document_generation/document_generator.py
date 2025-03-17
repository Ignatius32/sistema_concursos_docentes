"""
Base document generation functionality for concursos docentes application.
Contains core functions for generating documents from templates.
"""
from datetime import datetime
from flask_login import current_user
from app.models.models import db, HistorialEstado, DocumentoConcurso, Concurso, Departamento, TribunalMiembro
from app.integrations.google_drive import GoogleDriveAPI
from app.helpers.api_services import get_departamento_heads_data

drive_api = GoogleDriveAPI()

def generar_documento_desde_template(concurso_id, template_name, doc_tipo, prepare_data_func, considerandos_text=None):
    """
    Generic function to generate a document from a template.
    
    Args:
        concurso_id (int): ID of the concurso
        template_name (str): Name of the template in Google Drive
        doc_tipo (str): Type of document for database record
        prepare_data_func (function): Function that prepares the data for the template
        considerandos_text (str, optional): Compiled considerandos text to add to the document
        
    Returns:
        tuple: (success, message, url) - Indicates success/failure, message, and URL if successful
    """
    try:
        concurso = Concurso.query.get_or_404(concurso_id)
        
        if not concurso.borradores_folder_id:
            return False, 'El concurso no tiene una carpeta de borradores asociada.', None
        
        # Get data for template from the specific function - pass document type
        data, validation_message = prepare_data_func(concurso, doc_tipo)
        
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
                '<<despacho_consejo_directivo>>': data['despacho_consejo_directivo'],
                '<<descripcion_cargo>>': data.get('descripcion_cargo', '')
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
            
            # Add sustanciacion placeholders
            if concurso.sustanciacion:
                sustanciacion = concurso.sustanciacion
                # Format dates
                constitucion_fecha = sustanciacion.constitucion_fecha.strftime('%d/%m/%Y %H:%M') if sustanciacion.constitucion_fecha else ''
                sorteo_fecha = sustanciacion.sorteo_fecha.strftime('%d/%m/%Y %H:%M') if sustanciacion.sorteo_fecha else ''
                exposicion_fecha = sustanciacion.exposicion_fecha.strftime('%d/%m/%Y %H:%M') if sustanciacion.exposicion_fecha else ''
                
                placeholders.update({
                    # Constitución
                    '<<constitucion_fecha>>': constitucion_fecha,
                    '<<constitucion_lugar>>': sustanciacion.constitucion_lugar or '',
                    '<<constitucion_virtual_link>>': sustanciacion.constitucion_virtual_link or '',
                    
                    # Sorteo
                    '<<sorteo_fecha>>': sorteo_fecha,
                    '<<sorteo_lugar>>': sustanciacion.sorteo_lugar or '',
                    '<<sorteo_virtual_link>>': sustanciacion.sorteo_virtual_link or '',
                    '<<temas_exposicion>>': (sustanciacion.temas_exposicion or '').replace('|', '\n'),
                    
                    # Exposición
                    '<<exposicion_fecha>>': exposicion_fecha,
                    '<<exposicion_lugar>>': sustanciacion.exposicion_lugar or '',
                    '<<exposicion_virtual_link>>': sustanciacion.exposicion_virtual_link or '',
                })
            
            # Add tribunal placeholders
            tribunal_members = TribunalMiembro.query.filter_by(concurso_id=concurso.id).all()
            presidente = next((m for m in tribunal_members if m.rol == 'Presidente'), None)
            vocales = [m for m in tribunal_members if m.rol == 'Vocal']
            suplentes = [m for m in tribunal_members if m.rol == 'Suplente']

            def format_member(m):
                return f"{m.apellido}, {m.nombre} (DNI: {m.dni})"

            placeholders.update({
                '<<tribunal_presidente>>': format_member(presidente) if presidente else '',
                '<<tribunal_vocales>>': '\n'.join(format_member(v) for v in vocales),
                '<<tribunal_suplentes>>': '\n'.join(format_member(s) for s in suplentes),
                '<<tribunal_miembros>>': '\n'.join(format_member(m) for m in tribunal_members)
            })

            # Replace placeholders in considerandos text
            processed_text = considerandos_text
            for placeholder, value in placeholders.items():
                processed_text = processed_text.replace(placeholder, value)
            
            # Add processed considerandos to data
            data['considerandos'] = processed_text
            
        # Generate file name with timestamp
        file_name = f"{doc_tipo.replace('_', ' ').title()}_Concurso_{concurso.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
        
        # Use API to create document from template in borradores folder
        file_id, web_link = drive_api.create_document_from_template(
            template_name,
            data,
            concurso.borradores_folder_id,
            file_name
        )
        
        # Create document record
        documento = DocumentoConcurso(
            concurso=concurso,
            tipo=doc_tipo,
            url=web_link,
            estado='BORRADOR'
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
        db.session.rollback()
        return False, f'Error al generar el documento: {str(e)}', None