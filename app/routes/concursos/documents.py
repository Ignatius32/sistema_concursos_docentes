from flask import redirect, url_for, flash, request, render_template, current_app
from app.utils.keycloak_auth import keycloak_login_required, admin_required, get_current_username
from datetime import datetime
from app.models.models import db, Concurso, Departamento, DocumentoConcurso, HistorialEstado, DocumentTemplateConfig
from app.services.placeholder_resolver import get_core_placeholders
from app.helpers.api_services import get_considerandos_data, get_departamento_heads_data
from app.document_generation.document_generator import generar_documento_desde_template
import json
from . import concursos, drive_api

def update_concurso_resolution_number(concurso, template_config, documento):
    """
    Update the corresponding resolution number field in the concurso based on document parentesco.
    
    Args:
        concurso: The Concurso instance
        template_config: The DocumentTemplateConfig instance  
        documento: The DocumentoConcurso instance with resolution info
    """
    if not template_config.es_res or not template_config.parentesco:
        return
    
    if not documento.tipo_res or not documento.nro_res:
        return
    
    # Construct the full resolution string
    res_string = f"{documento.tipo_res} {documento.nro_res}"
    
    # Update the appropriate field based on parentesco
    if template_config.parentesco == "LLAMADO":
        concurso.nro_res_llamado = res_string
    elif template_config.parentesco == "TRIBUNAL":
        concurso.nro_res_tribunal = res_string
    else:
        concurso.nro_res_otras = res_string

def generate_resolution_filename(documento, concurso, template_config, is_firmado=True):
    """
    Generate a filename for resolution documents based on their metadata.
    
    Args:
        documento: The DocumentoConcurso instance with resolution info
        concurso: The Concurso instance
        template_config: The DocumentTemplateConfig instance
        is_firmado: Whether this is for the signed version (default: True)
    
    Returns:
        str: The generated filename
    """
    if not template_config.es_res or not documento.tipo_res or not documento.nro_res:
        # Fallback to original naming for non-resolutions or incomplete data
        original_filename = documento.tipo.lower().replace('_', ' ') + f"_concurso_{concurso.id}"
        return f"{original_filename}_firmado.pdf" if is_firmado else f"{original_filename}.pdf"
    
    # Sanitize resolution type for filename (remove spaces, special chars)
    tipo_sanitized = documento.tipo_res.replace(' ', '_').replace('.', '').replace('/', '-')
    
    # Sanitize resolution number for filename (replace / with -)
    nro_sanitized = documento.nro_res.replace('/', '-').replace('\\', '-')
    
    # Get concurso basic info for context
    concurso_info = f"Concurso_{concurso.id}_{concurso.categoria}_{concurso.dedicacion}"
    
    # Add departamento if available for better organization
    if concurso.departamento_rel:
        dept_name = concurso.departamento_rel.nombre.replace(' ', '_')[:20]  # Limit length
        concurso_info = f"{concurso_info}_{dept_name}"
    
    # Construct the filename
    base_filename = f"{tipo_sanitized}_{nro_sanitized}_{concurso_info}"
    
    # Add suffix based on document state
    if is_firmado:
        return f"{base_filename}_firmado.pdf"
    else:
        return f"{base_filename}.pdf"

def maybe_rename_document_in_drive(documento, concurso, template_config, file_id):
    """
    Optionally rename a document in Google Drive if it's a resolution with metadata.
    This is called after uploading to potentially rename the file to a more descriptive name.
    
    Args:
        documento: The DocumentoConcurso instance
        concurso: The Concurso instance
        template_config: The DocumentTemplateConfig instance
        file_id: The Google Drive file ID
    
    Returns:
        bool: True if renaming was attempted, False if not applicable
    """
    if not template_config.es_res or not documento.tipo_res or not documento.nro_res:
        return False
    
    try:
        # Generate the new resolution-based filename
        new_filename = generate_resolution_filename(documento, concurso, template_config, is_firmado=True)
        
        # Attempt to rename the file in Google Drive
        # Note: This would require extending the GoogleDriveAPI to support renaming
        # For now, we just return True to indicate we would rename if the API supported it
        current_app.logger.info(f"Would rename document {file_id} to: {new_filename}")
        return True
        
    except Exception as e:
        current_app.logger.warning(f"Failed to rename document {file_id}: {str(e)}")
        return False

@concursos.route('/<int:concurso_id>/generar-resolucion-llamado-tribunal', methods=['GET'])
@keycloak_login_required
@admin_required
def generar_resolucion_llamado_tribunal(concurso_id):
    """Handle the request to generate a resolution document with tribunal information."""
    concurso = Concurso.query.get_or_404(concurso_id)
    # Redirect to the considerandos builder
    return redirect(url_for('concursos.considerandos_builder', 
                           concurso_id=concurso_id, 
                           document_type='RESOLUCION_LLAMADO_TRIBUNAL', 
                           template_name='resLlamadoTribunalInterino'))

@concursos.route('/<int:concurso_id>/generar-resolucion-llamado-regular', methods=['GET'])
@keycloak_login_required
@admin_required
def generar_resolucion_llamado_regular(concurso_id):
    """Handle the request to generate a regular resolution document."""
    concurso = Concurso.query.get_or_404(concurso_id)
    # Redirect to the considerandos builder
    return redirect(url_for('concursos.considerandos_builder', 
                           concurso_id=concurso_id, 
                           document_type='RESOLUCION_LLAMADO_REGULAR', 
                           template_name='resLlamadoRegular'))

@concursos.route('/<int:concurso_id>/generar-resolucion-tribunal-regular', methods=['GET'])
@keycloak_login_required
@admin_required
def generar_resolucion_tribunal_regular(concurso_id):
    """Handle the request to generate a regular tribunal resolution document."""
    concurso = Concurso.query.get_or_404(concurso_id)
    # Redirect to the considerandos builder
    return redirect(url_for('concursos.considerandos_builder', 
                           concurso_id=concurso_id, 
                           document_type='RESOLUCION_TRIBUNAL_REGULAR', 
                           template_name='resTribunalRegular'))

@concursos.route('/<int:concurso_id>/generar-acta-constitucion-tribunal-regular', methods=['GET'])
@keycloak_login_required
@admin_required
def generar_acta_constitucion_tribunal_regular(concurso_id):
    """Handle the request to generate a regular tribunal constitution document."""
    concurso = Concurso.query.get_or_404(concurso_id)

    # Check document visibility and uniqueness from API
    doc_data = get_considerandos_data('ACTA_CONSTITUCION_TRIBUNAL_REGULAR', concurso.tipo)
    if not doc_data:
        flash('Este documento no está disponible para este tipo de concurso.', 'warning')
        return redirect(url_for('concursos.ver', concurso_id=concurso_id))

    # Check if unique document already exists
    if doc_data.get('unique', 0) == 1:
        existing_document = DocumentoConcurso.query.filter_by(
            concurso_id=concurso_id,
            tipo='ACTA_CONSTITUCION_TRIBUNAL_REGULAR'
        ).first()
        if existing_document:
            # Implementation for existing document
            pass

    # Generate the document directly using the consolidated function
    success, message, url = generar_documento_desde_template(
        concurso_id,
        'actaConstitucionTribunalRegular',
        'ACTA_CONSTITUCION_TRIBUNAL_REGULAR'
    )

    if success:
        flash(f'{message} <a href="{url}" target="_blank" class="alert-link">Abrir documento</a>', 'success')
    else:
        flash(message, 'danger')

    return redirect(url_for('concursos.ver', concurso_id=concurso_id))

