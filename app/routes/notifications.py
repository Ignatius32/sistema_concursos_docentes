"""
Routes for notification campaigns in concursos docentes application.
Contains functionality for creating, editing, and triggering email notification campaigns.
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify, make_response
from app.utils.keycloak_auth import keycloak_login_required, get_current_username
from datetime import datetime
import json
import json

from app.models.models import db, Concurso, NotificationCampaign, NotificationLog, TribunalMiembro, Persona, Postulante, DocumentoConcurso, DocumentTemplateConfig, HistorialEstado
from app.integrations.google_drive import GoogleDriveAPI
from app.services.placeholder_resolver import get_core_placeholders, replace_text_with_placeholders
from app.helpers.api_services import get_departamento_heads_data
from app.utils.constants import DOCUMENTO_TIPOS

# Initialize blueprint
notifications_bp = Blueprint('notifications', __name__)
drive_api = GoogleDriveAPI()

def parse_email_lines(email_text):
    """Parse a string with one email per line into a list of emails."""
    if not email_text:
        return []
    
    emails = []
    for line in email_text.splitlines():
        line = line.strip()
        if line:  # Skip empty lines
            emails.append(line)
    
    return emails

@notifications_bp.route('/notifications/campaigns/nueva', methods=['GET'])
@keycloak_login_required
def crear_notificacion_campaign_form():
    """Display form to create a new notification campaign."""
    
    active_document_templates = DocumentTemplateConfig.query.filter_by(is_active=True).order_by(DocumentTemplateConfig.display_name).all()
    
    return render_template(
        'notifications/crear_editar_campana.html',
        form_action=url_for('notifications.crear_notificacion_campaign'),
        campaign=None,
        document_templates=active_document_templates
    )

@notifications_bp.route('/notifications/campaigns/nueva', methods=['POST'])
@keycloak_login_required
def crear_notificacion_campaign():
    """Handle creation of a new notification campaign."""
    try:        # Get form data
        nombre_campana = request.form.get('nombre_campana')
        asunto_email = request.form.get('asunto_email')
        cuerpo_email_html = request.form.get('cuerpo_email_html')
        otros_roles = request.form.getlist('otros_roles_destinatarios')  # This will get multiple values
        emails_estaticos = request.form.get('emails_estaticos', '')
        adjuntos_personalizados = request.form.get('adjuntos_personalizados', '')
        estado_al_enviar = request.form.get('estado_al_enviar', '').strip() or None
        subestado_al_enviar = request.form.get('subestado_al_enviar', '').strip() or None
        
        # Process custom attachment IDs
        adjuntos_personalizados_list = []
        if adjuntos_personalizados:
            for line in adjuntos_personalizados.splitlines():
                drive_id = line.strip()
                if drive_id:  # Skip empty lines
                    adjuntos_personalizados_list.append(drive_id)
        
        # Process document attachment configs
        documento_tipos_adjuntos_json = request.form.getlist('documento_concurso_tipos_adjuntos')
        parsed_document_configs = []
        
        for json_config in documento_tipos_adjuntos_json:
            try:
                doc_config = json.loads(json_config)
                if isinstance(doc_config, dict) and 'tipo' in doc_config and 'version' in doc_config:
                    parsed_document_configs.append(doc_config)
            except json.JSONDecodeError:
                current_app.logger.warning(f"Invalid document config JSON: {json_config}")
        
        # Process tribunal role-claustro selections
        tribunal_roles_claustro = request.form.getlist('tribunal_rol_claustro')
        tribunal_destinatarios = []
        
        for item in tribunal_roles_claustro:
            parts = item.split('_')
            if len(parts) == 2:
                rol, claustro = parts
                tribunal_destinatarios.append({'rol': rol, 'claustro': claustro})
        
        # Validate required fields
        if not nombre_campana or not asunto_email or not cuerpo_email_html:
            flash('Todos los campos son obligatorios', 'danger')
            return redirect(url_for('notifications.crear_notificacion_campaign_form'))
        
        # Construct destinatarios_config JSON
        destinatarios_config = {
            'tribunal_destinatarios': tribunal_destinatarios,
            'otros_roles_destinatarios': otros_roles,
            'emails_estaticos': parse_email_lines(emails_estaticos)
        }        # Create new campaign
        campaign = NotificationCampaign(
            nombre_campana=nombre_campana,
            asunto_email=asunto_email,
            cuerpo_email_html=cuerpo_email_html,
            documentos_adjuntos_config=parsed_document_configs,  # Store parsed document configs
            adjuntos_personalizados=adjuntos_personalizados_list,  # Store custom attachment IDs
            estado_al_enviar=estado_al_enviar,
            subestado_al_enviar=subestado_al_enviar,
            creado_por_id=None  # TODO: Update model to use Keycloak user ID or username
        )
        campaign.destinatarios_json = destinatarios_config
        db.session.add(campaign)
        db.session.commit()
        
        flash(f'La campaña "{nombre_campana}" ha sido creada con éxito', 'success')
        return redirect(url_for('notifications.list_notification_campaigns'))
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al crear campaña de notificación: {str(e)}")
        flash(f'Error al crear la campaña: {str(e)}', 'danger')
        return redirect(url_for('notifications.crear_notificacion_campaign_form'))

@notifications_bp.route('/notifications/campaigns/<int:campaign_id>/editar', methods=['GET'])
@keycloak_login_required
def editar_notificacion_campaign_form(campaign_id):
    """Display form to edit an existing notification campaign."""
    campaign = NotificationCampaign.query.get_or_404(campaign_id)
      # Format the static emails as newline-separated text
    emails_estaticos = '\n'.join(campaign.destinatarios_json.get('emails_estaticos', []))
    
    # Format the custom attachment IDs as newline-separated text
    adjuntos_personalizados = '\n'.join(campaign.adjuntos_personalizados or [])
    
    active_document_templates = DocumentTemplateConfig.query.filter_by(is_active=True).order_by(DocumentTemplateConfig.display_name).all()
    
    return render_template(
        'notifications/crear_editar_campana.html',
        form_action=url_for('notifications.editar_notificacion_campaign', campaign_id=campaign_id),
        campaign=campaign,
        emails_estaticos=emails_estaticos,
        adjuntos_personalizados=adjuntos_personalizados,
        document_templates=active_document_templates
    )

@notifications_bp.route('/notifications/campaigns/<int:campaign_id>/editar', methods=['POST'])
@keycloak_login_required
def editar_notificacion_campaign(campaign_id):
    """Handle updating of an existing notification campaign."""
    campaign = NotificationCampaign.query.get_or_404(campaign_id)
    
    try:
        # Get form data
        nombre_campana = request.form.get('nombre_campana')
        asunto_email = request.form.get('asunto_email')
        cuerpo_email_html = request.form.get('cuerpo_email_html')
        otros_roles = request.form.getlist('otros_roles_destinatarios')
        emails_estaticos = request.form.get('emails_estaticos', '')
        adjuntos_personalizados = request.form.get('adjuntos_personalizados', '')
        estado_al_enviar = request.form.get('estado_al_enviar', '').strip() or None
        subestado_al_enviar = request.form.get('subestado_al_enviar', '').strip() or None
        
        # Process custom attachment IDs
        adjuntos_personalizados_list = []
        if adjuntos_personalizados:
            for line in adjuntos_personalizados.splitlines():
                drive_id = line.strip()
                if drive_id:  # Skip empty lines
                    adjuntos_personalizados_list.append(drive_id)
        
        # Process document attachment configs
        documento_tipos_adjuntos_json = request.form.getlist('documento_concurso_tipos_adjuntos')
        parsed_document_configs = []
        
        for json_config in documento_tipos_adjuntos_json:
            try:
                doc_config = json.loads(json_config)
                if isinstance(doc_config, dict) and 'tipo' in doc_config and 'version' in doc_config:
                    parsed_document_configs.append(doc_config)
            except json.JSONDecodeError:
                current_app.logger.warning(f"Invalid document config JSON: {json_config}")
        
        # Process tribunal role-claustro selections
        tribunal_roles_claustro = request.form.getlist('tribunal_rol_claustro')
        tribunal_destinatarios = []
        
        for item in tribunal_roles_claustro:
            parts = item.split('_')
            if len(parts) == 2:
                rol, claustro = parts
                tribunal_destinatarios.append({'rol': rol, 'claustro': claustro})
        
        # Validate required fields
        if not nombre_campana or not asunto_email or not cuerpo_email_html:
            flash('Todos los campos son obligatorios', 'danger')
            return redirect(url_for('notifications.editar_notificacion_campaign_form', campaign_id=campaign_id))
        
        # Update campaign
        campaign.nombre_campana = nombre_campana
        campaign.asunto_email = asunto_email
        campaign.cuerpo_email_html = cuerpo_email_html
        campaign.documentos_adjuntos_config = parsed_document_configs  # Update document configs
        campaign.adjuntos_personalizados = adjuntos_personalizados_list  # Update custom attachment IDs
        campaign.estado_al_enviar = estado_al_enviar
        campaign.subestado_al_enviar = subestado_al_enviar
        campaign.destinatarios_json = {
            'tribunal_destinatarios': tribunal_destinatarios,
            'otros_roles_destinatarios': otros_roles,
            'emails_estaticos': parse_email_lines(emails_estaticos)
        }
        campaign.actualizado_en = datetime.utcnow()
        db.session.commit()
        
        flash(f'La campaña "{nombre_campana}" ha sido actualizada con éxito', 'success')
        return redirect(url_for('notifications.list_notification_campaigns'))
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al actualizar campaña de notificación: {str(e)}")
        flash(f'Error al actualizar la campaña: {str(e)}', 'danger')
        return redirect(url_for('notifications.editar_notificacion_campaign_form', campaign_id=campaign_id))

@notifications_bp.route('/notifications/campaigns/<int:campaign_id>/eliminar', methods=['POST'])
@keycloak_login_required
def eliminar_notificacion_campaign(campaign_id):
    """Handle deletion of a notification campaign."""
    campaign = NotificationCampaign.query.get_or_404(campaign_id)
    
    try:
        nombre_campana = campaign.nombre_campana
        db.session.delete(campaign)
        db.session.commit()
        flash(f'La campaña "{nombre_campana}" ha sido eliminada con éxito', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al eliminar campaña de notificación: {str(e)}")
        flash(f'Error al eliminar la campaña: {str(e)}', 'danger')
    
    return redirect(url_for('notifications.list_notification_campaigns'))

@notifications_bp.route('/notifications/campaigns', methods=['GET'])
@keycloak_login_required
def list_notification_campaigns():
    """Display all global notification campaign templates."""
    campaigns = NotificationCampaign.query.order_by(NotificationCampaign.creado_en.desc()).all()
    
    return render_template(
        'notifications/list_campaigns.html', 
        campaigns=campaigns
    )

@notifications_bp.route('/notifications/campaigns/export')
@keycloak_login_required
def export_campaigns():
    """Export all notification campaigns as JSON"""
    campaigns = NotificationCampaign.query.all()
    
    # Convert campaigns to dictionary format
    campaigns_data = []
    for campaign in campaigns:
        campaign_dict = {
            'nombre_campana': campaign.nombre_campana,
            'asunto_email': campaign.asunto_email,
            'cuerpo_email_html': campaign.cuerpo_email_html,
            'destinatarios_json': campaign.destinatarios_json,
            'documentos_adjuntos_config': campaign.documentos_adjuntos_config,
            'adjuntos_personalizados': campaign.adjuntos_personalizados,
            'estado_al_enviar': campaign.estado_al_enviar,
            'subestado_al_enviar': campaign.subestado_al_enviar,
            # Include metadata
            'creado_en': campaign.creado_en.isoformat() if campaign.creado_en else None,
            'actualizado_en': campaign.actualizado_en.isoformat() if campaign.actualizado_en else None,
            'creado_por_username': campaign.creado_por.username if campaign.creado_por else None
        }
        campaigns_data.append(campaign_dict)
    
    # Create export data with metadata
    export_data = {
        'export_metadata': {
            'export_date': datetime.utcnow().isoformat(),
            'total_campaigns': len(campaigns_data),
            'version': '1.0'
        },
        'campaigns': campaigns_data
    }
    
    # Create response with JSON file download
    response = make_response(json.dumps(export_data, indent=2, ensure_ascii=False))
    response.headers['Content-Type'] = 'application/json'
    response.headers['Content-Disposition'] = f'attachment; filename=notification_campaigns_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.json'
    
    flash(f'Campañas de notificación exportadas exitosamente. {len(campaigns_data)} campañas incluidas.', 'success')
    return response

@notifications_bp.route('/notifications/campaigns/import', methods=['GET', 'POST'])
@keycloak_login_required
def import_campaigns():
    """Import notification campaigns from JSON"""
    if request.method == 'GET':
        return render_template('notifications/import_campaigns.html')
    
    # Handle POST request (file upload)
    try:
        # Check if file was uploaded
        if 'import_file' not in request.files:
            flash('No se seleccionó ningún archivo.', 'danger')
            return render_template('notifications/import_campaigns.html')
        
        file = request.files['import_file']
        if file.filename == '':
            flash('No se seleccionó ningún archivo.', 'danger')
            return render_template('notifications/import_campaigns.html')
        
        if not file.filename.endswith('.json'):
            flash('Solo se permiten archivos JSON.', 'danger')
            return render_template('notifications/import_campaigns.html')
        
        # Read and parse the uploaded file
        file_content = file.read().decode('utf-8')
        import_data = json.loads(file_content)
        
        # Validate the import data structure
        if 'campaigns' not in import_data:
            flash('El archivo JSON debe contener una clave "campaigns".', 'danger')
            return render_template('notifications/import_campaigns.html')
        
        campaigns_data = import_data['campaigns']
        overwrite_existing = request.form.get('overwrite_existing') == 'on'
        
        imported_count = 0
        updated_count = 0
        skipped_count = 0
        errors = []
        
        for campaign_data in campaigns_data:
            try:
                # Check if campaign already exists (by nombre_campana)
                existing_campaign = NotificationCampaign.query.filter_by(
                    nombre_campana=campaign_data.get('nombre_campana')
                ).first()
                
                if existing_campaign and not overwrite_existing:
                    skipped_count += 1
                    continue
                
                # Prepare campaign data (excluding metadata fields)
                campaign_fields = {
                    'nombre_campana': campaign_data.get('nombre_campana'),
                    'asunto_email': campaign_data.get('asunto_email'),
                    'cuerpo_email_html': campaign_data.get('cuerpo_email_html'),
                    'destinatarios_json': campaign_data.get('destinatarios_json', {}),
                    'documentos_adjuntos_config': campaign_data.get('documentos_adjuntos_config', []),
                    'adjuntos_personalizados': campaign_data.get('adjuntos_personalizados', []),
                    'estado_al_enviar': campaign_data.get('estado_al_enviar'),
                    'subestado_al_enviar': campaign_data.get('subestado_al_enviar')
                }
                
                if existing_campaign:
                    # Update existing campaign
                    for field, value in campaign_fields.items():
                        setattr(existing_campaign, field, value)
                    existing_campaign.actualizado_en = datetime.utcnow()
                    updated_count += 1
                else:
                    # Create new campaign
                    campaign = NotificationCampaign(**campaign_fields)
                    campaign.creado_en = datetime.utcnow()
                    campaign.actualizado_en = datetime.utcnow()
                    campaign.creado_por_id = None  # TODO: Update when Keycloak integration is complete
                    db.session.add(campaign)
                    imported_count += 1
                    
            except Exception as e:
                errors.append(f"Error procesando campaña {campaign_data.get('nombre_campana', 'desconocida')}: {str(e)}")
        
        # Commit changes
        db.session.commit()
        
        # Show results
        success_msg = []
        if imported_count > 0:
            success_msg.append(f"{imported_count} campañas importadas")
        if updated_count > 0:
            success_msg.append(f"{updated_count} campañas actualizadas")
        if skipped_count > 0:
            success_msg.append(f"{skipped_count} campañas omitidas (ya existían)")
            
        if success_msg:
            flash(f"Importación completada: {', '.join(success_msg)}.", 'success')
        
        if errors:
            for error in errors:
                flash(error, 'warning')
                
        return redirect(url_for('notifications.list_notification_campaigns'))
        
    except json.JSONDecodeError:
        flash('El archivo no contiene un JSON válido.', 'danger')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al importar las campañas: {str(e)}")
        flash(f'Error al importar las campañas: {str(e)}', 'danger')
    
    return render_template('notifications/import_campaigns.html')

@notifications_bp.route('/concursos/<int:concurso_id>/notifications/campaigns/<int:campaign_id>/trigger', methods=['POST'])
@keycloak_login_required
def trigger_notification_campaign(concurso_id, campaign_id):
    """Trigger the sending of emails for a notification campaign in the context of a specific concurso."""    
    concurso = Concurso.query.get_or_404(concurso_id)
    campaign = NotificationCampaign.query.get_or_404(campaign_id)
    
    try:
        # Initialize set for unique email addresses
        resolved_emails = set()
        destination_names = {}  # Map of email -> name for personalization
        
        # Extract configuration from destinatarios_json
        config = campaign.destinatarios_json
        tribunal_destinatarios = config.get('tribunal_destinatarios', [])
        otros_roles = config.get('otros_roles_destinatarios', [])
        
        # Process tribunal members based on role and claustro combinations
        for tribunal_config in tribunal_destinatarios:
            rol = tribunal_config.get('rol')
            claustro = tribunal_config.get('claustro')
            
            if rol and claustro:
                # Get matching tribunal members
                miembros = TribunalMiembro.query.join(Persona).filter(
                    TribunalMiembro.concurso_id == concurso_id,
                    TribunalMiembro.rol == rol,
                    TribunalMiembro.claustro == claustro
                ).all()
                
                for m in miembros:
                    if m.persona and m.persona.correo:
                        resolved_emails.add(m.persona.correo)
                        destination_names[m.persona.correo] = f"{m.persona.nombre} {m.persona.apellido}"
        
        # Process other roles to resolve emails
        if 'postulantes' in otros_roles:
            postulantes = Postulante.query.filter_by(concurso_id=concurso_id).all()
            for p in postulantes:
                if p.correo:
                    resolved_emails.add(p.correo)
                    destination_names[p.correo] = f"{p.nombre} {p.apellido}"
        # Include only active applicants if requested
        if 'postulantes_activos' in otros_roles:
            postulantes_activos = Postulante.query.filter_by(concurso_id=concurso_id).all()
            for p in postulantes_activos:
                try:
                    estado_val = (p.estado or '').strip().lower()
                except Exception:
                    estado_val = ''
                if estado_val == 'activo' and p.correo:
                    resolved_emails.add(p.correo)
                    destination_names[p.correo] = f"{p.nombre} {p.apellido}"
        # Include only active applicants if requested
        if 'postulantes_activos' in otros_roles:
            postulantes_activos = Postulante.query.filter_by(concurso_id=concurso_id).all()
            for p in postulantes_activos:
                try:
                    estado_val = (p.estado or '').strip().lower()
                except Exception:
                    estado_val = ''
                if estado_val == 'activo' and p.correo:
                    resolved_emails.add(p.correo)
                    destination_names[p.correo] = f"{p.nombre} {p.apellido}"
        
        if 'jefe_departamento' in otros_roles:
            try:
                departamento_nombre = (concurso.departamento_rel.nombre or "") if concurso.departamento_rel else ""
                depto_norm = departamento_nombre.strip().lower()
                # Get department heads data from local DB helper
                dept_heads_data = get_departamento_heads_data()
                
                if dept_heads_data:
                    for head in dept_heads_data:
                        head_depto = (head.get('departamento') or '').strip().lower()
                        if head_depto == depto_norm:
                            head_email = head.get('email') or head.get('correo')
                            if head_email:
                                resolved_emails.add(head_email)
                                display_name = head.get('nombre') or head.get('responsable') or 'Jefe de Departamento'
                                destination_names[head_email] = display_name
            except Exception as e:
                current_app.logger.error(f"Error fetching department heads: {str(e)}")
                flash(f'Error al obtener datos de jefes de departamento: {str(e)}', 'warning')
          # Add static emails
        for email in config.get('emails_estaticos', []):
            if email:
                resolved_emails.add(email)
                
        # Collect document attachment file IDs
        attachment_file_ids = []
        if campaign.documentos_adjuntos_config and len(campaign.documentos_adjuntos_config) > 0:
            current_app.logger.info(f"Getting attachments for document configs: {campaign.documentos_adjuntos_config}")
            
            for doc_config in campaign.documentos_adjuntos_config:
                doc_tipo = doc_config.get('tipo')
                doc_version = doc_config.get('version')
                
                if not doc_tipo or not doc_version:
                    current_app.logger.warning(f"Skipping invalid document config: {doc_config}")
                    continue
                
                current_app.logger.info(f"Attempting to attach {doc_tipo} (version: {doc_version})")
                try:
                    # Find the relevant document for the concurso and type.
                    # We take the latest document for the specified type
                    documento = DocumentoConcurso.query.filter_by(
                        concurso_id=concurso_id,
                        tipo=doc_tipo
                    ).order_by(DocumentoConcurso.id.desc()).first()

                    if documento:
                        file_to_attach = None
                        if doc_version == "firmado":
                            if documento.file_id and documento.file_id.strip():
                                file_to_attach = documento.file_id
                                current_app.logger.info(f"Selected signed version: {documento.file_id} for {doc_tipo}")
                        elif doc_version == "borrador":
                            if documento.borrador_file_id and documento.borrador_file_id.strip():
                                file_to_attach = documento.borrador_file_id
                                current_app.logger.info(f"Selected draft version: {documento.borrador_file_id} for {doc_tipo}")
                        
                        if file_to_attach:
                            if file_to_attach not in attachment_file_ids: # Avoid duplicate attachments if configured multiple times
                                attachment_file_ids.append(file_to_attach)
                        else:
                            current_app.logger.warning(f"No suitable file ID found for {doc_tipo} (version: {doc_version}) for concurso {concurso_id}")
                    else:
                        current_app.logger.warning(f"No document found for type {doc_tipo} for concurso {concurso_id}")
                except Exception as e:
                    current_app.logger.error(f"Error retrieving document attachment of type {doc_tipo} (version: {doc_version}): {str(e)}")
                    flash(f'Error al adjuntar el documento de tipo {doc_tipo} ({doc_version}): {str(e)}', 'warning')
          # Add custom attachment IDs
        if campaign.adjuntos_personalizados and len(campaign.adjuntos_personalizados) > 0:
            current_app.logger.info(f"Adding custom attachments: {campaign.adjuntos_personalizados}")
            for file_id in campaign.adjuntos_personalizados:
                if file_id and file_id.strip() and file_id.strip() not in attachment_file_ids:
                    attachment_file_ids.append(file_id.strip())
                    current_app.logger.info(f"Added custom attachment with ID: {file_id}")
        
        # Begin sending emails
        sent_count = 0
        failed_count = 0
        
        for email_address in resolved_emails:
            try:
                # Look up if we have a recipient persona ID
                recipient_persona_id = None
                recipient_name = destination_names.get(email_address, "")
                
                # Try to find a persona associated with this email for personalized placeholders
                if recipient_name:
                    # This is a simplified lookup - in a real implementation, you may want to 
                    # use the email address to find the corresponding persona ID more accurately
                    persona = Persona.query.filter(
                        (Persona.correo == email_address) | 
                        ((Persona.nombre + ' ' + Persona.apellido) == recipient_name) |
                        ((Persona.apellido + ', ' + Persona.nombre) == recipient_name)
                    ).first()
                    
                    if persona:
                        recipient_persona_id = persona.id
                
                # Get placeholders for this concurso and recipient from the central resolver
                placeholders = get_core_placeholders(concurso_id, persona_id=recipient_persona_id)
                
                # Ensure the recipient name is in the placeholders
                if not placeholders.get('nombre_destinatario') and recipient_name:
                    placeholders['nombre_destinatario'] = recipient_name
                
                # Use the centralized text replacement function
                final_asunto = replace_text_with_placeholders(campaign.asunto_email, placeholders)
                final_cuerpo = replace_text_with_placeholders(campaign.cuerpo_email_html, placeholders)
                
                # Send email with attachments
                result = drive_api.send_email(
                    to_email=email_address,
                    subject=final_asunto,
                    html_body=final_cuerpo,
                    sender_name='Selecciones Docentes CRUB UNCo',
                    placeholders=placeholders,
                    attachment_ids=attachment_file_ids if attachment_file_ids else None
                )
                
                # Log the notification
                log = NotificationLog(
                    campaign_id=campaign.id,
                    concurso_id=concurso_id,
                    destinatario_email=email_address,
                    asunto_enviado=final_asunto,
                    cuerpo_enviado_html=final_cuerpo,
                    estado_envio="ENVIADO",
                    error_envio=None
                )
                db.session.add(log)
                sent_count += 1
                
            except Exception as e:                
                error_message = str(e)
                current_app.logger.error(f"Error sending notification to {email_address}: {error_message}")
                
                # Log the failed notification
                log = NotificationLog(
                    campaign_id=campaign.id,
                    concurso_id=concurso_id,
                    destinatario_email=email_address,
                    asunto_enviado=final_asunto if 'final_asunto' in locals() else campaign.asunto_email,
                    cuerpo_enviado_html=final_cuerpo if 'final_cuerpo' in locals() else campaign.cuerpo_email_html,
                    estado_envio="FALLIDO",
                    error_envio=error_message
                )
                db.session.add(log)
                failed_count += 1
        db.session.commit()
        
        # Update concurso estado and subestado if configured
        current_app.logger.info(f"Checking estado update: sent_count={sent_count}, campaign.estado_al_enviar='{campaign.estado_al_enviar}'")
        if sent_count > 0 and campaign.estado_al_enviar:
            try:
                current_app.logger.info(f"Updating concurso {concurso_id} estado from '{concurso.estado_actual}' to '{campaign.estado_al_enviar}'")
                old_estado = concurso.estado_actual
                old_subestado = concurso.subestado
                
                concurso.estado_actual = campaign.estado_al_enviar
                if campaign.subestado_al_enviar:
                    current_app.logger.info(f"Processing subestado update: current='{concurso.subestado}', adding='{campaign.subestado_al_enviar}'")
                    # Handle subestado accumulation
                    if concurso.subestado:
                        try:
                            # Try to parse existing subestado as JSON
                            subestado_values = json.loads(concurso.subestado)
                            if not isinstance(subestado_values, list):
                                subestado_values = [subestado_values]
                        except (json.JSONDecodeError, TypeError):
                            # If it's not valid JSON, treat as a single string value
                            subestado_values = [concurso.subestado]
                        
                        # Add new value if not already present
                        if campaign.subestado_al_enviar not in subestado_values:
                            subestado_values.append(campaign.subestado_al_enviar)
                            concurso.subestado = json.dumps(subestado_values)
                            current_app.logger.info(f"Updated subestado to: {concurso.subestado}")
                        else:
                            current_app.logger.info(f"Subestado '{campaign.subestado_al_enviar}' already exists, not adding")
                    else:
                        # If subestado is empty, initialize with a single value
                        concurso.subestado = json.dumps([campaign.subestado_al_enviar])
                        current_app.logger.info(f"Initialized subestado with: {concurso.subestado}")
                
                # Create history entry for estado change
                observaciones_parts = [f"Campaña de notificación '{campaign.nombre_campana}' enviada exitosamente a {sent_count} destinatarios"]
                if old_estado != campaign.estado_al_enviar:
                    observaciones_parts.append(f"Estado cambiado de '{old_estado}' a '{campaign.estado_al_enviar}'")
                if campaign.subestado_al_enviar and old_subestado != concurso.subestado:
                    observaciones_parts.append(f"Subestado actualizado: '{campaign.subestado_al_enviar}' agregado")
                
                historial = HistorialEstado(
                    concurso_id=concurso_id,
                    estado=campaign.estado_al_enviar,
                    subestado_snapshot=concurso.subestado,
                    fecha=datetime.now(),
                    observaciones=". ".join(observaciones_parts)
                )
                db.session.add(historial)
                
                db.session.commit()
                current_app.logger.info(f"Successfully updated concurso {concurso_id} estado_actual to '{campaign.estado_al_enviar}'")
            except Exception as e:
                current_app.logger.error(f"Error updating concurso estado: {str(e)}")
                db.session.rollback()
        else:
            current_app.logger.info(f"Estado update skipped: sent_count={sent_count}, estado_al_enviar='{campaign.estado_al_enviar}'")
        
        # Flash summary message
        attachment_count = len(attachment_file_ids) if attachment_file_ids else 0
        if sent_count > 0 and failed_count == 0:
            flash(f'Campaña "{campaign.nombre_campana}" enviada con éxito a {sent_count} destinatarios con {attachment_count} documentos adjuntos.', 'success')
        elif sent_count > 0 and failed_count > 0:
            flash(f'Campaña "{campaign.nombre_campana}" enviada parcialmente: {sent_count} exitosos, {failed_count} fallidos, {attachment_count} documentos adjuntos.', 'warning')
        elif sent_count == 0 and failed_count > 0:
            flash(f'Error al enviar la campaña "{campaign.nombre_campana}". Todos los {failed_count} envíos fallaron.', 'danger')
        else:
            flash(f'No se encontraron destinatarios para la campaña "{campaign.nombre_campana}".', 'warning')
    except Exception as e:
        db.session.rollback()        
        current_app.logger.error(f"Error al ejecutar campaña de notificación: {str(e)}")
        flash(f'Error al ejecutar la campaña: {str(e)}', 'danger')
        # In case of error, redirect to the modal
        return redirect(url_for('concursos.ver', concurso_id=concurso_id) + '#notificacionesModal')
    
    # On success, redirect without opening the modal
    return redirect(url_for('concursos.ver', concurso_id=concurso_id))

@notifications_bp.route('/concursos/<int:concurso_id>/notifications/campaigns/<int:campaign_id>/preview', methods=['GET'])
@keycloak_login_required
def preview_notification_campaign(concurso_id, campaign_id):
    """Get preview data for a notification campaign."""
    concurso = Concurso.query.get_or_404(concurso_id)
    campaign = NotificationCampaign.query.get_or_404(campaign_id)
    
    try:
        # Initialize set for unique email addresses
        resolved_emails = set()
        destination_names = {}  # Map of email -> name for personalization
        
        # Extract configuration from destinatarios_json
        config = campaign.destinatarios_json
        tribunal_destinatarios = config.get('tribunal_destinatarios', [])
        otros_roles = config.get('otros_roles_destinatarios', [])
        
        # Process tribunal members based on role and claustro combinations
        for tribunal_config in tribunal_destinatarios:
            rol = tribunal_config.get('rol')
            claustro = tribunal_config.get('claustro')
            
            if rol and claustro:
                # Get matching tribunal members
                miembros = TribunalMiembro.query.join(Persona).filter(
                    TribunalMiembro.concurso_id == concurso_id,
                    TribunalMiembro.rol == rol,
                    TribunalMiembro.claustro == claustro
                ).all()
                
                for m in miembros:
                    if m.persona and m.persona.correo:
                        resolved_emails.add(m.persona.correo)
                        destination_names[m.persona.correo] = f"{m.persona.nombre} {m.persona.apellido}"
        
        # Process other roles to resolve emails
        if 'postulantes' in otros_roles:
            postulantes = Postulante.query.filter_by(concurso_id=concurso_id).all()
            for p in postulantes:
                if p.correo:
                    resolved_emails.add(p.correo)
                    destination_names[p.correo] = f"{p.nombre} {p.apellido}"
        
        if 'jefe_departamento' in otros_roles:
            try:
                departamento_nombre = (concurso.departamento_rel.nombre or "") if concurso.departamento_rel else ""
                depto_norm = departamento_nombre.strip().lower()
                # Get department heads data from local DB helper
                dept_heads_data = get_departamento_heads_data()
                
                if dept_heads_data:
                    for head in dept_heads_data:
                        head_depto = (head.get('departamento') or '').strip().lower()
                        if head_depto == depto_norm:
                            head_email = head.get('email') or head.get('correo')
                            if head_email:
                                resolved_emails.add(head_email)
                                display_name = head.get('nombre') or head.get('responsable') or 'Jefe de Departamento'
                                destination_names[head_email] = display_name
            except Exception as e:
                current_app.logger.warning(f"Could not get department head data: {e}")
        
        # Add static emails
        static_emails = config.get('emails_estaticos', [])
        for email in static_emails:
            resolved_emails.add(email)
            if email not in destination_names:
                destination_names[email] = email  # Use email as name if no name available
        
        # Get core placeholders for preview
        placeholders = get_core_placeholders(concurso_id)
        
        # Replace placeholders in subject and body
        preview_subject = replace_text_with_placeholders(campaign.asunto_email, placeholders)
        preview_body = replace_text_with_placeholders(campaign.cuerpo_email_html, placeholders)
        
        # Get document attachments info
        document_attachments = []
        if campaign.documentos_adjuntos_config:
            for doc_config in campaign.documentos_adjuntos_config:
                doc_tipo = doc_config.get('tipo')
                doc_version = doc_config.get('version')
                
                # Get document if it exists
                documento = DocumentoConcurso.query.filter_by(
                    concurso_id=concurso_id,
                    tipo=doc_tipo
                ).order_by(DocumentoConcurso.id.desc()).first()
                
                # Get template config name for display
                template_config = DocumentTemplateConfig.query.filter_by(
                    document_type_key=doc_tipo,
                    is_active=True
                ).first()
                template_name = template_config.display_name if template_config else doc_tipo
                
                document_attachments.append({
                    'tipo': doc_tipo,
                    'version': doc_version,
                    'template_name': template_name,
                    'exists': documento is not None,
                    'filename': f"{template_name}_{concurso.expediente}.pdf" if documento else f"{template_name}_NO_GENERADO.pdf"
                })
        
        # Get custom attachments info
        custom_attachments = []
        if campaign.adjuntos_personalizados:
            for attachment_id in campaign.adjuntos_personalizados:
                custom_attachments.append({
                    'id': attachment_id,
                    'name': f'Adjunto personalizado ({attachment_id[:10]}...)',
                    'exists': True  # Assume it exists, will be verified when sending
                })
        
        preview_data = {
            'campaign_name': campaign.nombre_campana,
            'subject': preview_subject,
            'body_html': preview_body,
            'recipients': [{'email': email, 'name': destination_names.get(email, email)} for email in sorted(resolved_emails)],
            'recipient_count': len(resolved_emails),
            'document_attachments': document_attachments,
            'custom_attachments': custom_attachments,
            'estado_change': {
                'estado_actual': concurso.estado_actual,
                'nuevo_estado': campaign.estado_al_enviar,
                'subestado_actual': concurso.subestado,
                'nuevo_subestado': campaign.subestado_al_enviar
            } if campaign.estado_al_enviar else None
        }
        
        return jsonify(preview_data)
        
    except Exception as e:
        current_app.logger.error(f"Error generating notification preview: {str(e)}")
        return jsonify({'error': str(e)}), 500
