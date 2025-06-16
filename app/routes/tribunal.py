from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session, send_file, current_app, g
from app.models.models import db, Concurso, TribunalMiembro, Recusacion, DocumentoTribunal, HistorialEstado, DocumentoConcurso, FirmaDocumento, Persona, Postulante, Sustanciacion, Categoria, DocumentoPostulante
from app.integrations.google_drive import GoogleDriveAPI
from app.integrations.keycloak_admin_client import KeycloakAdminClient
from app.helpers.pdf_utils import add_signature_stamp, verify_signed_pdf, merge_postulante_documents
from app.helpers.api_services import get_asignaturas_from_external_api
from app.utils.keycloak_auth import (
    keycloak_login_required, 
    admin_required, 
    tribunal_required,
    get_current_user_info,
    get_current_user_email,
    get_current_user_name,
    get_current_username
)
from app.config.keycloak_config import KeycloakConfig
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from functools import wraps
import secrets
import hashlib
import os
import io
import base64

tribunal = Blueprint('tribunal', __name__, url_prefix='/tribunal')
drive_api = GoogleDriveAPI()

# Token utilities for password reset
def generate_reset_token(user_id: str, expiry_hours: int = 24) -> str:
    """Generate a secure reset token for password reset."""
    # Create a random token
    random_token = secrets.token_urlsafe(32)
    
    # Create expiry timestamp
    expiry = datetime.utcnow() + timedelta(hours=expiry_hours)
    expiry_str = expiry.isoformat()
    
    # Create the payload: user_id|expiry|random_token
    payload = f"{user_id}|{expiry_str}|{random_token}"
    
    # Create a hash using a secret key (you should store this in config)
    secret_key = os.environ.get('RESET_TOKEN_SECRET', 'your-secret-key-here')
    signature = hashlib.sha256(f"{payload}|{secret_key}".encode()).hexdigest()
    
    # Combine payload and signature
    token = f"{payload}|{signature}"
    
    # URL-safe base64 encode
    import base64
    return base64.urlsafe_b64encode(token.encode()).decode()

def verify_reset_token(token: str) -> dict:
    """Verify and decode a reset token."""
    try:
        import base64
        
        # Decode from base64
        decoded = base64.urlsafe_b64decode(token.encode()).decode()
        
        # Split the token
        parts = decoded.split('|')
        if len(parts) != 4:
            return {'valid': False, 'error': 'Invalid token format'}
        
        user_id, expiry_str, random_token, signature = parts
        
        # Verify signature
        secret_key = os.environ.get('RESET_TOKEN_SECRET', 'your-secret-key-here')
        expected_signature = hashlib.sha256(f"{user_id}|{expiry_str}|{random_token}|{secret_key}".encode()).hexdigest()
        
        if signature != expected_signature:
            return {'valid': False, 'error': 'Invalid token signature'}
        
        # Check expiry
        expiry = datetime.fromisoformat(expiry_str)
        if datetime.utcnow() > expiry:
            return {'valid': False, 'error': 'Token has expired'}
        
        return {
            'valid': True,
            'user_id': user_id,
            'expiry': expiry
        }
        
    except Exception as e:
        return {'valid': False, 'error': f'Token verification failed: {str(e)}'}

def send_reset_email_internal(persona: Persona, keycloak_user_id: str) -> bool:
    """Send password reset email using Google Drive email system."""
    try:
        # Generate reset token
        reset_token = generate_reset_token(keycloak_user_id)
        
        # Build reset URL pointing to our app
        reset_url = url_for('tribunal.reset_password', token=reset_token, _external=True)
        
        # Use Google Drive email system
        try:
            # Initialize Google Drive API
            drive_api = GoogleDriveAPI()
            
            # Email subject
            subject = "Configurar Contraseña - Portal de Tribunal"
            
            # HTML email body with placeholders
            html_body = """
            <!DOCTYPE html>
            <html lang="es">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Configurar Contraseña - Portal de Tribunal</title>
                <style>
                    body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }
                    .header { background-color: #007bff; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }
                    .content { background-color: #f8f9fa; padding: 30px; border: 1px solid #dee2e6; border-top: none; }
                    .button { display: inline-block; background-color: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; margin: 20px 0; font-weight: bold; }
                    .footer { background-color: #e9ecef; padding: 15px; border: 1px solid #dee2e6; border-top: none; border-radius: 0 0 5px 5px; font-size: 0.9em; color: #6c757d; }
                    .warning { background-color: #fff3cd; border: 1px solid #ffeaa7; color: #856404; padding: 15px; border-radius: 5px; margin: 15px 0; }
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>Portal de Tribunal</h1>
                    <p>Sistema de Concursos Docentes</p>
                </div>
                
                <div class="content">
                    <h2>Hola <<nombre>> <<apellido>>,</h2>
                    
                    <p>Ha sido designado(a) como miembro del tribunal para un concurso docente. Para acceder al Portal de Tribunal, necesita configurar su contraseña de acceso.</p>
                    
                    <p>Haga clic en el siguiente enlace para configurar su contraseña:</p>
                    
                    <div style="text-align: center;">
                        <a href="<<reset_url>>" class="button">Configurar Contraseña</a>
                    </div>
                    
                    <div class="warning">
                        <strong>Importante:</strong>
                        <ul>
                            <li>Este enlace es válido por 24 horas</li>
                            <li>Solo puede ser usado una vez</li>
                            <li>No comparta este enlace con otras personas</li>
                        </ul>
                    </div>
                    
                    <p>Una vez que configure su contraseña, podrá acceder al Portal de Tribunal usando su correo electrónico y la contraseña que haya elegido.</p>
                    
                    <p>Si tiene problemas para acceder o no solicitó este acceso, contacte al administrador del sistema.</p>
                </div>
                
                <div class="footer">
                    <p><strong>Sistema de Concursos Docentes</strong></p>
                    <p>Este es un mensaje automático, por favor no responda a este correo.</p>
                    <p>Si no puede hacer clic en el enlace, copie y pegue la siguiente URL en su navegador:</p>
                    <p style="word-break: break-all; font-size: 0.8em;"><<reset_url>></p>
                </div>
            </body>
            </html>
            """
            
            # Placeholders for email content
            placeholders = {
                'nombre': persona.nombre,
                'apellido': persona.apellido,
                'reset_url': reset_url,
                'correo': persona.correo
            }
            
            # Send email via Google Drive API
            result = drive_api.send_email(
                to_email=persona.correo,
                subject=subject,
                html_body=html_body,
                sender_name="Sistema de Concursos Docentes",
                placeholders=placeholders
            )
            
            current_app.logger.info(f"Password reset email sent successfully to {persona.correo} via Google Drive")
            current_app.logger.info(f"Reset URL: {reset_url}")
            
            # Show success message in development
            if current_app.debug:
                flash(f'Email de configuración enviado a {persona.correo}. Reset URL: <a href="{reset_url}" target="_blank">{reset_url}</a>', 'info')
            
            return True
            
        except Exception as email_error:
            current_app.logger.error(f"Failed to send email via Google Drive: {email_error}")
            
            # Fallback: Log the URL for manual testing
            current_app.logger.info(f"EMAIL FALLBACK - Password reset URL for {persona.correo}: {reset_url}")
            current_app.logger.info(f"Reset token: {reset_token}")
            
            # In development, show the link in the UI as fallback
            if current_app.debug:
                flash(f'Error enviando email, pero enlace generado: <a href="{reset_url}" target="_blank">Configurar contraseña para {persona.correo}</a>', 'warning')
            
            return True  # Return True because token was generated successfully
        
    except Exception as e:
        current_app.logger.error(f"Error generating reset email: {e}")
        return False



def notify_tribunal_member_with_reset(persona: Persona, keycloak_admin: KeycloakAdminClient) -> dict:
    """
    Notify a tribunal member with password reset link using Drive integration.
    Returns dict with success status and message.
    """
    try:
        if not persona.correo:
            return {
                'success': False,
                'message': f'{persona.nombre} {persona.apellido} no tiene correo registrado'
            }
        
        # Find user in Keycloak by email
        keycloak_user = keycloak_admin.get_user_by_email(persona.correo)        
        if not keycloak_user:
            return {
                'success': False,
                'message': f'Usuario {persona.nombre} {persona.apellido} no encontrado en Keycloak.'
            }
        
        # Use our internal reset system with Drive integration
        success = send_reset_email_internal(persona, keycloak_user['id'])
        
        if success:
            return {
                'success': True,
                'message': f'Email de configuración enviado a {persona.nombre} {persona.apellido} via Drive.',
                'keycloak_user_id': keycloak_user['id']
            }
        else:
            return {
                'success': False,
                'message': f'Error al enviar email a {persona.nombre} {persona.apellido}.'
            }
            
    except Exception as e:
        return {
            'success': False,
            'message': f'Error procesando {persona.nombre} {persona.apellido}: {str(e)}'
        }

def tribunal_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'persona_id' not in session:
            flash('Debe iniciar sesión como miembro del tribunal para acceder.', 'warning')
            return redirect(url_for('tribunal.acceso'))
        return f(*args, **kwargs)
    return decorated_function

@tribunal.route('/concurso/<int:concurso_id>')
@admin_required
def index(concurso_id):
    """Display tribunal members for a specific concurso."""
    concurso = Concurso.query.get_or_404(concurso_id)
    miembros = TribunalMiembro.query.filter_by(concurso_id=concurso_id).join(Persona).all()
    return render_template('tribunal/index.html', concurso=concurso, miembros=miembros)