@concursos.route('/<int:concurso_id>/considerandos-builder', methods=['GET', 'POST'])
@keycloak_login_required
@admin_required
def considerandos_builder(concurso_id):
    """
    Handle the considerandos builder interface.
    """
    import time
    from app.models.models import DocumentTemplateConfig
    
    start_time = time.time()
    current_app.logger.debug(f"[CONSIDERANDOS] Starting considerandos_builder for concurso_id: {concurso_id}")
    
    step_start = time.time()
    concurso = Concurso.query.get_or_404(concurso_id)
    current_app.logger.debug(f"[CONSIDERANDOS] Concurso query took: {time.time() - step_start:.3f}s")
    
    # Get the departamento object
    step_start = time.time()
    departamento = Departamento.query.get(concurso.departamento_id) if concurso.departamento_id else None
    current_app.logger.debug(f"[CONSIDERANDOS] Departamento query took: {time.time() - step_start:.3f}s")
    
    # Get document type key and template Google ID from query parameters
    document_type_key = request.args.get('document_type_key')
    template_google_id = request.args.get('template_google_id')
    
    # For backward compatibility
    if not document_type_key and request.args.get('document_type'):
        document_type_key = request.args.get('document_type')
    if not template_google_id and request.args.get('template_name'):
        template_google_id = request.args.get('template_name')
      # Get all placeholders from the centralized resolver
    step_start = time.time()
    placeholders = get_core_placeholders(concurso_id)
    current_app.logger.debug(f"[CONSIDERANDOS] get_core_placeholders took: {time.time() - step_start:.3f}s")
    
    # Get the cargo description from the placeholders
    descripcion_cargo = placeholders['descripcion_cargo']
    
    if not document_type_key or not template_google_id:
        flash('Tipo de documento o plantilla no especificados', 'danger')
        return redirect(url_for('concursos.ver', concurso_id=concurso_id))    # Fetch considerandos options from the API (still needed for the actual text options)
    step_start = time.time()
    considerandos_data = get_considerandos_data(document_type_key, concurso.tipo)
    elapsed_considerandos = time.time() - step_start
    current_app.logger.debug(f"[CONSIDERANDOS] get_considerandos_data took: {elapsed_considerandos:.3f}s")
    
    # Fetch departamento heads data (with fallback if it times out)
    step_start = time.time()
    departamento_heads = get_departamento_heads_data()
    elapsed_dept_heads = time.time() - step_start
    current_app.logger.debug(f"[CONSIDERANDOS] get_departamento_heads_data took: {elapsed_dept_heads:.3f}s")
    
    # If department heads data fails, continue without it (graceful degradation)
    if departamento_heads is None:
        current_app.logger.warning(f"[CONSIDERANDOS] Department heads API failed, continuing without this data")
        departamento_heads = []
        
    if considerandos_data is None:
        current_app.logger.error(f"[CONSIDERANDOS] Considerandos API failed - this is critical")
        error_message = 'No se pudieron cargar los considerandos. Por favor, inténtelo de nuevo más tarde.'
        return render_template(
            'concursos/considerandos_builder.html', 
            concurso=concurso,
            departamento=departamento,
            document_type=document_type_key,
            considerandos_data={},
            departamento_heads=departamento_heads,
            descripcion_cargo=descripcion_cargo,
            error_message=error_message
        )
    
    # Extract just the considerandos part to use in the template
    considerandos_options = considerandos_data.get('considerandos', {})
    
    if request.method == 'POST':
        # Save committee and council information
        try:
            # Process committee date
            fecha_comision_str = request.form.get('fecha_comision_academica')
            if fecha_comision_str:
                concurso.fecha_comision_academica = datetime.strptime(fecha_comision_str, '%Y-%m-%d').date()
            else:
                concurso.fecha_comision_academica = None
                
            # Process council date
            fecha_consejo_str = request.form.get('fecha_consejo_directivo')
            if fecha_consejo_str:
                concurso.fecha_consejo_directivo = datetime.strptime(fecha_consejo_str, '%Y-%m-%d').date()
            else:
                concurso.fecha_consejo_directivo = None
            
            # Process text fields
            concurso.despacho_comision_academica = request.form.get('despacho_comision_academica', '')
            concurso.sesion_consejo_directivo = request.form.get('sesion_consejo_directivo', '')
            concurso.despacho_consejo_directivo = request.form.get('despacho_consejo_directivo', '')
            
            # Save to database
            db.session.commit()
        except Exception as e:
            flash(f'Error al guardar información de comisión y consejo: {str(e)}', 'warning')
            db.session.rollback()
        
        # Collect selected considerandos in the specified order
        selected_considerandos = []
        
        # Process considerandos order from the hidden input
        considerandos_order_json = request.form.get('considerandos_order', '[]')
        try:
            considerandos_order = json.loads(considerandos_order_json)
            
            # Extract considerando values in the specified order
            for item in considerandos_order:
                value = item.get('value', '')
                if value and value.strip():
                    selected_considerandos.append(value.strip())
                
        except json.JSONDecodeError:
            # Fallback to the old way if the JSON is invalid
            # This ensures backward compatibility
            for considerando_key in considerandos_options.keys():
                selected_value = request.form.get(considerando_key)
                if selected_value:
                    selected_considerandos.append(selected_value)
            
            # Add custom considerandos if provided
            custom_considerandos = request.form.getlist('custom_considerandos[]')
            for custom_text in custom_considerandos:
                if custom_text and custom_text.strip():
                    selected_considerandos.append(custom_text.strip())
        
        # Compile considerandos text with single line breaks
        considerandos_text = "\n".join(selected_considerandos)
        
        # Proceed with document generation
        success, message, url = generar_documento_desde_template(
            concurso_id,
            template_google_id,  # Using the Google Doc ID as template name
            document_type_key,   # Using the document_type_key for doc_tipo
            None,                # Using the default prepare_data_for_document function now
            considerandos_text
        )
        
        if success:
            flash(f'{message} <a href="{url}" target="_blank" class="alert-link">Abrir documento</a>', 'success')
        else:
            flash(message, 'danger')
            
        return redirect(url_for('concursos.ver', concurso_id=concurso_id))
      # Display the considerandos form
    current_app.logger.debug(f"[CONSIDERANDOS] Total considerandos_builder took: {time.time() - start_time:.3f}s")
    return render_template(
        'concursos/considerandos_builder.html',
        concurso=concurso,
        departamento=departamento,
        document_type=document_type_key,
        considerandos_data=considerandos_options,
        departamento_heads=departamento_heads,
        descripcion_cargo=descripcion_cargo
    )

