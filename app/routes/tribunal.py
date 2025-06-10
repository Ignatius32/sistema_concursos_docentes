from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session, send_file, current_app
from flask_login import login_required, current_user
from app.models.models import db, Concurso, TribunalMiembro, Recusacion, DocumentoTribunal, HistorialEstado, DocumentoConcurso, FirmaDocumento, Persona, Postulante, Sustanciacion, Categoria, DocumentoPostulante
from app.integrations.google_drive import GoogleDriveAPI
from app.helpers.pdf_utils import add_signature_stamp, verify_signed_pdf, merge_postulante_documents
from app.helpers.api_services import get_asignaturas_from_external_api
from datetime import datetime
from werkzeug.utils import secure_filename
from functools import wraps
import string
import random
import os
import json
import base64
import io
import random
import string
import string
import random
import io

tribunal = Blueprint('tribunal', __name__, url_prefix='/tribunal')
drive_api = GoogleDriveAPI()

# Helper function to generate a random password
def generate_random_password(length=10):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for i in range(length))

# Helper function to generate a username from name and last name
def generate_username(nombre, apellido, dni=None):
    # Remove special characters and spaces
    nombre = ''.join(e for e in nombre if e.isalnum()).lower()
    apellido = ''.join(e for e in apellido if e.isalnum()).lower()
    
    # Create base username
    base_username = f"{nombre[0]}{apellido}"[:15]  # First letter of name + last name, max 15 chars
    
    # Check if username exists in Persona table instead of TribunalMiembro
    existing = Persona.query.filter(Persona.username.like(f"{base_username}%")).all()
    
    if not existing:
        return base_username
    
    # If username exists, add last digits of DNI or a random number
    if dni and len(dni) >= 3:
        return f"{base_username}{dni[-3:]}"
    else:
        return f"{base_username}{random.randint(100, 999)}"

def tribunal_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'persona_id' not in session:
            flash('Debe iniciar sesión como miembro del tribunal para acceder.', 'warning')
            return redirect(url_for('tribunal.acceso'))
        return f(*args, **kwargs)
    return decorated_function

@tribunal.route('/concurso/<int:concurso_id>')
@login_required
def index(concurso_id):
    """Display tribunal members for a specific concurso."""
    concurso = Concurso.query.get_or_404(concurso_id)
    miembros = TribunalMiembro.query.filter_by(concurso_id=concurso_id).join(Persona).all()
    return render_template('tribunal/index.html', concurso=concurso, miembros=miembros)