@tribunal.route('/concurso/<int:concurso_id>/agregar', methods=['GET', 'POST'])
@admin_required
def agregar(concurso_id):
    """Add multiple members to the tribunal of a concurso."""
    current_app.logger.info(f"agregar() called - Method: {request.method}, Content-Type: {request.content_type}")
    current_app.logger.info(f"Request is_json: {request.is_json}")
    current_app.logger.info(f"Request form data: {dict(request.form)}")
    current_app.logger.info(f"Request JSON data: {request.get_json(silent=True)}")
    
    concurso = Concurso.query.get_or_404(concurso_id)
    
    if request.method == 'POST':
        current_app.logger.info(f"POST request to agregar - Content-Type: {request.content_type}, is_json: {request.is_json}")
        try:
            # Handle multiple member additions
            json_data = request.get_json() if request.is_json else None
            current_app.logger.info(f"JSON data received: {json_data}")
            
            if json_data:
                # Extract members array from JSON data
                if 'members' in json_data:
                    members_data = json_data['members']
                else:
                    members_data = json_data  # Backwards compatibility
                
                current_app.logger.info(f"Members data extracted: {members_data}")
                # JSON request for multiple members
                return agregar_multiple_members(concurso_id, members_data)
            else:
                # Traditional form submission for single member (backward compatibility)
                return agregar_single_member(concurso_id, concurso)
                        
        except Exception as e:
            db.session.rollback()
            if request.is_json:
                return jsonify({
                    'success': False,
                    'errors': [f'Error al procesar la solicitud: {str(e)}'],
                    'message': 'Error interno del servidor'
                }), 500
            else:
                flash(f'Error al procesar la solicitud: {str(e)}', 'danger')
                return redirect(url_for('tribunal.agregar', concurso_id=concurso_id))
    
    # GET request - show the form
    # Get available personas for selection (exclude those already assigned to this concurso)
    assigned_persona_ids = db.session.query(TribunalMiembro.persona_id).filter_by(concurso_id=concurso_id).subquery()
    available_personas = Persona.query.filter(~Persona.id.in_(db.select(assigned_persona_ids))).order_by(Persona.apellido, Persona.nombre).all()
    
    # Get existing members for this concurso
    existing_members = TribunalMiembro.query.filter_by(concurso_id=concurso_id).join(Persona).order_by(Persona.apellido, Persona.nombre).all()
    
    return render_template('tribunal/agregar.html', 
                          concurso=concurso, 
                          available_personas=available_personas,
                          existing_members=existing_members)

def agregar_single_member(concurso_id, concurso):
    """Handle single member addition (backward compatibility)."""
    # Extract form data
    rol = request.form.get('rol')
    claustro = request.form.get('claustro')
    persona_id = request.form.get('persona_id')
    
    if not persona_id:
        flash('Debe seleccionar una persona existente.', 'danger')
        return redirect(url_for('tribunal.agregar', concurso_id=concurso_id))
    
    # Find the existing persona
    persona = Persona.query.get_or_404(persona_id)
    
    # Check if this persona is already assigned to this concurso
    existing_assignment = TribunalMiembro.query.filter_by(
        persona_id=persona.id, 
        concurso_id=concurso_id
    ).first()
    
    if existing_assignment:
        flash(f'La persona {persona.nombre} {persona.apellido} ya está asignada a este concurso como {existing_assignment.rol}.', 'warning')
        return redirect(url_for('tribunal.index', concurso_id=concurso_id))
    
    # Create the tribunal member
    success = create_tribunal_member(concurso, persona, rol, claustro)
    
    if success:
        flash('Miembro del tribunal asignado exitosamente.', 'success')
        return redirect(url_for('tribunal.index', concurso_id=concurso_id))
    else:
        return redirect(url_for('tribunal.agregar', concurso_id=concurso_id))

def agregar_multiple_members(concurso_id, members_data):
    """Handle multiple member additions via JSON."""
    current_app.logger.info(f"agregar_multiple_members called with {len(members_data) if members_data else 0} members")
    concurso = Concurso.query.get_or_404(concurso_id)
    added_members = []
    errors = []
    
    for member_data in members_data:
        persona_id = member_data.get('persona_id')
        rol = member_data.get('rol')
        claustro = member_data.get('claustro', 'Docente')
        
        # Get permissions from the data (convert string values to boolean)
        permissions = {
            'can_add_tema': member_data.get('can_add_tema') in ['1', True, 'true', 'True'],
            'can_upload_file': member_data.get('can_upload_file') in ['1', True, 'true', 'True'],
            'can_sign_file': member_data.get('can_sign_file') in ['1', True, 'true', 'True'],
            'can_view_postulante_docs': member_data.get('can_view_postulante_docs') in ['1', True, 'true', 'True']
        }
        
        if not persona_id or not rol:
            errors.append('Datos incompletos para uno de los miembros')
            continue
            
        # Find the persona
        persona = Persona.query.get(persona_id)
        if not persona:
            errors.append(f'Persona con ID {persona_id} no encontrada')
            continue
            
        # Check if already assigned
        existing_assignment = TribunalMiembro.query.filter_by(
            persona_id=persona.id, 
            concurso_id=concurso_id
        ).first()
        
        if existing_assignment:
            errors.append(f'{persona.nombre} {persona.apellido} ya está asignado como {existing_assignment.rol}')
            continue
        
        # Create the tribunal member with custom permissions
        current_app.logger.info(f"Attempting to create tribunal member: {persona.nombre} {persona.apellido} - {rol}")
        current_app.logger.info(f"Permissions: {permissions}")
        member_id = create_tribunal_member(concurso, persona, rol, claustro, permissions)
        
        if member_id:
            added_members.append({
                'id': member_id,
                'persona_id': persona.id,
                'name': f'{persona.nombre} {persona.apellido}',
                'rol': rol,
                'claustro': claustro
            })
            current_app.logger.info(f"Successfully added: {persona.nombre} {persona.apellido} with ID {member_id}")
        else:
            errors.append(f'Error al agregar {persona.nombre} {persona.apellido}')
            current_app.logger.error(f"Failed to add: {persona.nombre} {persona.apellido}")
    
    # Return JSON response
    success = len(added_members) > 0
    response_data = {
        'success': success,
        'members': added_members,
        'errors': errors,
        'message': f'Se agregaron {len(added_members)} miembros al tribunal' if success else 'No se pudo agregar ningún miembro'
    }
    
    current_app.logger.info(f"Returning response: {response_data}")
    return jsonify(response_data), 200 if success else 400

def create_tribunal_member(concurso, persona, rol, claustro, custom_permissions=None):
    """Create a tribunal member with proper permissions and Keycloak role."""
    try:
        current_app.logger.info(f"Creating tribunal member: {persona.nombre} {persona.apellido}, rol: {rol}, claustro: {claustro}")
        current_app.logger.info(f"Custom permissions: {custom_permissions}")
        
        # Ensure user has tribunal role in Keycloak
        if persona.keycloak_user_id:
            try:
                keycloak_admin = KeycloakAdminClient()
                if not keycloak_admin.has_client_role(persona.keycloak_user_id, KeycloakConfig.KEYCLOAK_TRIBUNAL_ROLE):
                    keycloak_admin.assign_client_role(persona.keycloak_user_id, KeycloakConfig.KEYCLOAK_TRIBUNAL_ROLE)
                    current_app.logger.info(f"Assigned tribunal role to user {persona.keycloak_user_id}")
            except Exception as e:
                current_app.logger.warning(f"Could not assign tribunal role to user {persona.keycloak_user_id}: {e}")
        
        # Create Google Drive folder for tribunal member
        folder_id = drive_api.create_tribunal_folder(
            parent_folder_id=concurso.tribunal_folder_id,
            nombre=persona.nombre,
            apellido=persona.apellido,
            dni=persona.dni,
            rol=rol
        )
        
        # Create new tribunal member assignment
        miembro = TribunalMiembro(
            concurso_id=concurso.id,
            persona_id=persona.id,
            rol=rol,
            claustro=claustro,
            drive_folder_id=folder_id,
            notificado=False
        )
        
        # Set permissions based on custom permissions or default role-based permissions
        if custom_permissions:
            miembro.can_add_tema = custom_permissions.get('can_add_tema', False)
            miembro.can_upload_file = custom_permissions.get('can_upload_file', False)
            miembro.can_sign_file = custom_permissions.get('can_sign_file', False)
            miembro.can_view_postulante_docs = custom_permissions.get('can_view_postulante_docs', False)
        else:
            # Set default permissions based on role            
            if rol == 'Presidente':
                miembro.can_add_tema = True
                miembro.can_upload_file = True
                miembro.can_sign_file = True
                miembro.can_view_postulante_docs = True
            elif rol == 'Titular':
                miembro.can_add_tema = True
                miembro.can_sign_file = True
                miembro.can_upload_file = False
                miembro.can_view_postulante_docs = True
            else:  # Suplente and others
                miembro.can_add_tema = False
                miembro.can_upload_file = False
                miembro.can_sign_file = False
                miembro.can_view_postulante_docs = False
        
        db.session.add(miembro)
        db.session.commit()
        return miembro.id  # Return the member ID instead of True
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error creating tribunal member: {str(e)}')
        flash(f'Error al crear miembro del tribunal: {str(e)}', 'danger')
        return None  # Return None instead of False