@concursos.route('/<int:concurso_id>/documento/<int:documento_id>/eliminar', methods=['POST'])
@keycloak_login_required
@admin_required
def eliminar_documento(concurso_id, documento_id):
    """Delete a document from a concurso."""
    concurso = Concurso.query.get_or_404(concurso_id)
    documento = DocumentoConcurso.query.get_or_404(documento_id)
    
    # Verify the document belongs to the concurso
    if documento.concurso_id != concurso_id:
        flash('El documento no pertenece a este concurso.', 'danger')
        return redirect(url_for('concursos.ver', concurso_id=concurso_id))
    
    try:
        # Get file ID from URL
        file_id = documento.url.split('/')[-2]  # Google Drive URLs have the file ID in the second-to-last segment
        
        # Try to delete from Drive
        try:
            drive_api.delete_file(file_id)
        except Exception as e:
            flash(f'Advertencia: No se pudo eliminar el archivo de Google Drive: {str(e)}', 'warning')
        
        # Delete from database
        db.session.delete(documento)
        
        # Add entry to history
        historial = HistorialEstado(
            concurso=concurso,
            estado="DOCUMENTO_ELIMINADO",
            observaciones=f"Documento {documento.tipo} eliminado por {get_current_username()}"
        )
        db.session.add(historial)
        
        db.session.commit()
        flash('Documento eliminado exitosamente.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el documento: {str(e)}', 'danger')
    
    return redirect(url_for('concursos.ver', concurso_id=concurso_id))

