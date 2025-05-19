"""
Routes for notification campaigns in concursos docentes application.
Contains functionality for creating, editing, and triggering email notification campaigns.
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import login_required, current_user
from datetime import datetime
import json

from app.models.models import db, Concurso, NotificationCampaign, NotificationLog, TribunalMiembro, Persona, Postulante, DocumentoConcurso, DocumentTemplateConfig
from app.integrations.google_drive import GoogleDriveAPI
from app.services.placeholder_resolver import get_core_placeholders, replace_text_with_placeholders
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
@login_required
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
@login_required
def crear_notificacion_campaign():
    """Handle creation of a new notification campaign."""
    
    try:        # Get form data
        nombre_campana = request.form.get('nombre_campana')
        asunto_email = request.form.get('asunto_email')
        cuerpo_email_html = request.form.get('cuerpo_email_html')
        otros_roles = request.form.getlist('otros_roles_destinatarios')  # This will get multiple values
        emails_estaticos = request.form.get('emails_estaticos', '')
        adjuntos_personalizados = request.form.get('adjuntos_personalizados', '')
        
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
        }          # Create new campaign
        campaign = NotificationCampaign(
            nombre_campana=nombre_campana,
            asunto_email=asunto_email,
            cuerpo_email_html=cuerpo_email_html,
            documentos_adjuntos_config=parsed_document_configs,  # Store parsed document configs
            adjuntos_personalizados=adjuntos_personalizados_list,  # Store custom attachment IDs
            creado_por_id=current_user.id
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
@login_required
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
@login_required
def editar_notificacion_campaign(campaign_id):
    """Handle updating of an existing notification campaign."""
    campaign = NotificationCampaign.query.get_or_404(campaign_id)
    try:        # Get form data
        nombre_campana = request.form.get('nombre_campana')
        asunto_email = request.form.get('asunto_email')
        cuerpo_email_html = request.form.get('cuerpo_email_html')
        otros_roles = request.form.getlist('otros_roles_destinatarios')
        emails_estaticos = request.form.get('emails_estaticos', '')
        adjuntos_personalizados = request.form.get('adjuntos_personalizados', '')
        
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
            return redirect(url_for('notifications.editar_notificacion_campaign_form', campaign_id=campaign_id))          # Update campaign
        campaign.nombre_campana = nombre_campana
        campaign.asunto_email = asunto_email
        campaign.cuerpo_email_html = cuerpo_email_html
        campaign.documentos_adjuntos_config = parsed_document_configs  # Update document configs
        campaign.adjuntos_personalizados = adjuntos_personalizados_list  # Update custom attachment IDs
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
@login_required
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
@login_required
def list_notification_campaigns():
    """Display all global notification campaign templates."""
    campaigns = NotificationCampaign.query.order_by(NotificationCampaign.creado_en.desc()).all()
    
    return render_template(
        'notifications/list_campaigns.html', 
        campaigns=campaigns
    )

@notifications_bp.route('/concursos/<int:concurso_id>/notifications/campaigns/<int:campaign_id>/trigger', methods=['POST'])
@login_required
def trigger_notification_campaign(concurso_id, campaign_id):
    """Trigger the sending of emails for a notification campaign in the context of a specific concurso."""
    concurso = Concurso.query.get_or_404(concurso_id)
    campaign = NotificationCampaign.query.get_or_404(campaign_id)
    
    try:        # Initialize set for unique email addresses
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
                departamento_nombre = concurso.departamento_rel.nombre if concurso.departamento_rel else ""
                # Get department heads data from API
                dept_heads_data = get_departamento_heads_data()
                
                if dept_heads_data:
                    for head in dept_heads_data:
                        if head.get('departamento') == departamento_nombre:
                            head_email = head.get('email')
                            if head_email:
                                resolved_emails.add(head_email)
                                destination_names[head_email] = head.get('nombre', 'Jefe de Departamento')
            except Exception as e:
                current_app.logger.error(f"Error fetching department heads: {str(e)}")
                flash(f'Error al obtener datos de jefes de departamento: {str(e)}', 'warning')
        
        # Add static emails
        for email in config.get('emails_estaticos', []):
            if email:
                resolved_emails.add(email)          # Collect document attachment file IDs
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
                    sender_name='Sistema de Concursos Docentes',
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