@tribunal.route('/<int:miembro_id>/editar', methods=['GET', 'POST'])
@admin_required
def editar(miembro_id):
    """Edit tribunal member assignment (rol, claustro, and permissions only)."""
    miembro = TribunalMiembro.query.get_or_404(miembro_id)
    concurso = Concurso.query.get_or_404(miembro.concurso_id)
    persona = miembro.persona
    
    if request.method == 'POST':
        try:            
            old_rol = miembro.rol
            
            # Update ONLY tribunal assignment data (not personal information)
            # Personal info (name, surname, DNI, email, phone) should be edited through admin_personas
            miembro.rol = request.form.get('rol')
            miembro.claustro = request.form.get('claustro')
            
            # Handle permission checkboxes
            miembro.can_add_tema = 'can_add_tema' in request.form
            miembro.can_upload_file = 'can_upload_file' in request.form
            miembro.can_sign_file = 'can_sign_file' in request.form
            miembro.can_view_postulante_docs = 'can_view_postulante_docs' in request.form
            
            # Update Drive folder name if role changed
            if miembro.drive_folder_id and old_rol != miembro.rol:
                new_folder_name = f"{miembro.rol}_{persona.apellido}_{persona.nombre}_{persona.dni}"
                drive_api.update_folder_name(miembro.drive_folder_id, new_folder_name)

            db.session.commit()
            flash('Asignación de tribunal actualizada exitosamente. Para modificar datos personales, use la sección Administrar Personas.', 'success')
            return redirect(url_for('tribunal.index', concurso_id=miembro.concurso_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar la asignación de tribunal: {str(e)}', 'danger')
    
    return render_template('tribunal/editar.html', miembro=miembro, persona=persona, concurso=concurso)

@tribunal.route('/<int:miembro_id>/eliminar', methods=['POST'])
@admin_required
def eliminar(miembro_id):
    """Delete a tribunal member assignment (but not the Persona record)."""
    miembro = TribunalMiembro.query.get_or_404(miembro_id)
    concurso_id = miembro.concurso_id
    persona = miembro.persona
    nombre_completo = f"{persona.nombre} {persona.apellido}"
    
    try:
        # Delete Drive folder if exists
        if miembro.drive_folder_id:
            drive_api.delete_folder(miembro.drive_folder_id)
        
        # Delete only the assignment, not the persona
        db.session.delete(miembro)
        db.session.commit()
        flash(f'{nombre_completo} ha sido eliminado exitosamente del tribunal. Su registro personal se mantiene en la base de datos.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar miembro del tribunal: {str(e)}', 'danger')
    
    return redirect(url_for('tribunal.index', concurso_id=concurso_id))

@tribunal.route('/<int:miembro_id>/recusar', methods=['GET', 'POST'])
@keycloak_login_required
def recusar(miembro_id):
    """Submit a recusation against a tribunal member."""
    miembro = TribunalMiembro.query.get_or_404(miembro_id)
    concurso = Concurso.query.get_or_404(miembro.concurso_id)
    
    if request.method == 'POST':
        try:
            # Create recusation
            recusacion = Recusacion(
                concurso_id=miembro.concurso_id,
                miembro_id=miembro_id,
                motivo=request.form.get('motivo'),
                estado='PRESENTADA'
            )
            
            db.session.add(recusacion)
            db.session.commit()
            
            flash('Recusación presentada correctamente.', 'success')
            return redirect(url_for('tribunal.index', concurso_id=miembro.concurso_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al presentar recusación: {str(e)}', 'danger')
    
    return render_template('tribunal/recusar.html', miembro=miembro, concurso=concurso)

@tribunal.route('/<int:miembro_id>/subir-documento', methods=['POST'])
@tribunal_required
def subir_documento(miembro_id):
    """Upload a document for a tribunal member."""
    miembro = TribunalMiembro.query.get_or_404(miembro_id)
    concurso = Concurso.query.get_or_404(miembro.concurso_id)
    persona = miembro.persona
    
    try:
        # Get form data
        tipo = request.form.get('tipo')
        file = request.files.get('documento')
        
        if not file:
            flash('No se seleccionó ningún archivo.', 'danger')
            return redirect(url_for('tribunal.index', concurso_id=concurso.id))
        
        if not miembro.drive_folder_id:
            flash('El miembro del tribunal no tiene una carpeta asociada.', 'danger')
            return redirect(url_for('tribunal.index', concurso_id=concurso.id))
        
        # Create filename with proper suffix
        filename = secure_filename(f"{tipo}_{persona.apellido}_{persona.nombre}_{concurso.id}.pdf")
        
        # Read file data
        file_data = file.read()
        
        # Upload to Google Drive
        file_id, web_view_link = drive_api.upload_document(
            miembro.drive_folder_id,
            filename,
            file_data
        )
        
        # Create document record
        documento = DocumentoTribunal(
            miembro_id=miembro.id,
            tipo=tipo,
            url=web_view_link
        )
        
        db.session.add(documento)
        db.session.commit()
        
        flash(f'Documento subido exitosamente. <a href="{web_view_link}" target="_blank" class="alert-link">Ver documento</a>', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al subir documento: {str(e)}', 'danger')
    
    return redirect(url_for('tribunal.index', concurso_id=concurso.id))

# Test endpoint for debugging JSON requests
@tribunal.route('/test-json', methods=['POST'])
@admin_required  
def test_json():
    """Test endpoint to debug JSON requests."""
    current_app.logger.info(f"Test JSON - Content-Type: {request.content_type}, is_json: {request.is_json}")
    current_app.logger.info(f"Request data: {request.get_data()}")
    
    try:
        if request.is_json:
            data = request.get_json()
            return jsonify({"success": True, "received": data})
        else:
            return jsonify({"success": False, "error": "Not JSON request"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@tribunal.route('/notificar-tribunal/<int:concurso_id>/<int:documento_id>', methods=['POST'])
@admin_required
def notificar_tribunal(concurso_id, documento_id):
    """Notify tribunal members with their credentials after acta constitución is generated."""
    try:
        concurso = Concurso.query.get_or_404(concurso_id)
        documento = DocumentoConcurso.query.get_or_404(documento_id)
        
        # Verify this is an Acta Constitución document
        if documento.tipo != 'ACTA_CONSTITUCION_TRIBUNAL_REGULAR':
            flash('Este documento no es un Acta de Constitución de Tribunal Regular.', 'danger')
            return redirect(url_for('concursos.ver', concurso_id=concurso_id))
            
        # Initialize Keycloak admin client
        keycloak_admin = KeycloakAdminClient()
        
        # Get only non-suplente members
        miembros = TribunalMiembro.query.filter(
            TribunalMiembro.concurso_id == concurso_id,
            TribunalMiembro.rol != 'Suplente'
        ).join(Persona).all()
        
        notificados = 0
        errores = []
        
        for miembro in miembros:
            persona = miembro.persona
            
            # Use the Drive-based notification helper function
            result = notify_tribunal_member_with_reset(persona, keycloak_admin)
            
            if result['success']:
                # Update notification status
                miembro.notificado = True
                miembro.fecha_notificacion = datetime.utcnow()
                notificados += 1
            else:
                errores.append(result['message'])
        
        db.session.commit()
        
        # Show results
        if notificados > 0:
            flash(f'Emails de configuración de contraseña enviados exitosamente a {notificados} miembros del tribunal via Drive.', 'success')
        
        if errores:
            for error in errores:
                flash(error, 'warning')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al enviar credenciales: {str(e)}', 'danger')
    
    return redirect(url_for('concursos.ver', concurso_id=concurso_id))

@tribunal.route('/concurso/<int:concurso_id>/notificar-todos', methods=['POST'])
@admin_required
def notificar_todos_miembros(concurso_id):
    """Notify all tribunal members with their credentials."""
    try:
        concurso = Concurso.query.get_or_404(concurso_id)
        miembros = TribunalMiembro.query.filter_by(concurso_id=concurso_id).join(Persona).all()
        
        # Initialize Keycloak admin client
        keycloak_admin = KeycloakAdminClient()
        
        notificados = 0
        errores = []
        
        for miembro in miembros:
            # Skip suplentes
            if miembro.rol.lower() == 'suplente':
                continue
                
            persona = miembro.persona
            
            # Use the new notification helper function
            result = notify_tribunal_member_with_reset(persona, keycloak_admin)
            
            if result['success']:
                # Update notification status
                miembro.notificado = True
                miembro.fecha_notificacion = datetime.utcnow()
                notificados += 1
            else:
                errores.append(result['message'])
        
        db.session.commit()
          # Show results
        if notificados > 0:
            flash(f'Emails de configuración de contraseña enviados exitosamente a {notificados} miembros del tribunal via Drive.', 'success')
        
        if errores:
            for error in errores:
                flash(error, 'warning')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al enviar credenciales: {str(e)}', 'danger')
    
    return redirect(url_for('tribunal.index', concurso_id=concurso_id))

@tribunal.route('/<int:miembro_id>/notificar', methods=['POST'])
@admin_required
def notificar_miembro(miembro_id):
    """Notify a single tribunal member with their credentials."""
    try:
        miembro = TribunalMiembro.query.get_or_404(miembro_id)
        persona = miembro.persona
        concurso = Concurso.query.get_or_404(miembro.concurso_id)

        if not persona.correo:
            flash(f'El miembro {persona.nombre} {persona.apellido} no tiene correo registrado.', 'warning')
            return redirect(url_for('tribunal.index', concurso_id=concurso.id))
          # Initialize Keycloak admin client
        keycloak_admin = KeycloakAdminClient()
        
        # Use the new notification helper function
        result = notify_tribunal_member_with_reset(persona, keycloak_admin)
        
        if result['success']:
            # Update notification status
            miembro.notificado = True
            miembro.fecha_notificacion = datetime.utcnow()
            db.session.commit()
            flash(result['message'], 'success')
        else:
            flash(result['message'], 'danger')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al enviar credenciales: {str(e)}', 'danger')
    
    return redirect(url_for('tribunal.index', concurso_id=concurso.id))

# Routes for tribunal member portal
@tribunal.route('/acceso')
def acceso():
    """Redirect to main Keycloak login - legacy route for backward compatibility."""
    flash('Para acceder al portal de tribunal, utilice el inicio de sesión principal del sistema.', 'info')
    return redirect(url_for('auth.login'))

@tribunal.route('/reset/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Handle password reset with token validation and Keycloak integration."""
    
    # Verify the token
    token_data = verify_reset_token(token)
    
    if not token_data['valid']:
        flash(f'Enlace de restablecimiento inválido o expirado: {token_data.get("error", "Token inválido")}', 'danger')
        return redirect(url_for('auth.login'))
    
    keycloak_user_id = token_data['user_id']
    
    if request.method == 'GET':
        # Show the reset password form
        return render_template('tribunal/reset_password.html', token=token)
    
    # POST request - process password reset
    password = request.form.get('password', '').strip()
    confirm_password = request.form.get('confirm_password', '').strip()
    
    # Validate passwords
    if not password or not confirm_password:
        flash('Por favor complete todos los campos.', 'danger')
        return render_template('tribunal/reset_password.html', token=token)
    
    if password != confirm_password:
        flash('Las contraseñas no coinciden.', 'danger')
        return render_template('tribunal/reset_password.html', token=token)
    
    if len(password) < 6:
        flash('La contraseña debe tener al menos 6 caracteres.', 'danger')
        return render_template('tribunal/reset_password.html', token=token)
    
    try:
        # Initialize Keycloak admin client
        keycloak_admin = KeycloakAdminClient()
        
        # Set the new password in Keycloak
        success = keycloak_admin.set_user_password(keycloak_user_id, password, temporary=False)
        
        if success:
            flash('Contraseña configurada exitosamente. Ya puede acceder al portal.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Error al configurar la contraseña. Intente nuevamente.', 'danger')
            return render_template('tribunal/reset_password.html', token=token)
            
    except Exception as e:
        current_app.logger.error(f"Error setting password for user {keycloak_user_id}: {e}")
        flash('Error interno al configurar la contraseña. Contacte al administrador.', 'danger')
        return render_template('tribunal/reset_password.html', token=token)

@tribunal.route('/activar', methods=['GET', 'POST'])
def activar_cuenta():
    """Allow tribunal members to activate their account using DNI and email."""
    if request.method == 'POST':
        dni = request.form.get('dni')
        correo = request.form.get('correo')
        
        # Find the persona
        persona = Persona.query.filter_by(dni=dni, correo=correo).first()
        
        if not persona:
            flash('No se encontró una persona con esos datos en el sistema.', 'danger')
            return render_template('tribunal/activar_cuenta.html')
              # Check if this persona is assigned to any tribunal
        miembro = TribunalMiembro.query.filter_by(persona_id=persona.id).first()
        if not miembro:
            flash('Esta persona no está asignada a ningún tribunal.', 'danger')
            return render_template('tribunal/activar_cuenta.html')
        
        try:
            # Initialize Keycloak admin client
            keycloak_admin = KeycloakAdminClient()
            
            # Find user in Keycloak by email
            keycloak_user = keycloak_admin.get_user_by_email(persona.correo)
            if not keycloak_user:
                flash('Usuario no encontrado en Keycloak. Contacte al administrador.', 'danger')
                return render_template('tribunal/activar_cuenta.html')
            
            # Send password reset email using Drive integration
            success = send_reset_email_internal(persona, keycloak_user['id'])
            
            if success:
                flash('Se ha enviado un enlace de activación a su correo electrónico.', 'success')
                return redirect(url_for('tribunal.acceso'))
            else:
                flash('Error al enviar el enlace de activación. Contacte al administrador.', 'danger')
            
        except Exception as e:
            flash(f'Error al procesar la solicitud: {str(e)}', 'danger')
            
    return render_template('tribunal/activar_cuenta.html')

@tribunal.route('/recuperar-password', methods=['GET', 'POST'])
def recuperar_password():
    """Allow tribunal members to request a password reset link."""
    if request.method == 'POST':
        dni = request.form.get('dni')
        correo = request.form.get('correo')
        
        # Find persona by DNI and email
        persona = Persona.query.filter_by(dni=dni, correo=correo).first()
        
        if not persona:
            flash('No se encontró una persona con esos datos en el sistema.', 'danger')
            return render_template('tribunal/recuperar_password.html')
              # Check if this persona is assigned to any tribunal
        miembro = TribunalMiembro.query.filter_by(persona_id=persona.id).first()
        if not miembro:
            flash('Esta persona no está asignada a ningún tribunal.', 'danger')
            return render_template('tribunal/recuperar_password.html')
        
        try:
            # Initialize Keycloak admin client
            keycloak_admin = KeycloakAdminClient()
            
            # Find user in Keycloak by email
            keycloak_user = keycloak_admin.get_user_by_email(persona.correo)
            if not keycloak_user:
                flash('Usuario no encontrado en Keycloak. Contacte al administrador.', 'danger')
                return render_template('tribunal/recuperar_password.html')
            
            # Send password reset email using Drive integration
            success = send_reset_email_internal(persona, keycloak_user['id'])
            
            if success:
                flash('Se ha enviado un enlace de restablecimiento de contraseña a su correo electrónico.', 'success')
                return redirect(url_for('tribunal.acceso'))
            else:
                flash('Error al enviar el enlace de restablecimiento. Contacte al administrador.', 'danger')
            
        except Exception as e:
            flash(f'Error al procesar la solicitud: {str(e)}', 'danger')
            
    return render_template('tribunal/recuperar_password.html')

@tribunal.route('/salir')
def salir_tribunal():
    """Logout for tribunal members."""
    # Make sure to clear all tribunal-related session data
    session.pop('persona_id', None)
    session.pop('tribunal_miembro_id', None)
    session.pop('tribunal_nombre', None)
    session.pop('tribunal_rol', None)  # Also clear the role from session
    flash('Sesión cerrada exitosamente', 'success')
    return redirect(url_for('tribunal.acceso'))

@tribunal.route('/portal')
@keycloak_login_required
@tribunal_required
def portal():
    """Main portal for tribunal members."""
    # Get current user info from Keycloak
    user_info = get_current_user_info()
    if not user_info:
        flash('Error al obtener información del usuario', 'danger')
        return redirect(url_for('auth.login'))
    
    # Get persona based on Keycloak user info
    persona = None
    
    # Try to find persona by email first
    email = user_info.get('email')
    if email:
        persona = Persona.query.filter_by(correo=email).first()
    
    # If not found by email, try by username (might be DNI)
    if not persona:
        username = user_info.get('preferred_username')
        if username:
            persona = Persona.query.filter_by(dni=username).first()
    
    if not persona:
        flash('No se encontró su perfil en el sistema. Contacte al administrador.', 'danger')
        return redirect(url_for('auth.login'))
    
    # Set up session for compatibility with existing tribunal system
    session['persona_id'] = persona.id
    
    # Get active tribunal memberships
    miembro = TribunalMiembro.query.filter_by(persona_id=persona.id).order_by(TribunalMiembro.id.desc()).first()
    if not miembro:
        flash('No está asignado a ningún tribunal actualmente', 'warning')
        return redirect(url_for('auth.login'))
    
    # Set tribunal session data for compatibility
    session['tribunal_miembro_id'] = miembro.id
    session['tribunal_rol'] = miembro.rol    
    # Get active tribunal memberships
    miembro = TribunalMiembro.query.filter_by(persona_id=persona.id).order_by(TribunalMiembro.id.desc()).first()
    if not miembro:
        flash('No está asignado a ningún tribunal actualmente', 'warning')
        return redirect(url_for('auth.login'))
    
    # Set tribunal session data for compatibility
    session['tribunal_miembro_id'] = miembro.id
    session['tribunal_rol'] = miembro.rol
      # Get all concursos this persona is part of and their roles
    concursos = persona.get_concursos()
    
    # Get the roles for each concurso to simplify template rendering
    concurso_roles = {}
    for concurso in concursos:
        tribunal_miembro = TribunalMiembro.query.filter_by(
            persona_id=persona.id, 
            concurso_id=concurso.id
        ).first()
        if tribunal_miembro:
            concurso_roles[concurso.id] = tribunal_miembro.rol
    
    return render_template('tribunal/portal.html', 
                          miembro=miembro,
                          persona=persona, 
                          concursos=concursos,
                          concurso_roles=concurso_roles)

@tribunal.route('/portal/concurso/<int:concurso_id>')
@keycloak_login_required
@tribunal_required
def portal_concurso(concurso_id):
    """View for a tribunal member to see details of a specific concurso."""
    # Get current user info from Keycloak
    user_info = get_current_user_info()
    if not user_info:
        flash('Error al obtener información del usuario', 'danger')
        return redirect(url_for('auth.login'))
    
    # Get persona based on Keycloak user info
    persona = None
    email = user_info.get('email')
    if email:
        persona = Persona.query.filter_by(correo=email).first()
    
    if not persona:
        username = user_info.get('preferred_username')
        if username:
            persona = Persona.query.filter_by(dni=username).first()
    
    if not persona:
        flash('No se encontró su perfil en el sistema. Contacte al administrador.', 'danger')
        return redirect(url_for('auth.login'))
    
    # Set up session for compatibility
    session['persona_id'] = persona.id
      # Get tribunal member record
    miembro = TribunalMiembro.query.filter_by(persona_id=persona.id).order_by(TribunalMiembro.id.desc()).first()
    if not miembro:
        flash('No está asignado a ningún tribunal', 'danger')
        return redirect(url_for('tribunal.portal'))
    
    session['tribunal_miembro_id'] = miembro.id
    session['tribunal_rol'] = miembro.rol
    
    # Get concurso and verify this persona is assigned to it
    concurso = Concurso.query.get_or_404(concurso_id)
    assignment = TribunalMiembro.query.filter_by(persona_id=persona.id, concurso_id=concurso_id).first()
    
    if not assignment:
        flash('No tiene permisos para ver este concurso', 'danger')
        return redirect(url_for('tribunal.portal'))
      # Get template configs for document action control
    from app.models.models import DocumentTemplateConfig, TemaSetTribunal
    template_configs = DocumentTemplateConfig.query.all()
    template_configs_dict = {config.document_type_key: config for config in template_configs}
    
    # Get other tribunal members for this concurso
    miembros = TribunalMiembro.query.filter_by(concurso_id=concurso_id).join(Persona).all()
    
    # Get postulantes
    postulantes = concurso.postulantes.all()
    
    # Get this member's personal tema proposal if it exists
    mi_propuesta = None
    if concurso.sustanciacion:
        mi_propuesta = TemaSetTribunal.query.filter_by(
            sustanciacion_id=concurso.sustanciacion.id,
            miembro_id=miembro.id
        ).first()
      # Get asignaturas from external API
    asignaturas_externas = []
    if concurso.departamento_rel:
        asignaturas_externas = get_asignaturas_from_external_api(
            departamento=concurso.departamento_rel.nombre,
            area=concurso.area,
            orientacion_concurso=concurso.orientacion
        )
    
    # Get the categoria to access tribunal instructivos
    categoria = Categoria.query.filter_by(codigo=concurso.categoria).first()
    instructivo_tribunal = None
    
    if categoria and categoria.instructivo_tribunal:
        # Build the complete instructivo text for tribunal based on dedicacion
        base_instructivo = categoria.instructivo_tribunal.get('base', '')
        dedicacion_instructivo = categoria.instructivo_tribunal.get('porDedicacion', {}).get(concurso.dedicacion, '')
        
        instructivo_tribunal = {
            'base': base_instructivo,
            'dedicacion': dedicacion_instructivo
        }
    
    # Ensure role is set properly for template checks
    if 'tribunal_rol' in session:
        miembro.rol = session['tribunal_rol']
    return render_template('tribunal/portal_concurso.html',
                          miembro=miembro,
                          persona=persona,
                          concurso=concurso,
                          miembros=miembros,
                          template_configs_dict=template_configs_dict,
                          postulantes=postulantes,
                          asignaturas_externas=asignaturas_externas,
                          mi_propuesta=mi_propuesta,
                          instructivo_tribunal=instructivo_tribunal)

@tribunal.route('/concurso/<int:concurso_id>/documentacion-postulantes')
@tribunal_login_required
def documentacion_postulantes(concurso_id):
    """View for tribunal members to see all postulantes documents for a specific concurso."""
    # Check if persona is logged in
    if 'persona_id' not in session or 'tribunal_miembro_id' not in session:
        flash('Debe iniciar sesión como miembro del tribunal para acceder.', 'warning')
        return redirect(url_for('tribunal.acceso'))
    
    # Get persona and their assigned tribunal
    persona_id = session['persona_id']
    persona = Persona.query.get_or_404(persona_id)
    miembro_id = session['tribunal_miembro_id']
    miembro = TribunalMiembro.query.get_or_404(miembro_id)
    
    # Get concurso and verify this persona is assigned to it
    concurso = Concurso.query.get_or_404(concurso_id)
    assignment = TribunalMiembro.query.filter_by(persona_id=persona_id, concurso_id=concurso_id).first()
    
    if not assignment:
        flash('No tiene permisos para ver este concurso', 'danger')
        return redirect(url_for('tribunal.portal'))
    
    # Check if the tribunal member has permission to view postulante documents
    if not miembro.can_view_postulante_docs:
        flash('No tiene permisos para ver la documentación de los postulantes', 'danger')
        return redirect(url_for('tribunal.portal_concurso', concurso_id=concurso_id))
    
    # Get postulantes with their documents
    postulantes = concurso.postulantes.all()
    
    # Organize documents by postulante
    postulantes_with_docs = {}
    for postulante in postulantes:
        documentos = postulante.documentos.all()
        if documentos:
            postulantes_with_docs[postulante] = documentos
    
    # Load roles_categorias.json to determine required documents
    required_docs = []
    try:
        import os
        import json
        from flask import current_app
        
        with open(os.path.join(current_app.root_path, '../roles_categorias.json'), 'r', encoding='utf-8') as f:
            categorias_data = json.load(f)
            
        for rol in categorias_data:
            for cat in rol['categorias']:
                if cat['codigo'] == concurso.categoria:
                    # Add base documents
                    required_docs.extend(cat['documentacionRequerida']['base'])
                    
                    # Add documents by dedicacion if available
                    if 'porDedicacion' in cat['documentacionRequerida'] and concurso.dedicacion in cat['documentacionRequerida']['porDedicacion']:
                        required_docs.extend(cat['documentacionRequerida']['porDedicacion'][concurso.dedicacion])
                    break
    except Exception as e:
        print(f"Error loading required documents: {e}")
    
    return render_template('tribunal/documentacion_postulantes.html',
                          concurso=concurso,
                          miembro=miembro,
                          persona=persona,
                          postulantes=postulantes,
                          postulantes_with_docs=postulantes_with_docs,
                          required_docs=required_docs)

@tribunal.route('/concurso/<int:concurso_id>/postulante/<int:postulante_id>/documento/<int:documento_id>/view', methods=['GET'])
@tribunal_login_required
def ver_documento_postulante(concurso_id, postulante_id, documento_id):
    """Display postulante document content in a viewer."""
    try:
        from app.models.models import DocumentoPostulante
        import base64
        import io
        
        # Get concurso, postulante, documento and current tribunal member
        concurso = Concurso.query.get_or_404(concurso_id)
        postulante = Postulante.query.filter_by(id=postulante_id, concurso_id=concurso_id).first_or_404()
        documento = DocumentoPostulante.query.get_or_404(documento_id)
        
        persona_id = session['persona_id']
        miembro = TribunalMiembro.query.filter_by(
            persona_id=persona_id,
            concurso_id=concurso_id
        ).first_or_404()
        
        # Verify the document belongs to this postulante
        if documento.postulante_id != postulante_id:
            flash('El documento no pertenece a este postulante', 'danger')
            return redirect(url_for('tribunal.documentacion_postulantes', concurso_id=concurso_id))
        
        # Verify tribunal member has permission to view documents
        if not miembro.can_view_postulante_docs:
            flash('No tiene permisos para ver la documentación de los postulantes', 'danger')
            return redirect(url_for('tribunal.portal_concurso', concurso_id=concurso_id))
        
        # Extract file ID from Google Drive URL
        file_id = documento.url.split('/')[-2]  # Assuming URL format ends with /file_id/view
        
        # Get file content from Drive
        file_content_response = drive_api.get_file_content(file_id)
        if not file_content_response.get('fileData'):
            flash('No se pudo obtener el contenido del archivo', 'danger')
            return redirect(url_for('tribunal.documentacion_postulantes', concurso_id=concurso_id))
        
        # Decode base64 content
        pdf_content = base64.b64decode(file_content_response['fileData'])
        
        # Return the PDF content with proper headers
        return send_file(
            io.BytesIO(pdf_content),
            mimetype='application/pdf'
        )
        
    except Exception as e:
        flash(f'Error al obtener el documento: {str(e)}', 'danger')
        return redirect(url_for('tribunal.documentacion_postulantes', concurso_id=concurso_id))

@tribunal.route('/<int:concurso_id>/documento/<int:documento_id>/subir-firmado', methods=['POST'])
@tribunal_login_required
def subir_documento_presidente(concurso_id, documento_id):
    """Handle signed document upload from tribunal members with upload permission"""
    try:
        concurso = Concurso.query.get_or_404(concurso_id)
        documento = DocumentoConcurso.query.get_or_404(documento_id)
        persona_id = session['persona_id']
        miembro = TribunalMiembro.query.filter_by(
            persona_id=persona_id,
            concurso_id=concurso_id
        ).first_or_404()
          # Verify the document belongs to this concurso
        if documento.concurso_id != concurso_id:
            flash('El documento no pertenece a este concurso.', 'danger')
            return redirect(url_for('tribunal.portal_concurso', concurso_id=concurso_id))
        
        # Get template configuration
        from app.models.models import DocumentTemplateConfig
        template_config = DocumentTemplateConfig.query.filter_by(document_type_key=documento.tipo).first()
        
        # Check if tribunal can upload signed documents for this document type
        if not template_config or not template_config.tribunal_can_upload_signed:
            flash('No tiene permisos para subir documentos firmados de este tipo.', 'danger')
            return redirect(url_for('tribunal.portal_concurso', concurso_id=concurso_id))
        
        # Only allow members with upload permission to upload signed documents
        if not miembro.can_upload_file:
            flash('No tiene permisos para subir documentos firmados.', 'danger')
            return redirect(url_for('tribunal.portal_concurso', concurso_id=concurso_id))
        
        # Check if document is already signed
        if documento.estado == 'FIRMADO':
            flash('Este documento ya ha sido firmado.', 'danger')
            return redirect(url_for('tribunal.portal_concurso', concurso_id=concurso_id))
            
        # Get the file from the request
        file = request.files.get('documento')
        if not file:
            flash('No se seleccionó ningún archivo.', 'danger')
            return redirect(url_for('tribunal.portal_concurso', concurso_id=concurso_id))
            
        # Verify it's a PDF
        if not file.filename.lower().endswith('.pdf'):
            flash('Solo se permiten archivos PDF.', 'danger')
            return redirect(url_for('tribunal.portal_concurso', concurso_id=concurso_id))
            
        # Create filename based on document type and concurso id
        base_filename = documento.tipo.lower().replace('_', ' ')
        filename = secure_filename(f"{base_filename}_concurso_{concurso.id}_firmado.pdf")
        
        # Upload to documentos_firmados folder
        file_data = file.read()
        file_id, web_view_link = drive_api.upload_document(
            concurso.documentos_firmados_folder_id,
            filename,
            file_data
        )
        
        # Update document status and store the file_id 
        documento.estado = 'PENDIENTE DE FIRMA'
        documento.file_id = file_id  # Store the file_id for the uploaded version
        documento.url = web_view_link
        documento.firma_count = 0  # Reset firma count since this is a new document
          # Add entry to history
        historial = HistorialEstado(
            concurso=concurso,
            estado="DOCUMENTO_PENDIENTE_FIRMA",
            observaciones=f"Documento {documento.tipo} subido por {miembro.persona.nombre} {miembro.persona.apellido}, pendiente de firma"
        )
        db.session.add(historial)
        db.session.commit()
        
        flash(f'Documento subido exitosamente. <a href="{web_view_link}" target="_blank" class="alert-link">Ver documento</a>. El documento está pendiente de firma.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al subir el documento firmado: {str(e)}', 'danger')
    
    return redirect(url_for('tribunal.portal_concurso', concurso_id=concurso_id))

@tribunal.route('/<int:concurso_id>/documento/<int:documento_id>/firmar', methods=['POST'])
@tribunal_login_required
def firmar_documento(concurso_id, documento_id):
    """Handle document signing by tribunal members."""
    try:
        # Get concurso, documento and current tribunal member
        concurso = Concurso.query.get_or_404(concurso_id)
        documento = DocumentoConcurso.query.get_or_404(documento_id)
        persona_id = session['persona_id']
        miembro = TribunalMiembro.query.filter_by(
            persona_id=persona_id,
            concurso_id=concurso_id
        ).first_or_404()
        
        # Verify the document belongs to this concurso
        if documento.concurso_id != concurso_id:
            flash('El documento no pertenece a este concurso.', 'danger')
            return redirect(url_for('tribunal.portal_concurso', concurso_id=concurso_id))
          # Check if member already signed
        if documento.ya_firmado_por(miembro.id):
            flash('Ya ha firmado este documento.', 'danger')
            return redirect(url_for('tribunal.portal_concurso', concurso_id=concurso_id))
            
        # Get template configuration
        from app.models.models import DocumentTemplateConfig
        template_config = DocumentTemplateConfig.query.filter_by(document_type_key=documento.tipo).first()
        
        # Check if tribunal can sign this document type
        if not template_config or not template_config.tribunal_can_sign:
            flash('No tiene permisos para firmar este tipo de documento.', 'danger')
            return redirect(url_for('tribunal.portal_concurso', concurso_id=concurso_id))
            
        # Check if document is in the right state and has a file_id
        if documento.estado != 'PENDIENTE DE FIRMA' or not documento.file_id:
            flash('El documento no está en estado correcto para ser firmado.', 'danger')
            return redirect(url_for('tribunal.portal_concurso', concurso_id=concurso_id))
        
        # Get the file content from Drive
        file_content_response = drive_api.get_file_content(documento.file_id)
        if not file_content_response.get('fileData'):
            raise Exception("No se pudo obtener el contenido del archivo")
        
        # Get the binary content from base64
        import base64
        pdf_content = base64.b64decode(file_content_response['fileData'])
        
        # Add the signature using the PDF utility
        pdf_with_stamp = add_signature_stamp(
            pdf_content,
            miembro.persona.apellido,
            miembro.persona.nombre,
            miembro.persona.dni,
            documento.firma_count
        )
        
        if not pdf_with_stamp:
            raise Exception("Error al agregar la firma al PDF")
        
        # Convert back to base64 for upload
        pdf_base64 = base64.b64encode(pdf_with_stamp).decode('utf-8')
        
        # Upload back to Drive, replacing the original
        new_file_id, web_view_link = drive_api.overwrite_file(
            documento.file_id,
            pdf_base64
        )
        
        if not new_file_id:
            raise Exception("Error al guardar el documento firmado")
        
        # Update document with new file ID and URL if changed
        if new_file_id != documento.file_id:
            documento.file_id = new_file_id
        if web_view_link:
            documento.url = web_view_link
        
        # Increment signature count
        documento.firma_count += 1
        
        # Add firma record
        firma = FirmaDocumento(
            documento_id=documento.id,
            miembro_id=miembro.id
        )  # fecha_firma will be set automatically by the default value
        db.session.add(firma)
        
        # If document is not already marked as FIRMADO, update status once all tribunal members have signed
        if documento.estado != 'FIRMADO':
            tribunal_titulares = TribunalMiembro.query.filter(
                TribunalMiembro.concurso_id == concurso_id,
                TribunalMiembro.rol != 'Suplente'
            ).count()
            
            if documento.firma_count >= tribunal_titulares:
                documento.estado = 'FIRMADO'
                
                # Add entry to history
                historial = HistorialEstado(
                    concurso=concurso,
                    estado="DOCUMENTO_FIRMADO",
                    observaciones=f"Documento {documento.tipo} completamente firmado"
                )
                db.session.add(historial)
        
        db.session.commit()
        flash('Documento firmado exitosamente.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al firmar el documento: {str(e)}', 'danger')
        import traceback
        print(traceback.format_exc())
    
    return redirect(url_for('tribunal.portal_concurso', concurso_id=concurso_id))

@tribunal.route('/<int:concurso_id>/documento/<int:documento_id>/subir', methods=['POST'], endpoint='subir_acta_firmada')
def subir_acta_firmada(concurso_id, documento_id):
    """Handle tribunal member uploading a signed document. Redirects to subir_documento_presidente."""
    # Redirect to the standard endpoint for consistency
    return redirect(url_for('tribunal.subir_documento_presidente', concurso_id=concurso_id, documento_id=documento_id))

@tribunal.route('/<int:concurso_id>/documento/<int:documento_id>/view', methods=['GET'])
@tribunal_login_required
def ver_documento(concurso_id, documento_id):
    """Display document content in a viewer."""
    try:        # Get concurso, documento and current tribunal member
        concurso = Concurso.query.get_or_404(concurso_id)
        documento = DocumentoConcurso.query.get_or_404(documento_id)
        persona_id = session['persona_id']
        miembro = TribunalMiembro.query.filter_by(
            persona_id=persona_id,
            concurso_id=concurso_id
        ).first_or_404()
        
        # Verify the document belongs to this concurso
        if documento.concurso_id != concurso_id:
            flash('El documento no pertenece a este concurso.', 'danger')
            return redirect(url_for('tribunal.portal_concurso', concurso_id=concurso_id))
            
        # Get correct file_id based on document state
        if documento.estado in ['PENDIENTE_DE_FIRMA', 'FIRMADO'] and documento.file_id:
            file_id = documento.file_id  # Use the signed/uploaded version
        else:
            file_id = documento.borrador_file_id  # Use the draft version
            
        # Get file content from Drive
        file_content_response = drive_api.get_file_content(file_id)
        if not file_content_response.get('fileData'):
            raise Exception("No se pudo obtener el contenido del archivo")
            
        # Decode base64 content
        import base64
        pdf_content = base64.b64decode(file_content_response['fileData'])
        
        # Return the PDF content with proper headers
        return send_file(
            io.BytesIO(pdf_content),
            mimetype='application/pdf'
        )
        
    except Exception as e:
        flash(f'Error al obtener el documento: {str(e)}', 'danger')
        return redirect(url_for('tribunal.portal_concurso', concurso_id=concurso_id))

@tribunal.route('/<int:concurso_id>/cargar-sorteos', methods=['GET', 'POST'])
@tribunal_login_required
def cargar_sorteos(concurso_id):
    """Load sorteo temas for a concurso. Only accessible by members with can_add_tema permission.
    This route now handles both saving and saving & closing topics for individual tribunal members."""
    concurso = Concurso.query.get_or_404(concurso_id)
    persona_id = session['persona_id']
    miembro = TribunalMiembro.query.filter_by(
        persona_id=persona_id,
        concurso_id=concurso_id
    ).first_or_404()
    persona = Persona.query.get_or_404(persona_id)
    
    # Ensure role is set from session for proper template checks
    if 'tribunal_rol' in session:
        miembro.rol = session['tribunal_rol']
    
    # Make sure sustanciacion record exists
    sustanciacion = concurso.sustanciacion
    if not sustanciacion:
        sustanciacion = Sustanciacion(concurso_id=concurso_id)
        concurso.sustanciacion = sustanciacion
        db.session.add(sustanciacion)
        db.session.commit()
    
    # Check if global topics are already closed
    if concurso.sustanciacion and concurso.sustanciacion.temas_cerrados:
        if request.method == 'POST':
            flash('La carga de temas ya ha sido finalizada por un administrador. No se pueden realizar modificaciones.', 'warning')
            return redirect(url_for('tribunal.portal_concurso', concurso_id=concurso_id))
    
    # Get or create individual tema proposal for this miembro
    from app.models.models import TemaSetTribunal
    tema_propuesta = TemaSetTribunal.query.filter_by(
        sustanciacion_id=sustanciacion.id,
        miembro_id=miembro.id
    ).first()
    
    if tema_propuesta and tema_propuesta.propuesta_cerrada:
        if request.method == 'POST':
            flash('Ya ha cerrado sus temas de sorteo. Contacte al administrador si necesita realizar cambios.', 'warning')
            return redirect(url_for('tribunal.portal_concurso', concurso_id=concurso_id))
    
    if request.method == 'POST':
        if not miembro.can_add_tema:
            flash('No tiene permisos para cargar los temas de sorteo.', 'danger')
            return redirect(url_for('tribunal.portal_concurso', concurso_id=concurso_id))
        
        action = request.form.get('action', 'save')
        temas = request.form.get('temas_exposicion', '')
        
        try:
            # Create tema_propuesta if it doesn't exist
            if not tema_propuesta:
                tema_propuesta = TemaSetTribunal(
                    sustanciacion_id=sustanciacion.id,
                    miembro_id=miembro.id,
                    temas_propuestos=temas,
                    propuesta_cerrada=False
                )
                db.session.add(tema_propuesta)
            else:
                tema_propuesta.temas_propuestos = temas
                tema_propuesta.fecha_propuesta = datetime.utcnow()  # Update timestamp
            
            # Process based on action
            if action == 'save_and_close':
                # Validate that we have exactly 3 topics
                temas_lista = [t.strip() for t in temas.split('|') if t.strip()]
                
                if len(temas_lista) != 3:
                    flash('Para cerrar los temas, deben ser exactamente 3.', 'warning')
                    # Return to the form with current topics
                    return render_template(
                        'tribunal/cargar_sorteos.html', 
                        concurso=concurso, 
                        miembro=miembro, 
                        persona=persona,
                        current_temas_str=temas,
                        tema_propuesta=tema_propuesta
                    )
                
                # Mark as closed for this tribunal member
                tema_propuesta.propuesta_cerrada = True
                
                # Add entry to history
                historial = HistorialEstado(
                    concurso=concurso,
                    estado="TEMAS_SORTEO_MIEMBRO_CERRADOS",
                    observaciones=f"Propuesta de temas cerrada por {persona.nombre} {persona.apellido} ({miembro.rol})"
                )
                db.session.add(historial)
                db.session.commit()
                
                flash('Sus temas de sorteo han sido guardados y cerrados. Ya no se pueden realizar modificaciones.', 'success')
                
            else:  # default action: save
                # Get previous state for history logging
                old_temas = tema_propuesta.temas_propuestos if tema_propuesta else ''
                
                # Add appropriate history entry
                estado = "TEMAS_SORTEO_MIEMBRO_GUARDADOS"
                if not temas.strip() and old_temas:
                    estado = "TEMAS_SORTEO_MIEMBRO_BORRADOS"
                
                historial = HistorialEstado(
                    concurso=concurso,
                    estado=estado,
                    observaciones=f"Propuesta de temas actualizada por {persona.nombre} {persona.apellido} ({miembro.rol})"
                )
                db.session.add(historial)
                db.session.commit()
                
                flash('Sus temas de sorteo han sido guardados exitosamente.', 'success')
            
            return redirect(url_for('tribunal.portal_concurso', concurso_id=concurso_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al guardar los temas: {str(e)}', 'danger')
            return render_template(
                'tribunal/cargar_sorteos.html', 
                concurso=concurso, 
                miembro=miembro, 
                persona=persona,
                current_temas_str=temas,
                tema_propuesta=tema_propuesta
            )
    
    # For GET requests, get existing topics for this member if available
    current_temas_str = ''
    if tema_propuesta:
        current_temas_str = tema_propuesta.temas_propuestos
    return render_template(
        'tribunal/cargar_sorteos.html', 
        concurso=concurso, 
        miembro=miembro,
        persona=persona,
        current_temas_str=current_temas_str,
        tema_propuesta=tema_propuesta
    )

@tribunal.route('/<int:concurso_id>/reset-temas', methods=['POST'])
@admin_required
def reset_temas(concurso_id):
    """Reset sorteo temas for a concurso. Only accessible by admin."""
    concurso = Concurso.query.get_or_404(concurso_id)
    
   
    
    if not concurso.sustanciacion:
        flash('El concurso no tiene información de sustanciación.', 'danger')
        return redirect(url_for('tribunal.portal_concurso', concurso_id=concurso_id))
    
    try:
        # Clear temas_exposicion
        concurso.sustanciacion.temas_exposicion = None
        
        # Always reset the temas_cerrados flag to allow tribunal to restart
        concurso.sustanciacion.temas_cerrados = False
        
        # Add entry to history
        historial = HistorialEstado(
            concurso=concurso,
            estado="TEMAS_SORTEO_REINICIADOS",
            observaciones=f"Temas de sorteo eliminados y proceso reabierto para el tribunal por administrador {get_current_username()}"
        )
        db.session.add(historial)
        db.session.commit()
        
        flash('Temas de sorteo eliminados exitosamente. El tribunal podrá cargar nuevos temas.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar los temas: {str(e)}', 'danger')
    

    
    return redirect(url_for('tribunal.portal_concurso', concurso_id=concurso_id))

@tribunal.route('/<int:concurso_id>/reset-temas-miembro/<int:miembro_id>', methods=['POST'])
@admin_required
def reset_temas_miembro(concurso_id, miembro_id):
    """Unlock sorteo temas for a specific tribunal member to allow editing. Only accessible by admin."""
    concurso = Concurso.query.get_or_404(concurso_id)
    miembro_target = TribunalMiembro.query.get_or_404(miembro_id)
    
    # Verify the member belongs to this concurso
    if miembro_target.concurso_id != concurso_id:
        flash('El miembro no pertenece a este concurso.', 'danger')
        return redirect(url_for('concursos.ver', concurso_id=concurso_id))
    
    if not concurso.sustanciacion:
        flash('El concurso no tiene información de sustanciación.', 'danger')
        return redirect(url_for('concursos.ver', concurso_id=concurso_id))
    try:
        # Find the TemaSetTribunal record for this member
        from app.models.models import TemaSetTribunal
        tema_propuesta = TemaSetTribunal.query.filter_by(
            sustanciacion_id=concurso.sustanciacion.id,
            miembro_id=miembro_id
        ).first()
        
        if not tema_propuesta:
            flash(f'El miembro {miembro_target.persona.nombre} {miembro_target.persona.apellido} no tiene temas propuestos.', 'warning')
            return redirect(url_for('concursos.ver', concurso_id=concurso_id))
        
        # Check if topics are already consolidated
        temas_were_consolidated = concurso.sustanciacion.temas_cerrados
        tema_was_drawn = concurso.sustanciacion.tema_sorteado is not None
        
        # Instead of deleting, unlock the proposal for editing
        tema_propuesta.propuesta_cerrada = False
        
        # If topics were consolidated, we need to un-consolidate them
        if temas_were_consolidated:
            concurso.sustanciacion.temas_exposicion = None
            concurso.sustanciacion.temas_cerrados = False
            
            # If a topic was drawn, it's no longer valid
            if tema_was_drawn:
                concurso.sustanciacion.tema_sorteado = None
            
            # Add entry to history with details about un-consolidation
            estado = "TEMAS_SORTEO_MIEMBRO_Y_CONSOLIDACION_DESBLOQUEADOS"
            observaciones = f"Propuesta de temas del miembro {miembro_target.persona.nombre} {miembro_target.persona.apellido} desbloqueada por administrador {get_current_username()}. La consolidación de temas y el tema sorteado (si existía) han sido reiniciados. El miembro puede editar sus temas propuestos. Se requerirá nueva consolidación."
            flash_message = f'Propuesta de temas del miembro {miembro_target.persona.nombre} {miembro_target.persona.apellido} desbloqueada exitosamente. La consolidación general y el tema sorteado (si existía) han sido reiniciados. El miembro puede editar sus temas propuestos. Por favor, vuelva a consolidar los temas una vez que el miembro haya actualizado y enviado su propuesta.'
        else:
            # Standard unlock without un-consolidation
            estado = "TEMAS_SORTEO_MIEMBRO_DESBLOQUEADOS"
            observaciones = f"Propuesta de temas del miembro {miembro_target.persona.nombre} {miembro_target.persona.apellido} desbloqueada por administrador {get_current_username()}"
            flash_message = f'Propuesta de temas del miembro {miembro_target.persona.nombre} {miembro_target.persona.apellido} desbloqueada exitosamente.'
        
        # Add entry to history
        historial = HistorialEstado(
            concurso=concurso,
            estado=estado,
            observaciones=observaciones
        )
        db.session.add(historial)
        db.session.commit()
        
        flash(flash_message, 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al desbloquear la propuesta de temas: {str(e)}', 'danger')
    
    return redirect(url_for('concursos.ver', concurso_id=concurso_id, _anchor='sustanciacion'))

@tribunal.route('/api/buscar-persona', methods=['GET'])
@admin_required
def buscar_persona():
    """API endpoint to search for a persona by DNI"""
    dni = request.args.get('dni')
    
    if not dni:
        return jsonify({'error': 'DNI no proporcionado', 'encontrado': False}), 400
    
    # Find the persona by DNI
    persona = Persona.query.filter_by(dni=dni).first()
    
    if not persona:
        return jsonify({'mensaje': 'Persona no encontrada', 'encontrado': False}), 404
      # Return persona data
    return jsonify({
        'encontrado': True,
        'nombre': persona.nombre,
        'apellido': persona.apellido,
        'dni': persona.dni,
        'correo': persona.correo or '',
        'telefono': persona.telefono or '',
        'display_name': f"{persona.apellido}, {persona.nombre} - DNI: {persona.dni}" + 
                       (f" - {persona.correo}" if persona.correo else "")
    })

@tribunal.route('/api/buscar-personas', methods=['GET'])
@admin_required
def buscar_personas():
    """API endpoint to search for personas with flexible criteria"""
    query = request.args.get('q', '').strip()
    concurso_id = request.args.get('concurso_id')
    limit = min(int(request.args.get('limit', 50)), 100)  # Max 100 results
    
    if not query or len(query) < 2:
        return jsonify({'personas': []})
    
    # Base query for personas
    personas_query = Persona.query
      # If concurso_id is provided, exclude already assigned personas
    if concurso_id:
        assigned_persona_ids = db.session.query(TribunalMiembro.persona_id).filter_by(concurso_id=concurso_id).subquery()
        personas_query = personas_query.filter(~Persona.id.in_(db.select(assigned_persona_ids)))
    
    # Search by name, surname, DNI, or email
    search_filter = db.or_(
        Persona.nombre.ilike(f'%{query}%'),
        Persona.apellido.ilike(f'%{query}%'),
        Persona.dni.ilike(f'%{query}%'),
        Persona.correo.ilike(f'%{query}%')
    )
    
    personas = personas_query.filter(search_filter)\
                            .order_by(Persona.apellido, Persona.nombre)\
                            .limit(limit)\
                            .all()
    
    # Format results
    results = []
    for persona in personas:
        results.append({
            'id': persona.id,
            'nombre': persona.nombre,
            'apellido': persona.apellido,
            'dni': persona.dni,
            'correo': persona.correo or '',
            'telefono': persona.telefono or '',
            'display_name': f"{persona.apellido}, {persona.nombre} - DNI: {persona.dni}" + 
                           (f" - {persona.correo}" if persona.correo else "")
        })
    
    return jsonify({'personas': results})

@tribunal.route('/concurso/<int:concurso_id>/postulante/<int:postulante_id>/download-docs', methods=['GET'])
@tribunal_login_required
def download_postulante_docs(concurso_id, postulante_id):
    """Download merged PDF with all documentation for a specific postulante."""
    # Check if persona is logged in
    if 'persona_id' not in session or 'tribunal_miembro_id' not in session:
        flash('Debe iniciar sesión como miembro del tribunal para acceder.', 'warning')
        return redirect(url_for('tribunal.acceso'))
    
    # Get persona and their assigned tribunal
    persona_id = session['persona_id']
    persona = Persona.query.get_or_404(persona_id)
    miembro_id = session['tribunal_miembro_id']
    miembro = TribunalMiembro.query.get_or_404(miembro_id)
    
    # Get concurso and verify this persona is assigned to it
    concurso = Concurso.query.get_or_404(concurso_id)
    assignment = TribunalMiembro.query.filter_by(persona_id=persona_id, concurso_id=concurso_id).first()
    
    if not assignment:
        flash('No tiene permisos para ver este concurso', 'danger')
        return redirect(url_for('tribunal.portal'))
    
    # Check if the tribunal member has permission to view postulante documents
    if not miembro.can_view_postulante_docs:
        flash('No tiene permisos para ver la documentación de los postulantes', 'danger')
        return redirect(url_for('tribunal.portal_concurso', concurso_id=concurso_id))
    
    # Get postulante
    postulante = Postulante.query.get_or_404(postulante_id)
    
    # Verify postulante belongs to this concurso
    if postulante.concurso_id != concurso_id:
        flash('El postulante no pertenece a este concurso', 'danger')
        return redirect(url_for('tribunal.documentacion_postulantes', concurso_id=concurso_id))
      # Get all documents for this postulante (excluding DNI)
    documentos = DocumentoPostulante.query.filter(
        DocumentoPostulante.postulante_id == postulante_id,
        DocumentoPostulante.tipo != 'DNI'  # Exclude DNI documents
    ).all()
    
    if not documentos:
        flash('No hay documentos disponibles para descargar para este postulante', 'warning')
        return redirect(url_for('tribunal.documentacion_postulantes', concurso_id=concurso_id))
    
    try:
        # Generate merged PDF
        merged_pdf_bytes = merge_postulante_documents(concurso, postulante, documentos, drive_api)
        
        if not merged_pdf_bytes:
            flash('Error al generar el archivo PDF', 'danger')
            return redirect(url_for('tribunal.documentacion_postulantes', concurso_id=concurso_id))
        
        # Create filename
        filename = f"documentacion_{postulante.apellido}_{postulante.nombre}_{postulante.dni}_{concurso.id}.pdf"
        filename = secure_filename(filename)
        
        # Return file as download
        return send_file(
            io.BytesIO(merged_pdf_bytes),
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        current_app.logger.error(f"Error generating merged PDF for postulante {postulante_id}: {str(e)}")
        flash('Error al generar el archivo PDF', 'danger')

# Unified API routes for the new tribunal management system
@tribunal.route('/concurso/<int:concurso_id>/tribunal/add', methods=['POST'])
@admin_required
def add_single_member(concurso_id):
    """Add a single member to the tribunal via JSON API."""
    try:
        concurso = Concurso.query.get_or_404(concurso_id)
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'No se recibieron datos'
            }), 400
        
        persona_id = data.get('persona_id')
        if not persona_id:
            return jsonify({
                'success': False,
                'message': 'ID de persona requerido'
            }), 400
        
        persona = Persona.query.get_or_404(persona_id)
        
        # Check if already exists
        existing = TribunalMiembro.query.filter_by(
            concurso_id=concurso_id,
            persona_id=persona_id
        ).first()
        
        if existing:
            return jsonify({
                'success': False,
                'message': f'{persona.nombre} {persona.apellido} ya está en el tribunal'
            }), 400
        
        # Create member with permissions
        permissions = {
            'can_add_tema': data.get('can_add_tema', False),
            'can_upload_file': data.get('can_upload_file', False),
            'can_sign_file': data.get('can_sign_file', False),
            'can_view_postulante_docs': data.get('can_view_postulante_docs', False)
        }
        
        miembro_id = create_tribunal_member(
            concurso=concurso,
            persona=persona,
            rol=data.get('rol', 'Titular'),
            claustro=data.get('claustro', 'Docente'),
            custom_permissions=permissions
        )
        
        if miembro_id:
            miembro = TribunalMiembro.query.get(miembro_id)
            return jsonify({
                'success': True,
                'message': f'{persona.nombre} {persona.apellido} agregado al tribunal',
                'miembro': {
                    'id': miembro.id,
                    'rol': miembro.rol,
                    'claustro': miembro.claustro,
                    'can_add_tema': miembro.can_add_tema,
                    'can_upload_file': miembro.can_upload_file,
                    'can_sign_file': miembro.can_sign_file,
                    'can_view_postulante_docs': miembro.can_view_postulante_docs
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Error al crear el miembro del tribunal'
            }), 500
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error adding tribunal member: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'Error interno: {str(e)}'
        }), 500

@tribunal.route('/concurso/<int:concurso_id>/tribunal/edit/<int:miembro_id>', methods=['PUT'])
@admin_required
def edit_member_api(concurso_id, miembro_id):
    """Edit a tribunal member via JSON API."""

    try:
        miembro = TribunalMiembro.query.get_or_404(miembro_id)
        
        if miembro.concurso_id != concurso_id:
            return jsonify({
                'success': False,
                'message': 'Miembro no pertenece a este concurso'
            }), 400
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': 'No se recibieron datos'
            }), 400
        
        # Store old values for Drive folder update
        old_rol = miembro.rol
        persona = miembro.persona
        
        # Update member data
        miembro.rol = data.get('rol', miembro.rol)
        miembro.claustro = data.get('claustro', miembro.claustro)
        miembro.can_add_tema = data.get('can_add_tema', False)
        miembro.can_upload_file = data.get('can_upload_file', False)
        miembro.can_sign_file = data.get('can_sign_file', False)
        miembro.can_view_postulante_docs = data.get('can_view_postulante_docs', False)
        
        # Update Drive folder name if role changed
        if miembro.drive_folder_id and old_rol != miembro.rol:
            try:
                new_folder_name = f"{miembro.rol}_{persona.apellido}_{persona.nombre}_{persona.dni}"
                drive_api.update_folder_name(miembro.drive_folder_id, new_folder_name)
            except Exception as drive_error:
                current_app.logger.warning(f'Error updating Drive folder name: {drive_error}')
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Miembro actualizado correctamente',
            'miembro': {
                'id': miembro.id,
                'rol': miembro.rol,
                'claustro': miembro.claustro,
                'can_add_tema': miembro.can_add_tema,
                'can_upload_file': miembro.can_upload_file,
                'can_sign_file': miembro.can_sign_file,
                'can_view_postulante_docs': miembro.can_view_postulante_docs
            }
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error editing tribunal member: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'Error interno: {str(e)}'
        }), 500

@tribunal.route('/concurso/<int:concurso_id>/tribunal/delete/<int:miembro_id>', methods=['DELETE'])
@admin_required
def delete_member_api(concurso_id, miembro_id):
    """Delete a tribunal member via JSON API."""
    try:
        miembro = TribunalMiembro.query.get_or_404(miembro_id)
        
        if miembro.concurso_id != concurso_id:
            return jsonify({
                'success': False,
                'message': 'Miembro no pertenece a este concurso'
            }), 400
        
        persona = miembro.persona
        
        # Delete Drive folder if exists
        if miembro.drive_folder_id:
            try:
                drive_api.delete_folder(miembro.drive_folder_id)
            except Exception as drive_error:
                current_app.logger.warning(f'Error deleting Drive folder: {drive_error}')
        
        db.session.delete(miembro)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{persona.nombre} {persona.apellido} eliminado del tribunal'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error deleting tribunal member: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'Error interno: {str(e)}'
        }), 500

def send_simple_reset_fallback(persona: Persona, keycloak_user_id: str) -> bool:
    """Simple fallback method that generates token and logs it without Keycloak API calls."""
    try:
        # Generate reset token
        reset_token = generate_reset_token(keycloak_user_id)
        
        # Build reset URL pointing to our app
        reset_url = url_for('tribunal.reset_password', token=reset_token, _external=True)
        
        # Log the information for manual testing
        current_app.logger.info(f"Password reset fallback for {persona.correo}")
        current_app.logger.info(f"Reset URL: {reset_url}")
        current_app.logger.info(f"Token: {reset_token}")
        
        # In debug mode, show the link in the UI
        if current_app.debug:
            flash(f'Password reset link for {persona.nombre} {persona.apellido}: <a href="{reset_url}" target="_blank">Reset Password</a>', 'info')
        
        # You can implement actual email sending here without Keycloak
        # For example, using Flask-Mail or any other email service
        
        return True
        
    except Exception as e:
        current_app.logger.error(f"Error in fallback reset email: {e}")
        return False