@concursos.route('/<int:concurso_id>/documento/<int:documento_id>/subir-firmado', methods=['POST'])
@keycloak_login_required
@admin_required
def subir_documento_firmado(concurso_id, documento_id):
    """Upload a signed version of a document."""
    concurso = Concurso.query.get_or_404(concurso_id)
    documento = DocumentoConcurso.query.get_or_404(documento_id)
    
    # Verify the document belongs to the concurso
    if documento.concurso_id != concurso_id:
        flash('El documento no pertenece a este concurso.', 'danger')
        return redirect(url_for('concursos.ver', concurso_id=concurso_id))
    
    if not concurso.documentos_firmados_folder_id:
        flash('El concurso no tiene una carpeta de documentos firmados asociada.', 'danger')
        return redirect(url_for('concursos.ver', concurso_id=concurso_id))
    
    try:
        file = request.files.get('documento_firmado')
        
        if not file:
            flash('No se seleccionó ningún archivo.', 'danger')
            return redirect(url_for('concursos.ver', concurso_id=concurso_id))
        
        # Get template configuration for this document type
        template_config = DocumentTemplateConfig.query.filter_by(document_type_key=documento.tipo).first()
        
        # If it's a resolution, handle resolution-specific fields first
        if template_config and template_config.es_res:
            documento.nro_res = request.form.get('numero_resolucion')
            documento.tipo_res = request.form.get('tipo_resolucion')
            fecha_res_str = request.form.get('fecha_resolucion')
            if fecha_res_str:
                try:
                    documento.fecha_res = datetime.strptime(fecha_res_str, '%Y-%m-%d').date()
                except ValueError:
                    flash('Formato de fecha inválido.', 'danger')
                    return redirect(url_for('concursos.ver', concurso_id=concurso_id))
            documento.articulado = request.form.get('articulado')
        
        # Generate appropriate filename based on document type and metadata
        if template_config and template_config.es_res and documento.nro_res and documento.tipo_res:
            new_filename = generate_resolution_filename(documento, concurso, template_config, is_firmado=True)
        else:
            # Fallback to original naming for non-resolutions
            original_filename = documento.tipo.lower().replace('_', ' ') + f"_concurso_{concurso.id}"
            new_filename = f"{original_filename}_firmado.pdf"
        
        # Upload to documentos_firmados folder
        file_data = file.read()
        file_id, web_view_link = drive_api.upload_document(
            concurso.documentos_firmados_folder_id,
            new_filename,
            file_data
        )
        
        # Update concurso resolution number based on parentesco (if resolution)
        if template_config and template_config.es_res:
            update_concurso_resolution_number(concurso, template_config, documento)
        
        # Update document record for the signed version
        documento.file_id = file_id  # Store the file ID of the signed version
        documento.update_url_from_file_ids()  # Update URL based on state and file IDs
        documento.estado = 'FIRMADO'
        
        # Update concurso estado_actual and subestado if configured in template
        if template_config and template_config.estado_al_subir_firmado:
            concurso.estado_actual = template_config.estado_al_subir_firmado
              # Handle subestado - replace values that were set at borrador creation time
        if template_config and template_config.subestado_al_subir_firmado:
            if concurso.subestado:
                try:
                    # Try to parse existing subestado as JSON
                    subestado_values = json.loads(concurso.subestado)
                    if not isinstance(subestado_values, list):
                        subestado_values = [subestado_values]
                          # If borrador subestado exists, remove it
                    if template_config.subestado_al_generar_borrador and template_config.subestado_al_generar_borrador in subestado_values:
                        subestado_values.remove(template_config.subestado_al_generar_borrador)
                    
                    # Add the firmado subestado with a special prefix to identify it as a firmado subestado
                    firmado_subestado = f"firmado:{template_config.subestado_al_subir_firmado}"
                    if firmado_subestado not in subestado_values:
                        subestado_values.append(firmado_subestado)
                        
                    concurso.subestado = json.dumps(subestado_values)
                except (json.JSONDecodeError, TypeError):                    # If it's not valid JSON, start fresh with just the firmado value
                    firmado_subestado = f"firmado:{template_config.subestado_al_subir_firmado}"
                    concurso.subestado = json.dumps([firmado_subestado])
            else:
                # If subestado is empty, initialize with a single value
                firmado_subestado = f"firmado:{template_config.subestado_al_subir_firmado}"
                concurso.subestado = json.dumps([firmado_subestado])
        
        # Add entry to history
        historial = HistorialEstado(
            concurso=concurso,
            estado="DOCUMENTO_FIRMADO",
            observaciones=f"Documento firmado {documento.tipo} subido por {get_current_username()}"
        )
        db.session.add(historial)
        
        db.session.commit()
        flash(f'Documento firmado subido exitosamente. <a href="{web_view_link}" target="_blank" class="alert-link">Ver documento</a>', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al subir el documento firmado: {str(e)}', 'danger')
    
    return redirect(url_for('concursos.ver', concurso_id=concurso_id))

@concursos.route('/<int:concurso_id>/documentos/<int:documento_id>/enviar-firma', methods=['POST'])
@keycloak_login_required
@admin_required
def enviar_firma(concurso_id, documento_id):
    """Send a document for signature via email."""
    try:
        concurso = Concurso.query.get_or_404(concurso_id)
        documento = DocumentoConcurso.query.get_or_404(documento_id)
        
        # Validate document state and type
        if (documento.estado not in ['BORRADOR', 'ENVIADO PARA FIRMAR']) or 'RESOLUCION' not in documento.tipo:
            flash('Solo se pueden enviar para firma resoluciones en estado borrador o enviado para firma.', 'error')
            return redirect(url_for('concursos.ver', concurso_id=concurso_id))
            
        # Get form data
        destinatario = request.form.get('destinatario')
        observaciones = request.form.get('observaciones', '')
        if not destinatario:
            flash('El correo del destinatario es requerido.', 'error')
            return redirect(url_for('concursos.ver', concurso_id=concurso_id))
        
        # Get placeholders from the centralized resolver
        placeholders = get_core_placeholders(concurso_id)
            
        # Prepare email content
        doc_name = documento.tipo.replace('_', ' ').title()
        subject = f'Solicitud de firma: {doc_name} - Exp. {placeholders["expediente"] or "S/N"}'
        html_body = f"""
        <p>Se solicita la firma del siguiente documento:</p>
        <p><strong>{doc_name}</strong></p>
        <p><strong>Detalles del concurso:</strong></p>
        <ul>
            <li>Departamento: {placeholders["departamento_nombre"]}</li>
            <li>Área: {placeholders["area"]}</li>
            <li>Orientación: {placeholders["orientacion"]}</li>
            <li>Categoría: {placeholders["categoria_nombre"]} ({placeholders["categoria_codigo"]})</li>
            <li>Dedicación: {placeholders["dedicacion"]}</li>
        </ul>
        """
        
        if observaciones:
            html_body += f"<p><strong>Observaciones:</strong></p><p>{observaciones}</p>"
        
        # Ensure file_id is valid
        if not documento.file_id and documento.borrador_file_id:
            # Use borrador_file_id if file_id is not available
            attachment_id = documento.borrador_file_id
        elif documento.file_id:
            attachment_id = documento.file_id
        else:
            flash('El documento no tiene un archivo asociado para enviar.', 'error')
            return redirect(url_for('concursos.ver', concurso_id=concurso_id))
            
        # Send email with document as attachment
        drive_api.send_email(
            to_email=destinatario,
            subject=subject,
            html_body=html_body,
            sender_name='Sistema de Concursos Docentes',
            attachment_ids=[attachment_id],  # Make sure this is a list with a valid ID
            placeholders=placeholders  # Use all centralized placeholders
        )
        
        # Update document state
        documento.estado = 'ENVIADO PARA FIRMAR'
        db.session.commit()
        
        # Add entry to history
        historial = HistorialEstado(
            concurso=concurso,
            estado="DOCUMENTO_ENVIADO_FIRMA",
            observaciones=f"Documento {doc_name} enviado para firma a {destinatario}"
        )
        db.session.add(historial)
        db.session.commit()
        
        flash(f'El documento ha sido enviado a {destinatario} para su firma.', 'success')
        
    except Exception as e:
        flash(f'Error al enviar el documento: {str(e)}', 'error')
        
    return redirect(url_for('concursos.ver', concurso_id=concurso_id))

@concursos.route('/<int:concurso_id>/documento/<int:documento_id>/nueva-version', methods=['POST'])
@keycloak_login_required
@admin_required
def nueva_version_documento(concurso_id, documento_id):
    """Create a new version of a document."""
    try:
        concurso = Concurso.query.get_or_404(concurso_id)
        documento = DocumentoConcurso.query.get_or_404(documento_id)
        
        # Verify the document belongs to the concurso
        if documento.concurso_id != concurso_id:
            flash('El documento no pertenece a este concurso.', 'danger')
            return redirect(url_for('concursos.ver', concurso_id=concurso_id))
        
        # Get form data
        observaciones = request.form.get('observaciones', '')
        file = request.files.get('documento')
        
        if not file:
            flash('No se seleccionó ningún archivo.', 'danger')
            return redirect(url_for('concursos.ver', concurso_id=concurso_id))
        
        # Generate a timestamp-based version suffix instead of a numeric version
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        
        # Create a new filename with timestamp
        file_name = f"{documento.tipo.lower().replace('_', ' ')}_{concurso.id}_v{timestamp}.pdf"
        
        # Upload the new file to Google Drive
        file_data = file.read()
        file_id, web_view_link = drive_api.upload_document(
            concurso.borradores_folder_id,
            file_name,
            file_data
        )
          # Update the current document URL and file ID
        documento.borrador_file_id = file_id
        documento.update_url_from_file_ids()  # Update URL based on state and file IDs
        
        # Add entry to history with observaciones
        historial = HistorialEstado(
            concurso=concurso,
            estado="NUEVA_VERSION_DOCUMENTO",
            observaciones=f"Nueva versión del documento {documento.tipo} creada por {get_current_username()}: {observaciones}"
        )
        db.session.add(historial)
        
        db.session.commit()
        flash(f'Nueva versión del documento creada exitosamente.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al crear nueva versión: {str(e)}', 'danger')
    
    return redirect(url_for('concursos.ver', concurso_id=concurso_id))

@concursos.route('/<int:concurso_id>/documento/<int:documento_id>/eliminar-firmado', methods=['POST'])
@keycloak_login_required
@admin_required
def eliminar_documento_firmado(concurso_id, documento_id):
    """Delete a signed version of a document."""
    concurso = Concurso.query.get_or_404(concurso_id)
    documento = DocumentoConcurso.query.get_or_404(documento_id)
    
    # Verify the document belongs to the concurso
    if documento.concurso_id != concurso_id:
        flash('El documento no pertenece a este concurso.', 'danger')
        return redirect(url_for('concursos.ver', concurso_id=concurso_id))
    try:
        # Update document status back to BORRADOR
        documento.estado = 'BORRADOR'
        
        # Get template configuration for this document type
        template_config = DocumentTemplateConfig.query.filter_by(document_type_key=documento.tipo).first()
        
        # If document affected estado when uploaded as firmado, revert those changes
        if template_config and template_config.estado_al_subir_firmado and concurso.estado_actual == template_config.estado_al_subir_firmado:
            # Revert to previous estado
            previous_estado = "CREADO"  # Default fallback
            
            # Try to find a more appropriate previous state - either the borrador estado or an earlier state
            if template_config.estado_al_generar_borrador:
                previous_estado = template_config.estado_al_generar_borrador
            else:
                # Look for previous estado in history
                prev_history = HistorialEstado.query.filter(
                    HistorialEstado.concurso_id == concurso_id,
                    HistorialEstado.estado != "DOCUMENTO_FIRMADO",
                    HistorialEstado.estado != "DOCUMENTO_FIRMADO_ELIMINADO"
                ).order_by(HistorialEstado.fecha.desc()).first()
                
                if prev_history:
                    previous_estado = prev_history.estado
            
            concurso.estado_actual = previous_estado
        
        # Handle subestado if it was modified by this document type
        if template_config and template_config.subestado_al_subir_firmado and concurso.subestado:
            try:
                # Try to parse existing subestado as JSON
                subestado_values = json.loads(concurso.subestado)
                if not isinstance(subestado_values, list):
                    subestado_values = [subestado_values]
                
                # Remove the value added by this document type if it exists
                firmado_subestado = f"firmado:{template_config.subestado_al_subir_firmado}"
                if firmado_subestado in subestado_values:
                    subestado_values.remove(firmado_subestado)
                # For backward compatibility, also check without prefix
                elif template_config.subestado_al_subir_firmado in subestado_values:
                    subestado_values.remove(template_config.subestado_al_subir_firmado)
                    
                    # Update subestado or set to null if empty
                    if subestado_values:
                        concurso.subestado = json.dumps(subestado_values)
                    else:
                        concurso.subestado = None
            except (json.JSONDecodeError, TypeError):
                # If subestado is not valid JSON, leave it as is
                pass
        
        # Add entry to history
        historial = HistorialEstado(
            concurso=concurso,
            estado="DOCUMENTO_FIRMADO_ELIMINADO",
            observaciones=f"Documento firmado {documento.tipo} eliminado por {get_current_username()}"
        )
        db.session.add(historial)
        
        db.session.commit()
        flash('Documento firmado eliminado exitosamente. El documento volvió al estado borrador.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el documento firmado: {str(e)}', 'danger')
    
    return redirect(url_for('concursos.ver', concurso_id=concurso_id))

@concursos.route('/<int:concurso_id>/documento/<int:documento_id>/eliminar-pendiente-firma', methods=['POST'])
@keycloak_login_required
@admin_required
def eliminar_documento_pendiente_firma(concurso_id, documento_id):
    """Delete a document that is pending signature, resetting it back to BORRADOR state."""
    concurso = Concurso.query.get_or_404(concurso_id)
    documento = DocumentoConcurso.query.get_or_404(documento_id)
    
    # Verify the document belongs to the concurso
    if documento.concurso_id != concurso_id:
        flash('El documento no pertenece a este concurso.', 'danger')
        return redirect(url_for('concursos.ver', concurso_id=concurso_id))
    
    try:
        # Check if document is in PENDIENTE DE FIRMA state
        if documento.estado != 'PENDIENTE DE FIRMA':
            # Implementation for invalid state
            pass
        
        # Delete the file from Google Drive if file_id exists
        if documento.file_id:
            # Implementation for file deletion
            pass
        
        # Remove all signatures associated with this document
        for firma in documento.firmas:
            # Implementation for signature removal
            pass
        
        # Reset firma count
        documento.firma_count = 0
        
        # Update document status back to BORRADOR
        documento.estado = 'BORRADOR'
        
        # Add entry to history
        historial = HistorialEstado(
            concurso=concurso,
            estado="DOCUMENTO_PENDIENTE_FIRMA_ELIMINADO",
            observaciones=f"Documento pendiente de firma {documento.tipo} eliminado por {get_current_username()}"
        )
        db.session.add(historial)
        
        db.session.commit()
        flash('Documento pendiente de firma eliminado exitosamente. El documento volvió al estado borrador y puede ser subido nuevamente por el tribunal.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el documento pendiente de firma: {str(e)}', 'danger')
    
    return redirect(url_for('concursos.ver', concurso_id=concurso_id))

@concursos.route('/<int:concurso_id>/documento/<int:documento_id>/eliminar-borrador', methods=['POST'])
@keycloak_login_required
@admin_required
def eliminar_borrador(concurso_id, documento_id):
    """Delete a draft document from the borradores folder."""
    concurso = Concurso.query.get_or_404(concurso_id)
    documento = DocumentoConcurso.query.get_or_404(documento_id)
    
    # Verify the document belongs to the concurso
    if documento.concurso_id != concurso_id:
        flash('El documento no pertenece a este concurso.', 'danger')
        return redirect(url_for('concursos.ver', concurso_id=concurso_id))
    try:
        # Delete the file from Google Drive borradores folder
        if documento.borrador_file_id:
            try:
                drive_api.delete_file(documento.borrador_file_id)
            except Exception as e:
                flash(f'Advertencia: No se pudo eliminar el archivo borrador de Google Drive: {str(e)}', 'warning')
          # Add entry to history
        historial = HistorialEstado(
            concurso=concurso,
            estado="BORRADOR_ELIMINADO",
            observaciones=f"Borrador de {documento.tipo} eliminado por {get_current_username()}"
        )
        db.session.add(historial)
        
        # Get template configuration for this document type
        template_config = DocumentTemplateConfig.query.filter_by(document_type_key=documento.tipo).first()
        
        # If document is being deleted, and it affected estado or subestado when generated,
        # we may need to revert those changes
        if template_config and template_config.estado_al_generar_borrador and concurso.estado_actual == template_config.estado_al_generar_borrador:
            # Revert to previous estado if this was the only document of this type
            existing_docs = DocumentoConcurso.query.filter_by(
                concurso_id=concurso_id,
                tipo=documento.tipo
            ).filter(DocumentoConcurso.id != documento_id).all()
            
            if not existing_docs:
                # No other documents of this type, revert estado to previous
                previous_estado = "CREADO"  # Default fallback
                
                # Get the previous estado from history
                prev_history = HistorialEstado.query.filter(
                    HistorialEstado.concurso_id == concurso_id,
                    HistorialEstado.estado != "DOCUMENTO_GENERADO",
                    HistorialEstado.estado != "BORRADOR_ELIMINADO"
                ).order_by(HistorialEstado.fecha.desc()).first()
                
                if prev_history:
                    previous_estado = prev_history.estado
                
                concurso.estado_actual = previous_estado
        
        # Handle subestado if it was modified by this document type
        if template_config and template_config.subestado_al_generar_borrador and concurso.subestado:
            try:
                # Try to parse existing subestado as JSON
                subestado_values = json.loads(concurso.subestado)
                if not isinstance(subestado_values, list):
                    subestado_values = [subestado_values]
                
                # Remove the value added by this document type if it exists
                if template_config.subestado_al_generar_borrador in subestado_values:
                    subestado_values.remove(template_config.subestado_al_generar_borrador)
                    
                    # Update subestado or set to null if empty
                    if subestado_values:
                        concurso.subestado = json.dumps(subestado_values)
                    else:
                        concurso.subestado = None
            except (json.JSONDecodeError, TypeError):
                # If subestado is not valid JSON, leave it as is
                pass
        
        # If this is the only version (no signed document exists), delete the document record
        if documento.estado == 'BORRADOR':
            # Delete the document record completely
            db.session.delete(documento)
        else:
            # Just clear the borrador_file_id but keep the document record
            documento.borrador_file_id = None
        
        db.session.commit()
        flash('Borrador eliminado exitosamente.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el borrador: {str(e)}', 'danger')
    
    return redirect(url_for('concursos.ver', concurso_id=concurso_id))

@concursos.route('/<int:concurso_id>/documento/<int:documento_id>/eliminar-subido', methods=['POST'])
@keycloak_login_required
@admin_required
def eliminar_subido(concurso_id, documento_id):
    """Delete an uploaded/signed document from the firmados folder."""
    concurso = Concurso.query.get_or_404(concurso_id)
    documento = DocumentoConcurso.query.get_or_404(documento_id)
    
    # Verify the document belongs to the concurso
    if documento.concurso_id != concurso_id:
        flash('El documento no pertenece a este concurso.', 'danger')
        return redirect(url_for('concursos.ver', concurso_id=concurso_id))
    try:
        # Delete the file from Google Drive firmados folder
        if documento.file_id:
            try:
                drive_api.delete_file(documento.file_id)
            except Exception as e:
                flash(f'Advertencia: No se pudo eliminar el archivo firmado de Google Drive: {str(e)}', 'warning')
            # Clear the file_id after attempting deletion
            documento.file_id = None
        
        # Remove all signatures associated with this document
        if hasattr(documento, 'firmas'):
            for firma in documento.firmas:
                db.session.delete(firma)
        
        # Reset firma count
        documento.firma_count = 0
          # Reset document status to BORRADOR if there's still a draft version
        if documento.borrador_file_id:
            documento.estado = 'BORRADOR'
        else:
            # If no draft version exists, delete the document record
            db.session.delete(documento)
        
        # Get template configuration for this document type
        template_config = DocumentTemplateConfig.query.filter_by(document_type_key=documento.tipo).first()
        
        # If document affected estado when uploaded, revert those changes
        if template_config and template_config.estado_al_subir_firmado and concurso.estado_actual == template_config.estado_al_subir_firmado:
            # Revert to previous estado
            previous_estado = "CREADO"  # Default fallback
            
            # Try to find a more appropriate previous state - either the borrador estado or an earlier state
            if template_config.estado_al_generar_borrador:
                previous_estado = template_config.estado_al_generar_borrador
            else:
                # Look for previous estado in history
                prev_history = HistorialEstado.query.filter(
                    HistorialEstado.concurso_id == concurso_id,
                    HistorialEstado.estado != "DOCUMENTO_FIRMADO",
                    HistorialEstado.estado != "DOCUMENTO_SUBIDO_ELIMINADO"
                ).order_by(HistorialEstado.fecha.desc()).first()
                
                if prev_history:
                    previous_estado = prev_history.estado
            
            concurso.estado_actual = previous_estado
        
        # Handle subestado if it was modified by this document type
        if template_config and template_config.subestado_al_subir_firmado and concurso.subestado:
            try:
                # Try to parse existing subestado as JSON
                subestado_values = json.loads(concurso.subestado)
                if not isinstance(subestado_values, list):
                    subestado_values = [subestado_values]
                
                # Remove the value added by this document type if it exists
                firmado_subestado = f"firmado:{template_config.subestado_al_subir_firmado}"
                if firmado_subestado in subestado_values:
                    subestado_values.remove(firmado_subestado)
                # For backward compatibility, also check without prefix
                elif template_config.subestado_al_subir_firmado in subestado_values:
                    subestado_values.remove(template_config.subestado_al_subir_firmado)
                    
                    # Update subestado or set to null if empty
                    if subestado_values:
                        concurso.subestado = json.dumps(subestado_values)
                    else:
                        concurso.subestado = None
            except (json.JSONDecodeError, TypeError):
                # If subestado is not valid JSON, leave it as is
                pass
        
        # Add entry to history
        historial = HistorialEstado(
            concurso=concurso,
            estado="DOCUMENTO_SUBIDO_ELIMINADO",
            observaciones=f"Documento subido {documento.tipo} eliminado por {get_current_username()}"
        )
        db.session.add(historial)
        
        db.session.commit()
        flash('Documento subido eliminado exitosamente. El tribunal puede subir un nuevo documento.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el documento subido: {str(e)}', 'danger')
    
    return redirect(url_for('concursos.ver', concurso_id=concurso_id))

@concursos.route('/<int:concurso_id>/generar-documento/<string:document_type_key>', methods=['GET'])
@keycloak_login_required
@admin_required
def generar_documento(concurso_id, document_type_key):
    """
    Generic document generation route that handles all document types based on configuration.
    This centralizes document creation using the template configuration system.
    
    Args:
        concurso_id: ID of the concurso
        document_type_key: The document type key as defined in DocumentTemplateConfig
    """
    import time
    start_time = time.time()
    current_app.logger.info(f"[DOCUMENT_GEN] Starting document generation for concurso_id: {concurso_id}, document_type: {document_type_key}")
    
    concurso = Concurso.query.get_or_404(concurso_id)
    current_app.logger.info(f"[DOCUMENT_GEN] Concurso found: {concurso.expediente}")
    
    # Get the template configuration for this document type
    step_start = time.time()
    template_config = DocumentTemplateConfig.query.filter_by(
        document_type_key=document_type_key,
        is_active=True
    ).first()
    current_app.logger.debug(f"[DOCUMENT_GEN] Template config query took: {time.time() - step_start:.3f}s")
    
    if not template_config:
        current_app.logger.error(f"[DOCUMENT_GEN] No template configuration found for document_type: {document_type_key}")
        flash('No se encontró una configuración válida para este tipo de documento.', 'danger')
        return redirect(url_for('concursos.ver', concurso_id=concurso_id))
        
    # Log template configuration (Comportamiento del Documento fields)
    current_app.logger.info(f"[DOCUMENT_GEN] Template Config for {document_type_key}:")
    current_app.logger.info(f"  - Display Name: {template_config.display_name}")
    current_app.logger.info(f"  - Uses Considerandos Builder: {template_config.uses_considerandos_builder}")
    current_app.logger.info(f"  - Requires Tribunal Info: {template_config.requires_tribunal_info}")
    current_app.logger.info(f"  - Is Unique Per Concurso: {template_config.is_unique_per_concurso}")
    current_app.logger.info(f"  - Concurso Visibility: {template_config.concurso_visibility}")
    current_app.logger.info(f"  - Subida Directa: {template_config.subida_directa}")
    current_app.logger.info(f"  - Es Resolución: {template_config.es_res}")
    current_app.logger.info(f"  - Parentesco: {template_config.parentesco}")
    current_app.logger.info(f"  - Admin Can Send For Signature: {template_config.admin_can_send_for_signature}")
    current_app.logger.info(f"  - Tribunal Can Sign: {template_config.tribunal_can_sign}")
    current_app.logger.info(f"  - Google Doc ID: {template_config.google_doc_id}")

    # Check if the document should be visible for this concurso tipo
    if not template_config.is_visible_for_concurso_tipo(concurso.tipo):
        current_app.logger.warning(f"[DOCUMENT_GEN] Document not visible for concurso tipo: {concurso.tipo}")
        flash('Este documento no está disponible para este tipo de concurso.', 'warning')
        return redirect(url_for('concursos.ver', concurso_id=concurso_id))

    # Check uniqueness constraint if applicable
    if template_config.is_unique_per_concurso:
        step_start = time.time()
        existing_document = DocumentoConcurso.query.filter_by(
            concurso_id=concurso_id,
            tipo=document_type_key
        ).first()
        current_app.logger.debug(f"[DOCUMENT_GEN] Uniqueness check took: {time.time() - step_start:.3f}s")
        
        if existing_document:
            current_app.logger.warning(f"[DOCUMENT_GEN] Unique document already exists: {existing_document.id}")
            flash(f'Ya existe un documento de tipo {template_config.display_name} para este concurso.', 'warning')
            return redirect(url_for('concursos.ver', concurso_id=concurso_id))

    # If the template uses the considerandos builder, redirect to that route
    if template_config.uses_considerandos_builder:
        elapsed = time.time() - start_time
        current_app.logger.info(f"[DOCUMENT_GEN] Redirecting to considerandos builder after {elapsed:.3f}s")
        return redirect(url_for('concursos.considerandos_builder', 
                              concurso_id=concurso_id, 
                              document_type_key=document_type_key,
                              template_google_id=template_config.google_doc_id))
    
    # Otherwise, generate the document directly
    success, message, url = generar_documento_desde_template(
        concurso_id,
        template_config.google_doc_id,
        document_type_key
    )
    
    if success:
        flash(f'{message} <a href="{url}" target="_blank" class="alert-link">Abrir documento</a>', 'success')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('concursos.ver', concurso_id=concurso_id))