@tribunal.route('/concurso/<int:concurso_id>/agregar', methods=['GET', 'POST'])
@login_required
def agregar(concurso_id):
    """Add a new member to the tribunal of a concurso."""
    concurso = Concurso.query.get_or_404(concurso_id)
    
    if request.method == 'POST':
        try:              # Extract form data
            rol = request.form.get('rol')
            claustro = request.form.get('claustro')
            nombre = request.form.get('nombre')
            apellido = request.form.get('apellido')
            dni = request.form.get('dni')
            correo = request.form.get('correo')
            telefono = request.form.get('telefono')
            
            # First, find or create a Persona based on DNI
            persona = Persona.query.filter_by(dni=dni).first()
            
            if persona:
                # Update persona details if they've changed
                if persona.nombre != nombre or persona.apellido != apellido or persona.correo != correo or persona.telefono != telefono:
                    persona.nombre = nombre
                    persona.apellido = apellido
                    persona.correo = correo
                    persona.telefono = telefono
            else:                # Create new persona
                persona = Persona(
                    dni=dni,
                    nombre=nombre,
                    apellido=apellido,
                    correo=correo,
                    telefono=telefono,
                    username=dni  # Use DNI as username by default
                )
                db.session.add(persona)
                db.session.flush()  # To get the persona ID
            
            # Check if this persona is already assigned to this concurso
            existing_assignment = TribunalMiembro.query.filter_by(
                persona_id=persona.id, 
                concurso_id=concurso_id
            ).first()
            
            if existing_assignment:
                flash(f'La persona {nombre} {apellido} ya está asignada a este concurso como {existing_assignment.rol}.', 'warning')
                return redirect(url_for('tribunal.index', concurso_id=concurso_id))
            
            # Create Google Drive folder for tribunal member
            folder_name = f"{rol}_{apellido}_{nombre}_{dni}"
            folder_id = drive_api.create_tribunal_folder(
                parent_folder_id=concurso.tribunal_folder_id,
                nombre=nombre,
                apellido=apellido,
                dni=dni,
                rol=rol
            )
            
            # Create new tribunal member assignment
            miembro = TribunalMiembro(
                concurso_id=concurso_id,
                persona_id=persona.id,
                rol=rol,
                claustro=claustro,
                drive_folder_id=folder_id,
                notificado=False
            )
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
            
            flash('Miembro del tribunal agregado exitosamente. Use el botón "Notificar Tribunal" para enviarle el enlace de activación.', 'success')
            return redirect(url_for('tribunal.index', concurso_id=concurso_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al agregar miembro del tribunal: {str(e)}', 'danger')
    
    return render_template('tribunal/agregar.html', concurso=concurso)

@tribunal.route('/<int:miembro_id>/editar', methods=['GET', 'POST'])
@login_required
def editar(miembro_id):
    """Edit an existing tribunal member."""
    miembro = TribunalMiembro.query.get_or_404(miembro_id)
    concurso = Concurso.query.get_or_404(miembro.concurso_id)
    persona = miembro.persona
    
    if request.method == 'POST':
        try:            
            old_rol = miembro.rol
              # Update persona data
            persona.nombre = request.form.get('nombre')
            persona.apellido = request.form.get('apellido')
            persona.dni = request.form.get('dni')
            persona.correo = request.form.get('correo')
            persona.telefono = request.form.get('telefono')
            persona.username = persona.dni  # Keep username as DNI
            
            # Update assignment data
            miembro.rol = request.form.get('rol')
            miembro.claustro = request.form.get('claustro')
              # Handle permission checkboxes
            miembro.can_add_tema = 'can_add_tema' in request.form
            miembro.can_upload_file = 'can_upload_file' in request.form
            miembro.can_sign_file = 'can_sign_file' in request.form
            miembro.can_view_postulante_docs = 'can_view_postulante_docs' in request.form
            
            # Update Drive folder name if needed
            if miembro.drive_folder_id:
                new_folder_name = f"{miembro.rol}_{persona.apellido}_{persona.nombre}_{persona.dni}"
                drive_api.update_folder_name(miembro.drive_folder_id, new_folder_name)
            
            # Handle password reset if requested
            if 'regenerate_password' in request.form:
                # Generate reset token
                reset_token = persona.generate_reset_token()
                reset_url = url_for('tribunal.reset_password', token=reset_token, _external=True)
                
                # Send password reset email
                subject = f"Configuración de Nueva Contraseña - Portal de Tribunal"
                message = f"""
                <p>Estimado/a {persona.nombre} {persona.apellido}:</p>
                
                <p>Se solicita establecer una nueva contraseña para su cuenta en el sistema de concursos docentes.</p>    

                <p>Para configurar su nueva contraseña, haga clic en el siguiente enlace:</p>
                
                <p><a href="{reset_url}">Configurar Nueva Contraseña</a></p>
                
                <p>Este enlace es válido solo por un tiempo limitado y se desactivará después de configurar su contraseña.</p>
                
                <p>Si no solicitó este cambio, puede ignorar este correo.</p>
                
                <p>Saludos cordiales,<br>
                Sistema de Concursos Docentes</p>
                """
                
                try:
                    drive_api.send_email(
                        to_email=persona.correo,
                        subject=subject,
                        html_body=message,
                        sender_name='Sistema de Concursos Docentes'
                    )
                    flash('Se ha enviado un enlace de configuración de contraseña al correo del miembro.', 'success')
                except Exception as e:
                    flash(f'Error al enviar el correo: {str(e)}', 'warning')

            db.session.commit()

            # If this person is currently logged in, update their session data
            if 'persona_id' in session and session['persona_id'] == persona.id:
                session['tribunal_nombre'] = f"{persona.nombre} {persona.apellido}"
                # Update the role in session if it changed
                if 'tribunal_rol' not in session or old_rol != miembro.rol:
                    session['tribunal_rol'] = miembro.rol

            flash('Miembro del tribunal actualizado exitosamente.', 'success')
            return redirect(url_for('tribunal.index', concurso_id=miembro.concurso_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar miembro del tribunal: {str(e)}', 'danger')
    
    return render_template('tribunal/editar.html', miembro=miembro, persona=persona, concurso=concurso)

@tribunal.route('/<int:miembro_id>/eliminar', methods=['POST'])
@login_required
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
@login_required
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
@login_required
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



@tribunal.route('/notificar-tribunal/<int:concurso_id>/<int:documento_id>', methods=['POST'])
@login_required
def notificar_tribunal(concurso_id, documento_id):
    """Notify tribunal members with their credentials after acta constitución is generated."""
    try:
        concurso = Concurso.query.get_or_404(concurso_id)
        documento = DocumentoConcurso.query.get_or_404(documento_id)
        
        # Verify this is an Acta Constitución document
        if documento.tipo != 'ACTA_CONSTITUCION_TRIBUNAL_REGULAR':
            flash('Este documento no es un Acta de Constitución de Tribunal Regular.', 'danger')
            return redirect(url_for('concursos.ver', concurso_id=concurso_id))
          # Get only non-suplente members
        miembros = TribunalMiembro.query.filter(
            TribunalMiembro.concurso_id == concurso_id,
            TribunalMiembro.rol != 'Suplente'
        ).join(Persona).all()
        
        for miembro in miembros:
            persona = miembro.persona
            if not persona.correo:
                flash(f'El miembro {persona.nombre} {persona.apellido} no tiene correo registrado.', 'warning')
                continue
                
            # Ensure username is DNI
            persona.username = persona.dni
              # Generate reset token for password setup
            reset_token = persona.generate_reset_token()
            reset_url = url_for('tribunal.reset_password', token=reset_token, _external=True)
            
            # Prepare email content
            subject = f"Credenciales de Acceso - Tribunal Concurso #{concurso.id}"
            message = f"""
            <p>Estimado/a {persona.nombre} {persona.apellido}:</p>
            
            <p>Por medio de la presente, le informo que ha sido designado/a como miembro del tribunal para el 
            Concurso #{concurso.id} del Departamento de {concurso.departamento_rel.nombre}, Área {concurso.area}, 
            cargo {concurso.categoria} {concurso.dedicacion}.</p>
            
            <p><strong>Sus credenciales de acceso:</strong></p>
            <ul>
                <li><strong>Usuario:</strong> {persona.username}</li>
                <li>Para configurar su contraseña, haga clic en el siguiente enlace: 
                    <a href="{reset_url}">Configurar Contraseña</a>
                </li>
            </ul>
            
            <p>Este enlace es válido solo por un tiempo limitado y se desactivará después de configurar su contraseña.</p>
            
            <p>Una vez configurada su contraseña, puede ingresar al sistema en: 
            <a href="{request.host_url}tribunal/acceso">Portal de Tribunal</a></p>
            
            <p><strong>Información del Concurso:</strong></p>
            <ul>
                <li>Departamento: {concurso.departamento_rel.nombre}</li>
                <li>Área: {concurso.area}</li>
                <li>Orientación: {concurso.orientacion}</li>                <li>Categoría: {concurso.categoria_nombre} ({concurso.categoria})</li>
                <li>Dedicación: {concurso.dedicacion}</li>
                <li>Su rol: {miembro.rol}</li>
            </ul>
            """
            
            # Send email
            drive_api.send_email(
                to_email=persona.correo,
                subject=subject,
                html_body=message,
                sender_name='Sistema de Concursos Docentes'
            )
            
            # Update notification status
            miembro.notificado = True
            miembro.fecha_notificacion = datetime.utcnow()
        
        db.session.commit()
        flash('Correos de configuración de contraseña enviados exitosamente a todos los miembros del tribunal (excepto suplentes).', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al enviar credenciales: {str(e)}', 'danger')
    
    return redirect(url_for('concursos.ver', concurso_id=concurso_id))

@tribunal.route('/concurso/<int:concurso_id>/notificar-todos', methods=['POST'])
@login_required
def notificar_todos_miembros(concurso_id):
    """Notify all tribunal members with their credentials."""
    try:
        concurso = Concurso.query.get_or_404(concurso_id)
        miembros = TribunalMiembro.query.filter_by(concurso_id=concurso_id).join(Persona).all()
        
        notificados = 0
        errores = []
        
        for miembro in miembros:
            # Skip suplentes
            if miembro.rol.lower() == 'suplente':
                continue
                
            persona = miembro.persona
            
            if not persona.correo:
                errores.append(f'{persona.nombre} {persona.apellido} no tiene correo registrado')
                continue
            
            # Set username as DNI
            persona.username = persona.dni
            
            # Check if persona already has a password set
            has_password = persona.password_hash is not None
            
            if has_password:
                # Send login page link for users who already have passwords
                reset_url = url_for('tribunal.acceso', _external=True)
                subject = f"Designación en Tribunal - Concurso #{concurso.id} - Acceso al Portal"
                
                message = f"""
                <p>Estimado/a {persona.nombre} {persona.apellido}:</p>
                
                <p><strong>Ha sido designado/a como {miembro.rol.upper()} del Tribunal Evaluador</strong> para el siguiente concurso docente:</p>
                
                <div style="background-color: #f8f9fa; padding: 15px; margin: 15px 0; border-left: 4px solid #007bff;">
                    <h4>CONCURSO #{concurso.id}</h4>
                    <ul style="margin: 0; padding-left: 20px;">
                        <li><strong>Tipo:</strong> {concurso.tipo} - {concurso.cerrado_abierto}</li>
                        <li><strong>Departamento:</strong> {concurso.departamento_rel.nombre}</li>
                        <li><strong>Área:</strong> {concurso.area}</li>
                        <li><strong>Orientación:</strong> {concurso.orientacion}</li>
                        <li><strong>Categoría:</strong> {concurso.categoria_nombre} ({concurso.categoria})</li>
                        <li><strong>Dedicación:</strong> {concurso.dedicacion}</li>
                        <li><strong>Cantidad de cargos:</strong> {concurso.cant_cargos}</li>
                        {f'<li><strong>Expediente:</strong> {concurso.expediente}</li>' if concurso.expediente else ''}
                        {f'<li><strong>Resolución Llamado (Interino):</strong> {concurso.nro_res_llamado_interino}</li>' if concurso.nro_res_llamado_interino else ''}
                        {f'<li><strong>Resolución Llamado (Regular):</strong> {concurso.nro_res_llamado_regular}</li>' if concurso.nro_res_llamado_regular else ''}
                        {f'<li><strong>Resolución Tribunal:</strong> {concurso.nro_res_tribunal_regular}</li>' if concurso.nro_res_tribunal_regular else ''}
                    </ul>
                </div>
                
                <p><strong>Su designación como {miembro.rol.upper()}</strong> le otorga acceso al Portal de Tribunal donde podrá:</p>
                <ul>
                    <li>Consultar toda la documentación del concurso</li>
                    <li>Acceder a los expedientes de los postulantes</li>
                    <li>Participar en el proceso de evaluación</li>
                    <li>Gestionar la documentación del tribunal</li>
                    <li>Mantenerse informado sobre el cronograma y sustanciación</li>
                </ul>
                
                <p><strong>Para acceder al sistema:</strong></p>
                <div style="background-color: #e9f7ef; padding: 10px; margin: 10px 0; border-radius: 5px;">
                    <p><strong>🔗 Portal de Tribunal:</strong> <a href="{reset_url}" style="color: #007bff; text-decoration: none;"><strong>{reset_url}</strong></a></p>
                    <p><strong>👤 Su usuario:</strong> {persona.username}</p>
                    <p><em>Utilice la contraseña que ya tiene configurada</em></p>
                </div>
                """
            else:
                # Generate reset token for password setup
                reset_token = persona.generate_reset_token()
                reset_url = url_for('tribunal.reset_password', token=reset_token, _external=True)
                subject = f"Designación en Tribunal - Concurso #{concurso.id} - Configuración de Acceso"
                
                message = f"""
                <p>Estimado/a {persona.nombre} {persona.apellido}:</p>
                
                <p><strong>Ha sido designado/a como {miembro.rol.upper()} del Tribunal Evaluador</strong> para el siguiente concurso docente:</p>
                
                <div style="background-color: #f8f9fa; padding: 15px; margin: 15px 0; border-left: 4px solid #007bff;">
                    <h4>CONCURSO #{concurso.id}</h4>
                    <ul style="margin: 0; padding-left: 20px;">
                        <li><strong>Tipo:</strong> {concurso.tipo} - {concurso.cerrado_abierto}</li>
                        <li><strong>Departamento:</strong> {concurso.departamento_rel.nombre}</li>
                        <li><strong>Área:</strong> {concurso.area}</li>
                        <li><strong>Orientación:</strong> {concurso.orientacion}</li>
                        <li><strong>Categoría:</strong> {concurso.categoria_nombre} ({concurso.categoria})</li>
                        <li><strong>Dedicación:</strong> {concurso.dedicacion}</li>
                        <li><strong>Cantidad de cargos:</strong> {concurso.cant_cargos}</li>
                        {f'<li><strong>Expediente:</strong> {concurso.expediente}</li>' if concurso.expediente else ''}
                        {f'<li><strong>Resolución Llamado (Interino):</strong> {concurso.nro_res_llamado_interino}</li>' if concurso.nro_res_llamado_interino else ''}
                        {f'<li><strong>Resolución Llamado (Regular):</strong> {concurso.nro_res_llamado_regular}</li>' if concurso.nro_res_llamado_regular else ''}
                        {f'<li><strong>Resolución Tribunal:</strong> {concurso.nro_res_tribunal_regular}</li>' if concurso.nro_res_tribunal_regular else ''}
                    </ul>
                </div>
                
                <p><strong>Su designación como {miembro.rol.upper()}</strong> le otorga acceso al Portal de Tribunal donde podrá:</p>
                <ul>
                    <li>Consultar toda la documentación del concurso</li>
                    <li>Acceder a los expedientes de los postulantes</li>
                    <li>Participar en el proceso de evaluación</li>
                    <li>Gestionar la documentación del tribunal</li>
                    <li>Mantenerse informado sobre el cronograma y sustanciación</li>
                </ul>
                
                <p><strong>Para acceder al sistema debe configurar su contraseña:</strong></p>
                <div style="background-color: #fff3cd; padding: 10px; margin: 10px 0; border-radius: 5px;">
                    <p><strong>👤 Su usuario:</strong> {persona.username}</p>
                    <p><strong>🔑 Configurar contraseña:</strong> <a href="{reset_url}" style="color: #007bff; text-decoration: none;"><strong>Hacer clic aquí</strong></a></p>
                    <p><em>Este enlace es válido por tiempo limitado y se desactivará después de configurar su contraseña.</em></p>
                </div>
                
                <p>Una vez configurada su contraseña, podrá ingresar al sistema en: 
                <a href="{url_for('tribunal.acceso', _external=True)}" style="color: #007bff;">Portal de Tribunal</a></p>
                """
            
            # Add concurso information
            message += f"""
            <p><strong>Información del Concurso #{concurso.id}:</strong></p>
            <ul>
                <li>Departamento: {concurso.departamento_rel.nombre}</li>
                <li>Área: {concurso.area}</li>
                <li>Orientación: {concurso.orientacion}</li>
                <li>Categoría: {concurso.categoria_nombre} ({concurso.categoria})</li>
                <li>Dedicación: {concurso.dedicacion}</li>
                <li>Su rol: {miembro.rol}</li>
            </ul>
            """
            
            # Send email
            drive_api.send_email(
                to_email=persona.correo,
                subject=subject,
                html_body=message,
                sender_name='Sistema de Concursos Docentes'
            )
            
            # Update notification status
            miembro.notificado = True
            miembro.fecha_notificacion = datetime.utcnow()
        
        db.session.commit()
        
        # Show results
        if notificados > 0:
            flash(f'Credenciales enviadas exitosamente a {notificados} miembros del tribunal.', 'success')
        
        if errores:
            for error in errores:
                flash(error, 'warning')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al enviar credenciales: {str(e)}', 'danger')
    
    return redirect(url_for('tribunal.index', concurso_id=concurso_id))

@tribunal.route('/<int:miembro_id>/notificar', methods=['POST'])
@login_required
def notificar_miembro(miembro_id):
    """Notify a single tribunal member with their credentials."""
    try:
        miembro = TribunalMiembro.query.get_or_404(miembro_id)
        persona = miembro.persona
        concurso = Concurso.query.get_or_404(miembro.concurso_id)

        if not persona.correo:
            flash(f'El miembro {persona.nombre} {persona.apellido} no tiene correo registrado.', 'warning')
            return redirect(url_for('tribunal.index', concurso_id=concurso.id))
        
        # Set username as DNI
        persona.username = persona.dni
          # Check if persona already has a password set
        has_password = persona.password_hash is not None
        
        if has_password:
            # Send login page link for users who already have passwords
            reset_url = url_for('tribunal.acceso', _external=True)
            subject = f"Designación en Tribunal - Concurso #{concurso.id} - Acceso al Portal"
            
            message = f"""
            <p>Estimado/a {persona.nombre} {persona.apellido}:</p>
            
            <p><strong>Ha sido designado/a como {miembro.rol.upper()} del Tribunal Evaluador</strong> para el siguiente concurso docente:</p>
            
            <div style="background-color: #f8f9fa; padding: 15px; margin: 15px 0; border-left: 4px solid #007bff;">
                <h4>CONCURSO #{concurso.id}</h4>
                <ul style="margin: 0; padding-left: 20px;">
                    <li><strong>Tipo:</strong> {concurso.tipo} - {concurso.cerrado_abierto}</li>
                    <li><strong>Departamento:</strong> {concurso.departamento_rel.nombre}</li>
                    <li><strong>Área:</strong> {concurso.area}</li>
                    <li><strong>Orientación:</strong> {concurso.orientacion}</li>
                    <li><strong>Categoría:</strong> {concurso.categoria_nombre} ({concurso.categoria})</li>
                    <li><strong>Dedicación:</strong> {concurso.dedicacion}</li>
                    <li><strong>Cantidad de cargos:</strong> {concurso.cant_cargos}</li>
                    {f'<li><strong>Expediente:</strong> {concurso.expediente}</li>' if concurso.expediente else ''}
                    {f'<li><strong>Resolución Llamado (Interino):</strong> {concurso.nro_res_llamado_interino}</li>' if concurso.nro_res_llamado_interino else ''}
                    {f'<li><strong>Resolución Llamado (Regular):</strong> {concurso.nro_res_llamado_regular}</li>' if concurso.nro_res_llamado_regular else ''}
                    {f'<li><strong>Resolución Tribunal:</strong> {concurso.nro_res_tribunal_regular}</li>' if concurso.nro_res_tribunal_regular else ''}
                </ul>
            </div>
            
            <p><strong>Su designación como {miembro.rol.upper()}</strong> le otorga acceso al Portal de Tribunal donde podrá:</p>
            <ul>
                <li>Consultar toda la documentación del concurso</li>
                <li>Acceder a los expedientes de los postulantes</li>
                <li>Participar en el proceso de evaluación</li>
                <li>Gestionar la documentación del tribunal</li>
                <li>Mantenerse informado sobre el cronograma y sustanciación</li>
            </ul>
            
            <p><strong>Para acceder al sistema:</strong></p>
            <div style="background-color: #e9f7ef; padding: 10px; margin: 10px 0; border-radius: 5px;">
                <p><strong>🔗 Portal de Tribunal:</strong> <a href="{reset_url}" style="color: #007bff; text-decoration: none;"><strong>{reset_url}</strong></a></p>
                <p><strong>👤 Su usuario:</strong> {persona.username}</p>
                <p><em>Utilice la contraseña que ya tiene configurada</em></p>
            </div>
            """
        else:
            # Generate reset token for password setup
            reset_token = persona.generate_reset_token()
            reset_url = url_for('tribunal.reset_password', token=reset_token, _external=True)
            subject = f"Designación en Tribunal - Concurso #{concurso.id} - Configuración de Acceso"
            
            message = f"""
            <p>Estimado/a {persona.nombre} {persona.apellido}:</p>
            
            <p><strong>Ha sido designado/a como {miembro.rol.upper()} del Tribunal Evaluador</strong> para el siguiente concurso docente:</p>
            
            <div style="background-color: #f8f9fa; padding: 15px; margin: 15px 0; border-left: 4px solid #007bff;">
                <h4>CONCURSO #{concurso.id}</h4>
                <ul style="margin: 0; padding-left: 20px;">
                    <li><strong>Tipo:</strong> {concurso.tipo} - {concurso.cerrado_abierto}</li>
                    <li><strong>Departamento:</strong> {concurso.departamento_rel.nombre}</li>
                    <li><strong>Área:</strong> {concurso.area}</li>
                    <li><strong>Orientación:</strong> {concurso.orientacion}</li>
                    <li><strong>Categoría:</strong> {concurso.categoria_nombre} ({concurso.categoria})</li>
                    <li><strong>Dedicación:</strong> {concurso.dedicacion}</li>
                    <li><strong>Cantidad de cargos:</strong> {concurso.cant_cargos}</li>
                    {f'<li><strong>Expediente:</strong> {concurso.expediente}</li>' if concurso.expediente else ''}
                    {f'<li><strong>Resolución Llamado (Interino):</strong> {concurso.nro_res_llamado_interino}</li>' if concurso.nro_res_llamado_interino else ''}
                    {f'<li><strong>Resolución Llamado (Regular):</strong> {concurso.nro_res_llamado_regular}</li>' if concurso.nro_res_llamado_regular else ''}
                    {f'<li><strong>Resolución Tribunal:</strong> {concurso.nro_res_tribunal_regular}</li>' if concurso.nro_res_tribunal_regular else ''}
                </ul>
            </div>
            
            <p><strong>Su designación como {miembro.rol.upper()}</strong> le otorga acceso al Portal de Tribunal donde podrá:</p>
            <ul>
                <li>Consultar toda la documentación del concurso</li>
                <li>Acceder a los expedientes de los postulantes</li>
                <li>Participar en el proceso de evaluación</li>
                <li>Gestionar la documentación del tribunal</li>
                <li>Mantenerse informado sobre el cronograma y sustanciación</li>
            </ul>
            
            <p><strong>Para acceder al sistema debe configurar su contraseña:</strong></p>
            <div style="background-color: #fff3cd; padding: 10px; margin: 10px 0; border-radius: 5px;">
                <p><strong>👤 Su usuario:</strong> {persona.username}</p>
                <p><strong>🔑 Configurar contraseña:</strong> <a href="{reset_url}" style="color: #007bff; text-decoration: none;"><strong>Hacer clic aquí</strong></a></p>
                <p><em>Este enlace es válido por tiempo limitado y se desactivará después de configurar su contraseña.</em></p>
            </div>
            
            <p>Una vez configurada su contraseña, podrá ingresar al sistema en: 
            <a href="{url_for('tribunal.acceso', _external=True)}" style="color: #007bff;">Portal de Tribunal</a></p>
            """
        
        # Add concurso information
        message += f"""
        <p><strong>Información del Concurso #{concurso.id}:</strong></p>
        <ul>
            <li>Departamento: {concurso.departamento_rel.nombre}</li>
            <li>Área: {concurso.area}</li>
            <li>Orientación: {concurso.orientacion}</li>
            <li>Categoría: {concurso.categoria_nombre} ({concurso.categoria})</li>
            <li>Dedicación: {concurso.dedicacion}</li>
            <li>Su rol: {miembro.rol}</li>
        </ul>
        """
        
        # Send email
        drive_api.send_email(
            to_email=persona.correo,
            subject=subject,
            html_body=message,
            sender_name='Sistema de Concursos Docentes'
        )
        
        # Update notification status
        miembro.notificado = True
        miembro.fecha_notificacion = datetime.utcnow()
        
        db.session.commit()
        flash(f'Credenciales enviadas exitosamente a {persona.nombre} {persona.apellido}.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al enviar credenciales: {str(e)}', 'danger')
    
    return redirect(url_for('tribunal.index', concurso_id=concurso.id))

# Routes for tribunal member portal
@tribunal.route('/acceso', methods=['GET', 'POST'])
def acceso():
    """Login portal for tribunal members."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Find the persona by username
        persona = Persona.query.filter_by(username=username).first()
        
        if persona and persona.check_password(password):
            # Find an active tribunal assignment for this persona
            miembro = TribunalMiembro.query.filter_by(persona_id=persona.id).order_by(TribunalMiembro.id.desc()).first()
            
            if not miembro:
                flash('Su usuario no está asignado a ningún tribunal actualmente', 'danger')
                return render_template('tribunal/acceso.html')
            
            # Store persona id and tribunal member id in session
            session['persona_id'] = persona.id
            session['tribunal_miembro_id'] = miembro.id
            session['tribunal_nombre'] = f"{persona.nombre} {persona.apellido}"
            session['tribunal_rol'] = miembro.rol
            
            # Update last access time
            miembro.ultimo_acceso = datetime.utcnow()
            db.session.commit()
            
            flash(f'Bienvenido/a, {persona.nombre} {persona.apellido}', 'success')
            return redirect(url_for('tribunal.portal'))
        
        flash('Usuario o contraseña incorrectos', 'danger')
    
    return render_template('tribunal/acceso.html')

@tribunal.route('/reset/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Handle password reset/setup using a token."""
    # Find persona with this token
    persona = Persona.query.filter_by(reset_token=token).first()
    
    if not persona or not persona.check_reset_token(token):
        flash('El enlace de configuración de contraseña es inválido o ha expirado.', 'danger')
        return redirect(url_for('tribunal.acceso'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not password or len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres.', 'danger')
            return render_template('tribunal/reset_password.html', token=token)
        
        if password != confirm_password:
            flash('Las contraseñas no coinciden.', 'danger')
            return render_template('tribunal/reset_password.html', token=token)
        
        try:
            # Set the new password
            persona.set_password(password)
            db.session.commit()
            
            flash('Contraseña configurada exitosamente. Ya puede iniciar sesión.', 'success')
            return redirect(url_for('tribunal.acceso'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al configurar la contraseña: {str(e)}', 'danger')
            return render_template('tribunal/reset_password.html', token=token)
    
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
            # Generate reset token for password setup
            reset_token = persona.generate_reset_token()
            reset_url = url_for('tribunal.reset_password', token=reset_token, _external=True)
            
            subject = f"Activación de Cuenta - Portal de Tribunal"
            message = f"""
            <p>Estimado/a {persona.nombre} {persona.apellido}:</p>
            
            <p>Para activar su cuenta y configurar su contraseña, haga clic en el siguiente enlace:</p>
            <p><a href="{reset_url}">Activar Cuenta y Configurar Contraseña</a></p>
            
            <p>Su nombre de usuario es: <strong>{persona.dni}</strong></p>
            
            <p>Este enlace es válido solo por un tiempo limitado.</p>
            
            <p>Una vez configurada su contraseña, podrá ingresar al sistema desde: 
            <a href="{request.host_url}tribunal/acceso">Portal de Tribunal</a></p>
            """
            
            drive_api.send_email(
                to_email=persona.correo,
                subject=subject,
                html_body=message,
                sender_name='Sistema de Concursos Docentes'
            )
            
            flash('Se ha enviado un enlace de activación a su correo electrónico.', 'success')
            return redirect(url_for('tribunal.acceso'))
            
        except Exception as e:
            db.session.rollback()
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
            # Generate reset token for password setup
            reset_token = persona.generate_reset_token()
            reset_url = url_for('tribunal.reset_password', token=reset_token, _external=True)
            
            # Save the token to the database
            db.session.commit()
            
            # Prepare email content
            subject = f"Recuperación de Contraseña - Portal de Tribunal"
            message = f"""
            <p>Estimado/a {persona.nombre} {persona.apellido}:</p>
            
            <p>Recibimos una solicitud para restablecer su contraseña para el Portal de Tribunal.</p>
            
            <p>Para configurar una nueva contraseña, haga clic en el siguiente enlace:</p>
            <p><a href="{reset_url}">Configurar Nueva Contraseña</a></p>
            
            <p>Este enlace es válido solo por un tiempo limitado y se desactivará después de configurar su contraseña.</p>
            
            <p>Si no solicitó este cambio, puede ignorar este correo y su contraseña no será modificada.</p>
            
            <p>Saludos cordiales,<br>
            Sistema de Concursos Docentes</p>
            """
              # Send email
            drive_api.send_email(
                to_email=persona.correo,
                subject=subject,
                html_body=message,
                sender_name='Sistema de Concursos Docentes'
            )
            
            flash('Se ha enviado un enlace de restablecimiento de contraseña a su correo electrónico.', 'success')
            return redirect(url_for('tribunal.acceso'))
            
        except Exception as e:
            db.session.rollback()
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
def portal():
    """Main portal for tribunal members."""
    # Check if persona is logged in
    if 'persona_id' not in session:
        flash('Debe iniciar sesión para acceder al portal', 'warning')
        return redirect(url_for('tribunal.acceso'))
    
    # Get persona
    persona_id = session['persona_id']
    persona = Persona.query.get_or_404(persona_id)
    
    # Get active tribunal memberships
    miembro = TribunalMiembro.query.filter_by(persona_id=persona_id).order_by(TribunalMiembro.id.desc()).first()
    if not miembro:
        flash('No está asignado a ningún tribunal actualmente', 'warning')
        session.pop('persona_id', None)
        return redirect(url_for('tribunal.acceso'))
      # Get all concursos this persona is part of and their roles
    concursos = persona.get_concursos()
    
    # Get the roles for each concurso to simplify template rendering
    concurso_roles = {}
    for concurso in concursos:
        tribunal_miembro = TribunalMiembro.query.filter_by(
            persona_id=persona_id, 
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
def portal_concurso(concurso_id):
    """View for a tribunal member to see details of a specific concurso."""
    # Check if persona is logged in
    if 'persona_id' not in session or 'tribunal_miembro_id' not in session:
        flash('Debe iniciar sesión para acceder al portal', 'warning')
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
        
        # Check if member already signed        if documento.ya_firmado_por(miembro.id):
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
        
        try:
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
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al firmar el documento: {str(e)}', 'danger')
    
    return redirect(url_for('tribunal.portal_concurso', concurso_id=concurso_id))

@tribunal.route('/<int:concurso_id>/documento/<int:documento_id>/subir', methods=['POST'])
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
@login_required
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
            observaciones=f"Temas de sorteo eliminados y proceso reabierto para el tribunal por administrador {current_user.username}"
        )
        db.session.add(historial)
        db.session.commit()
        
        flash('Temas de sorteo eliminados exitosamente. El tribunal podrá cargar nuevos temas.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar los temas: {str(e)}', 'danger')
    
    return redirect(url_for('tribunal.portal_concurso', concurso_id=concurso_id))

@tribunal.route('/<int:concurso_id>/reset-temas-miembro/<int:miembro_id>', methods=['POST'])
@login_required
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
            observaciones = f"Propuesta de temas del miembro {miembro_target.persona.nombre} {miembro_target.persona.apellido} desbloqueada por administrador {current_user.username}. La consolidación de temas y el tema sorteado (si existía) han sido reiniciados. El miembro puede editar sus temas propuestos. Se requerirá nueva consolidación."
            flash_message = f'Propuesta de temas del miembro {miembro_target.persona.nombre} {miembro_target.persona.apellido} desbloqueada exitosamente. La consolidación general y el tema sorteado (si existía) han sido reiniciados. El miembro puede editar sus temas propuestos. Por favor, vuelva a consolidar los temas una vez que el miembro haya actualizado y enviado su propuesta.'
        else:
            # Standard unlock without un-consolidation
            estado = "TEMAS_SORTEO_MIEMBRO_DESBLOQUEADOS"
            observaciones = f"Propuesta de temas del miembro {miembro_target.persona.nombre} {miembro_target.persona.apellido} desbloqueada por administrador {current_user.username}"
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
@login_required
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
        'correo': persona.correo,
        'telefono': persona.telefono,
        'dni': persona.dni
    })

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
        return redirect(url_for('tribunal.documentacion_postulantes', concurso_id=concurso_id))