# Add the admin signature route
@concursos.route('/<int:concurso_id>/documento/<int:documento_id>/admin-firmar', methods=['POST'])
@keycloak_login_required
@admin_required
def admin_firmar_documento(concurso_id, documento_id):
    """Allow an admin to digitally sign a draft document."""    # Admin authentication is handled by the decorators above
    # Remove the old flask-login authentication check
    
    try:
        # Fetch concurso and document
        concurso = Concurso.query.get_or_404(concurso_id)
        documento = DocumentoConcurso.query.get_or_404(documento_id)
        
        # Check document belongs to this concurso
        if documento.concurso_id != concurso_id:
            flash('El documento no corresponde a este concurso', 'danger')
            return redirect(url_for('concursos.ver', concurso_id=concurso_id))
            
        # Get document template config
        template_config = DocumentTemplateConfig.query.filter_by(document_type_key=documento.tipo).first()
        if not template_config or not template_config.admin_can_sign:
            flash('Este tipo de documento no permite firma administrativa', 'danger')
            return redirect(url_for('concursos.ver', concurso_id=concurso_id))
            
        # Verify document is in BORRADOR state
        if documento.estado != 'BORRADOR':
            flash('Solo se pueden firmar documentos en estado BORRADOR', 'danger')
            return redirect(url_for('concursos.ver', concurso_id=concurso_id))
            
        # Verify document draft exists
        if not documento.borrador_file_id:
            flash('El documento no tiene un borrador para firmar', 'danger')
            return redirect(url_for('concursos.ver', concurso_id=concurso_id))
            
        # Verify concurso has documentos_firmados_folder
        if not concurso.documentos_firmados_folder_id:
            flash('El concurso no tiene una carpeta de documentos firmados configurada', 'danger')
            return redirect(url_for('concursos.ver', concurso_id=concurso_id))
            
        # Get admin persona record
        from app.models.models import Persona, User
        admin_persona = Persona.query.filter_by(username=get_current_username()).first()
        
        if not admin_persona:
            # Look for any admin persona records - if none found, use default information
            admin_personas = Persona.query.filter(Persona.username.like('%admin%')).all()
            if admin_personas:
                # Use the first admin-like persona found
                admin_persona = admin_personas[0]
                nombre = admin_persona.nombre
                apellido = admin_persona.apellido
                dni = admin_persona.dni
                cargo = getattr(admin_persona, 'cargo', 'Administrador')
            else:
                # Create default admin information if no Persona record exists
                nombre = "Admin"  # Default values
                apellido = "Sistema"
                dni = "00000000"
                cargo = "Administrador"
                
                # Try to get User record for better information
                admin_user = User.query.filter_by(username=get_current_username()).first()
                if admin_user:
                    username_parts = admin_user.username.split('.')
                    if len(username_parts) > 1:
                        nombre = username_parts[0].capitalize()
                        apellido = username_parts[1].capitalize()
        else:
            # Use admin's information for signing
            nombre = admin_persona.nombre
            apellido = admin_persona.apellido
            dni = admin_persona.dni
            
            # Use 'Administrador' as default cargo if not set
            cargo = getattr(admin_persona, 'cargo', 'Administrador')
            if not cargo:
                cargo = 'Administrador'
            
        # Get the draft document
        file_data = drive_api.get_file_content(documento.borrador_file_id)
        if not file_data or 'fileData' not in file_data:
            flash('No se pudo recuperar el documento para firmar', 'danger')
            return redirect(url_for('concursos.ver', concurso_id=concurso_id))
            
        # Decode base64 fileData
        import base64
        file_bytes = base64.b64decode(file_data.get('fileData'))
        file_name = file_data.get('fileName', f"documento_{documento.id}.pdf")
        mime_type = file_data.get('mimeType', 'application/pdf')
        
        # Handle conversion to PDF if needed
        if mime_type != 'application/pdf':
            # If the document is a Google Doc, the API might already return it as PDF
            if mime_type == 'application/vnd.google-apps.document':
                # Assuming API already converts to PDF
                pass
            else:
                flash('Solo se pueden firmar documentos en formato PDF', 'danger')
                return redirect(url_for('concursos.ver', concurso_id=concurso_id))
                
        # Add signature to PDF
        from app.helpers.pdf_utils import add_signature_stamp
        
        try:
            signed_pdf_bytes = add_signature_stamp(
                file_bytes, 
                apellido, 
                nombre, 
                dni, 
                cargo=cargo,
                signature_count=documento.firma_count
            )
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            flash(f'Error al firmar el documento: {str(e)}', 'danger')
            return redirect(url_for('concursos.ver', concurso_id=concurso_id))
            
        # Prepare filename for signed document
        if '.' in file_name:
            name_part, ext_part = file_name.rsplit('.', 1)
            signed_file_name = f"{name_part}_firmado_admin.{ext_part}"
        else:
            signed_file_name = f"{file_name}_firmado_admin.pdf"
            
        # Upload signed document
        try:
            file_id, web_view_link = drive_api.upload_document(
                concurso.documentos_firmados_folder_id,
                signed_file_name,
                signed_pdf_bytes,  # Pass bytes directly, not base64 encoded string
                'application/pdf'
            )
            
            # Update DocumentoConcurso record
            documento.file_id = file_id
            documento.url = web_view_link
            documento.estado = 'FIRMADO'
            documento.firma_count += 1
              # Add record to HistorialEstado
            historial = HistorialEstado(
                concurso_id=concurso_id,
                estado='FIRMADO',
                observaciones=f'Documento {documento.tipo} firmado digitalmente por {nombre} {apellido} (Cargo: {cargo})'
            )
            
            db.session.add(historial)
            db.session.commit()
            
            flash(f'Documento firmado exitosamente por {nombre} {apellido} (Cargo: {cargo})', 'success')
            return redirect(url_for('concursos.ver', concurso_id=concurso_id))
            
        except Exception as e:
            db.session.rollback()
            import traceback
            print(traceback.format_exc())
            flash(f'Error al subir el documento firmado: {str(e)}', 'danger')
            return redirect(url_for('concursos.ver', concurso_id=concurso_id))
            
    except Exception as e:
        db.session.rollback()
        import traceback
        print(traceback.format_exc())
        flash(f'Error inesperado: {str(e)}', 'danger')
        return redirect(url_for('concursos.ver', concurso_id=concurso_id))

@concursos.route('/<int:concurso_id>/crear-documento-subida-directa/<string:document_type_key>', methods=['POST'])
@keycloak_login_required
@admin_required
def crear_documento_subida_directa(concurso_id, document_type_key):
    """Create a document via direct upload for templates with subida_directa=True."""
    concurso = Concurso.query.get_or_404(concurso_id)
    
    # Get the template configuration for this document type
    template_config = DocumentTemplateConfig.query.filter_by(
        document_type_key=document_type_key,
        is_active=True
    ).first()
    
    if not template_config:
        flash('No se encontró una configuración válida para este tipo de documento.', 'danger')
        return redirect(url_for('concursos.ver', concurso_id=concurso_id))
    
    # Check if subida_directa is enabled for this template
    if not template_config.subida_directa:
        flash('Este tipo de documento no permite subida directa.', 'danger')
        return redirect(url_for('concursos.ver', concurso_id=concurso_id))
    
    # Check uniqueness constraint if applicable
    if template_config.is_unique_per_concurso:
        existing_document = DocumentoConcurso.query.filter_by(
            concurso_id=concurso_id,
            tipo=document_type_key
        ).first()
        
        if existing_document:
            flash(f'Ya existe un documento de tipo {template_config.display_name} para este concurso.', 'warning')
            return redirect(url_for('concursos.ver', concurso_id=concurso_id))
    
    if not concurso.documentos_firmados_folder_id:
        flash('El concurso no tiene una carpeta de documentos firmados asociada.', 'danger')
        return redirect(url_for('concursos.ver', concurso_id=concurso_id))
    
    try:
        file = request.files.get('documento_firmado')

        if not file:
            flash('No se seleccionó ningún archivo.', 'danger')
            return redirect(url_for('concursos.ver', concurso_id=concurso_id))

        # Collect resolution-specific fields (if applicable) before generating filename
        nro_res = None
        tipo_res = None
        fecha_res = None
        articulado = None

        if template_config.es_res:
            nro_res = request.form.get('numero_resolucion')
            tipo_res = request.form.get('tipo_resolucion')
            fecha_res_str = request.form.get('fecha_resolucion')
            if fecha_res_str:
                try:
                    fecha_res = datetime.strptime(fecha_res_str, '%Y-%m-%d').date()
                except ValueError:
                    flash('Formato de fecha inválido.', 'danger')
                    return redirect(url_for('concursos.ver', concurso_id=concurso_id))
            articulado = request.form.get('articulado')

        # Generate appropriate filename based on document type and metadata
        if template_config.es_res and nro_res and tipo_res:
            # Build a transient DocumentoConcurso-like object to reuse filename generator
            class _TmpDoc:
                pass
            tmp_doc = _TmpDoc()
            tmp_doc.nro_res = nro_res
            tmp_doc.tipo_res = tipo_res
            new_filename = generate_resolution_filename(tmp_doc, concurso, template_config, is_firmado=True)
        else:
            # Fallback to original naming for non-resolutions
            original_filename = document_type_key.lower().replace('_', ' ') + f"_concurso_{concurso.id}"
            new_filename = f"{original_filename}_firmado.pdf"

        # Upload to documentos_firmados folder
        file_data = file.read()
        file_id, web_view_link = drive_api.upload_document(
            concurso.documentos_firmados_folder_id,
            new_filename,
            file_data
        )

        # Create new document record directly as FIRMADO, now that we have file details
        documento = DocumentoConcurso(
            concurso_id=concurso_id,
            tipo=document_type_key,
            estado='FIRMADO',
            file_id=file_id,
            url=web_view_link,
            subida_directa=True  # Mark as direct upload
        )

        # If it's a resolution, persist resolution-specific fields on the record
        if template_config.es_res:
            documento.nro_res = nro_res
            documento.tipo_res = tipo_res
            documento.fecha_res = fecha_res
            documento.articulado = articulado

        # Update concurso resolution number based on parentesco (if resolution)
        if template_config.es_res:
            update_concurso_resolution_number(concurso, template_config, documento)

        db.session.add(documento)
        
        # Update concurso estado_actual and subestado if configured in template
        if template_config.estado_al_subir_firmado:
            concurso.estado_actual = template_config.estado_al_subir_firmado
            
        # Handle subestado
        if template_config.subestado_al_subir_firmado:
            if concurso.subestado:
                try:
                    subestado_values = json.loads(concurso.subestado)
                    if not isinstance(subestado_values, list):
                        subestado_values = [subestado_values]
                    
                    firmado_subestado = f"firmado:{template_config.subestado_al_subir_firmado}"
                    if firmado_subestado not in subestado_values:
                        subestado_values.append(firmado_subestado)
                        
                    concurso.subestado = json.dumps(subestado_values)
                except (json.JSONDecodeError, TypeError):
                    firmado_subestado = f"firmado:{template_config.subestado_al_subir_firmado}"
                    concurso.subestado = json.dumps([firmado_subestado])
            else:
                firmado_subestado = f"firmado:{template_config.subestado_al_subir_firmado}"
                concurso.subestado = json.dumps([firmado_subestado])
        
        # Add entry to history
        historial = HistorialEstado(
            concurso=concurso,
            estado="DOCUMENTO_SUBIDA_DIRECTA",
            observaciones=f"Documento {document_type_key} creado por subida directa por {get_current_username()}"
        )
        db.session.add(historial)
        
        db.session.commit()
        flash(f'Documento {template_config.display_name} subido exitosamente y marcado como firmado. <a href="{web_view_link}" target="_blank" class="alert-link">Ver documento</a>', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al subir el documento: {str(e)}', 'danger')
    
    return redirect(url_for('concursos.ver', concurso_id=concurso_id))

