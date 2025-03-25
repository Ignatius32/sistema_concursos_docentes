from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session, send_file
from flask_login import login_required, current_user
from app.models.models import db, Concurso, TribunalMiembro, Recusacion, DocumentoTribunal, HistorialEstado, DocumentoConcurso, FirmaDocumento
from app.integrations.google_drive import GoogleDriveAPI
from app.helpers.pdf_utils import add_signature_stamp, verify_signed_pdf
from datetime import datetime
import os
import random
import string
from werkzeug.utils import secure_filename
from functools import wraps
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
    
    # Check if username exists
    existing = TribunalMiembro.query.filter(TribunalMiembro.username.like(f"{base_username}%")).all()
    
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
        if 'tribunal_miembro_id' not in session:
            flash('Debe iniciar sesión como miembro del tribunal para acceder.', 'warning')
            return redirect(url_for('tribunal.acceso'))
        return f(*args, **kwargs)
    return decorated_function

@tribunal.route('/concurso/<int:concurso_id>')
@login_required
def index(concurso_id):
    """Display tribunal members for a specific concurso."""
    concurso = Concurso.query.get_or_404(concurso_id)
    miembros = TribunalMiembro.query.filter_by(concurso_id=concurso_id).all()
    return render_template('tribunal/index.html', concurso=concurso, miembros=miembros)

@tribunal.route('/concurso/<int:concurso_id>/agregar', methods=['GET', 'POST'])
@login_required
def agregar(concurso_id):
    """Add a new member to the tribunal of a concurso."""
    concurso = Concurso.query.get_or_404(concurso_id)
    
    if request.method == 'POST':
        try:
            # Extract form data
            rol = request.form.get('rol')
            nombre = request.form.get('nombre')
            apellido = request.form.get('apellido')
            dni = request.form.get('dni')
            correo = request.form.get('correo')
            
            # Check if tribunal member already exists with this DNI
            existing_member = TribunalMiembro.query.filter_by(dni=dni).first()
            
            if existing_member:
                # Add existing member to this concurso
                existing_member.concurso_id = concurso_id
                existing_member.rol = rol
                db.session.commit()
                flash('Miembro del tribunal existente asignado a este concurso.', 'success')
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
            
            # Create new tribunal member with DNI as username
            miembro = TribunalMiembro(
                concurso_id=concurso_id,
                rol=rol,
                nombre=nombre,
                apellido=apellido,
                dni=dni,
                correo=correo,
                drive_folder_id=folder_id,
                username=dni,  # Use DNI as username
                notificado=False
            )
            
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
    
    if request.method == 'POST':
        try:
            old_rol = miembro.rol
            # Update member data from form
            miembro.rol = request.form.get('rol')
            miembro.nombre = request.form.get('nombre')
            miembro.apellido = request.form.get('apellido')
            miembro.dni = request.form.get('dni')
            miembro.correo = request.form.get('correo')
            miembro.username = miembro.dni  # Keep username as DNI
            
            # Update Drive folder name if needed
            if miembro.drive_folder_id:
                new_folder_name = f"{miembro.rol}_{miembro.apellido}_{miembro.nombre}_{miembro.dni}"
                drive_api.update_folder_name(miembro.drive_folder_id, new_folder_name)
            
            # Handle password reset if requested
            if 'regenerate_password' in request.form:
                # Generate reset token
                reset_token = miembro.generate_reset_token()
                reset_url = url_for('tribunal.reset_password', token=reset_token, _external=True)
                
                # Send password reset email
                subject = f"Configuración de Nueva Contraseña - Portal de Tribunal"
                message = f"""
                <p>Estimado/a {miembro.nombre} {miembro.apellido}:</p>
                
                <p>Se ha solicitado un cambio de contraseña para su cuenta en el Portal de Tribunal.</p>
                
                <p>Para configurar su nueva contraseña, haga clic en el siguiente enlace:</p>
                
                <p><a href="{reset_url}">Configurar Nueva Contraseña</a></p>
                
                <p>Este enlace es válido solo por un tiempo limitado y se desactivará después de configurar su contraseña.</p>
                
                <p>Si no solicitó este cambio, puede ignorar este correo.</p>
                
                <p>Saludos cordiales,<br>
                Sistema de Concursos Docentes</p>
                """
                
                try:
                    drive_api.send_email(
                        to_email=miembro.correo,
                        subject=subject,
                        html_body=message,
                        sender_name='Sistema de Concursos Docentes'
                    )
                    flash('Se ha enviado un enlace de configuración de contraseña al correo del miembro.', 'success')
                except Exception as e:
                    flash(f'Error al enviar el correo: {str(e)}', 'warning')

            db.session.commit()

            # If this member is currently logged in, update their session data
            if 'tribunal_miembro_id' in session and session['tribunal_miembro_id'] == miembro.id:
                session['tribunal_nombre'] = f"{miembro.nombre} {miembro.apellido}"
                # Update the role in session if it changed
                if 'tribunal_rol' not in session or old_rol != miembro.rol:
                    session['tribunal_rol'] = miembro.rol

            flash('Miembro del tribunal actualizado exitosamente.', 'success')
            return redirect(url_for('tribunal.index', concurso_id=miembro.concurso_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar miembro del tribunal: {str(e)}', 'danger')
    
    return render_template('tribunal/editar.html', miembro=miembro, concurso=concurso)

@tribunal.route('/<int:miembro_id>/eliminar', methods=['POST'])
@login_required
def eliminar(miembro_id):
    """Delete a tribunal member."""
    miembro = TribunalMiembro.query.get_or_404(miembro_id)
    concurso_id = miembro.concurso_id
    
    try:
        # Delete Drive folder if exists
        if miembro.drive_folder_id:
            drive_api.delete_folder(miembro.drive_folder_id)
        
        db.session.delete(miembro)
        db.session.commit()
        flash('Miembro del tribunal eliminado exitosamente.', 'success')
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
        filename = secure_filename(f"{tipo}_{miembro.apellido}_{miembro.nombre}_{concurso.id}.pdf")
        
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

@tribunal.route('/notificar-sustanciacion/<int:concurso_id>', methods=['GET', 'POST'])
@login_required
def notificar_sustanciacion(concurso_id):
    """Notify all tribunal members of a concurso about the process and send activation links."""
    concurso = Concurso.query.get_or_404(concurso_id)
    miembros = TribunalMiembro.query.filter_by(concurso_id=concurso_id).all()
    
    # Get sustanciacion info if it exists
    sustanciacion = concurso.sustanciacion
    
    if not sustanciacion:
        flash('Para notificar al tribunal, primero debe cargar la información de sustanciación.', 'warning')
        return redirect(url_for('concursos.editar', concurso_id=concurso_id))
    
    if request.method == 'POST':
        try:
            # Process notification message
            message_template = request.form.get('mensaje', '')
            
            # Send email to each member
            for miembro in miembros:
                # Skip if no email
                if not miembro.correo:
                    flash(f'El miembro {miembro.nombre} {miembro.apellido} no tiene correo registrado.', 'warning')
                    continue
                
                # Ensure username is DNI
                miembro.username = miembro.dni
                
                # Generate reset token for password setup
                reset_token = miembro.generate_reset_token()
                reset_url = url_for('tribunal.reset_password', token=reset_token, _external=True)
                
                # Custom message for this member
                member_message = message_template
                member_message += f"""
                <p><strong>Sus credenciales de acceso al sistema:</strong></p>
                <ul>
                    <li><strong>Usuario:</strong> {miembro.username}</li>
                    <li>Para configurar su contraseña, haga clic en el siguiente enlace: 
                        <a href="{reset_url}">Configurar Contraseña</a>
                    </li>
                </ul>
                
                <p>Este enlace es válido solo por un tiempo limitado y se desactivará después de configurar su contraseña.</p>
                
                <p>Una vez configurada su contraseña, puede ingresar al sistema en: 
                <a href="{request.host_url}tribunal/acceso">Portal de Tribunal</a></p>
                """
                
                # Add details of sustanciacion
                if sustanciacion:
                    member_message += f"""
                    <h4>Información de la sustanciación del concurso:</h4>
                    <p><strong>Fecha de constitución del tribunal:</strong> {sustanciacion.constitucion_fecha.strftime('%d/%m/%Y %H:%M') if sustanciacion.constitucion_fecha else 'No definida'}</p>
                    <p><strong>Lugar:</strong> {sustanciacion.constitucion_lugar or 'No definido'}</p>
                    """
                    
                    if sustanciacion.constitucion_virtual_link:
                        member_message += f'<p><strong>Enlace para reunión virtual:</strong> <a href="{sustanciacion.constitucion_virtual_link}">{sustanciacion.constitucion_virtual_link}</a></p>'
                    
                    if sustanciacion.constitucion_observaciones:
                        member_message += f'<p><strong>Observaciones:</strong> {sustanciacion.constitucion_observaciones}</p>'
                
                subject = f"Notificación de Constitución de Tribunal - Concurso {concurso.id}"
                
                # Send email
                try:
                    drive_api.send_email(
                        to_email=miembro.correo,
                        subject=subject,
                        html_body=member_message,
                        sender_name='Sistema de Concursos Docentes',
                        placeholders={
                            'nombre': miembro.nombre,
                            'apellido': miembro.apellido,
                            'rol': miembro.rol,
                            'concurso_id': str(concurso.id),
                            'departamento': concurso.departamento_rel.nombre,
                            'area': concurso.area,
                            'categoria': concurso.categoria_nombre or concurso.categoria,
                            'dedicacion': concurso.dedicacion
                        }
                    )
                    
                    # Update notification status
                    miembro.notificado = True
                    miembro.fecha_notificacion = datetime.utcnow()
                    
                except Exception as e:
                    flash(f'Error al enviar correo a {miembro.correo}: {str(e)}', 'danger')
            
            # Add entry to history
            historial = HistorialEstado(
                concurso=concurso,
                estado="TRIBUNAL_NOTIFICADO",
                observaciones=f"Tribunal notificado de la sustanciación por {current_user.username}"
            )
            db.session.add(historial)
            
            db.session.commit()
            flash('Tribunal notificado exitosamente', 'success')
            return redirect(url_for('tribunal.index', concurso_id=concurso_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al notificar al tribunal: {str(e)}', 'danger')
    
    return render_template('tribunal/notificar_sustanciacion.html', 
                          concurso=concurso, 
                          miembros=miembros,
                          sustanciacion=sustanciacion)

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
        ).all()
        
        for miembro in miembros:
            if not miembro.correo:
                flash(f'El miembro {miembro.nombre} {miembro.apellido} no tiene correo registrado.', 'warning')
                continue
                
            # Ensure username is DNI
            miembro.username = miembro.dni
            
            # Generate reset token for password setup
            reset_token = miembro.generate_reset_token()
            reset_url = url_for('tribunal.reset_password', token=reset_token, _external=True)
            
            # Prepare email content
            subject = f"Credenciales de Acceso - Tribunal Concurso #{concurso.id}"
            message = f"""
            <p>Estimado/a {miembro.nombre} {miembro.apellido}:</p>
            
            <p>Por medio de la presente, le informo que ha sido designado/a como miembro del tribunal para el 
            Concurso #{concurso.id} del Departamento de {concurso.departamento_rel.nombre}, Área {concurso.area}, 
            cargo {concurso.categoria} {concurso.dedicacion}.</p>
            
            <p><strong>Sus credenciales de acceso:</strong></p>
            <ul>
                <li><strong>Usuario:</strong> {miembro.username}</li>
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
                <li>Orientación: {concurso.orientacion}</li>
                <li>Categoría: {concurso.categoria_nombre} ({concurso.categoria})</li>
                <li>Dedicación: {concurso.dedicacion}</li>
                <li>Su rol: {miembro.rol}</li>
            </ul>
            """
            
            # Send email
            drive_api.send_email(
                to_email=miembro.correo,
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

@tribunal.route('/<int:miembro_id>/notificar', methods=['POST'])
@login_required
def notificar_miembro(miembro_id):
    """Notify a single tribunal member with their credentials and sustanciación info."""
    try:
        miembro = TribunalMiembro.query.get_or_404(miembro_id)
        concurso = Concurso.query.get_or_404(miembro.concurso_id)
        sustanciacion = concurso.sustanciacion

        if not miembro.correo:
            flash(f'El miembro {miembro.nombre} {miembro.apellido} no tiene correo registrado.', 'warning')
            return redirect(url_for('tribunal.index', concurso_id=concurso.id))
        
        # Ensure username is DNI
        miembro.username = miembro.dni
        
        # Generate reset token for password setup if not already notified
        if not miembro.notificado:
            reset_token = miembro.generate_reset_token()
            reset_url = url_for('tribunal.reset_password', token=reset_token, _external=True)
        else:
            reset_url = url_for('tribunal.acceso', _external=True)
        
        # Prepare email content
        message = f"""
        <p>Estimado/a {miembro.nombre} {miembro.apellido}:</p>
        
        <p>Por medio de la presente, le envío información actualizada sobre el concurso donde ha sido designado/a 
        como {miembro.rol} del tribunal:</p>

        <p><strong>Información del Concurso #</strong>{concurso.id}:</p>
        <ul>
            <li>Departamento: {concurso.departamento_rel.nombre}</li>
            <li>Área: {concurso.area}</li>
            <li>Orientación: {concurso.orientacion}</li>
            <li>Categoría: {concurso.categoria_nombre} ({concurso.categoria})</li>
            <li>Dedicación: {concurso.dedicacion}</li>
            <li>Su rol: {miembro.rol}</li>
        </ul>
        """

        if not miembro.notificado:
            message += f"""
            <p><strong>Sus credenciales de acceso al sistema:</strong></p>
            <ul>
                <li><strong>Usuario:</strong> {miembro.username}</li>
                <li>Para configurar su contraseña, haga clic en el siguiente enlace: 
                    <a href="{reset_url}">Configurar Contraseña</a>
                </li>
            </ul>
            
            <p>Este enlace es válido solo por un tiempo limitado y se desactivará después de configurar su contraseña.</p>
            """
        else:
            message += f"""
            <p>Para acceder al sistema utilice el siguiente enlace con sus credenciales ya configuradas:</p>
            <p><a href="{reset_url}">Portal de Tribunal</a></p>
            """

        # Add sustanciación details if available
        if sustanciacion:
            message += f"""
            <h4>Información de la sustanciación del concurso:</h4>
            """
            
            if sustanciacion.constitucion_fecha:
                message += f"""
                <p><strong>Constitución del Tribunal:</strong></p>
                <ul>
                    <li><strong>Fecha:</strong> {sustanciacion.constitucion_fecha.strftime('%d/%m/%Y %H:%M')}</li>
                    <li><strong>Lugar:</strong> {sustanciacion.constitucion_lugar or 'No definido'}</li>
                    {f'<li><strong>Enlace virtual:</strong> <a href="{sustanciacion.constitucion_virtual_link}">{sustanciacion.constitucion_virtual_link}</a></li>' if sustanciacion.constitucion_virtual_link else ''}
                    {f'<li><strong>Observaciones:</strong> {sustanciacion.constitucion_observaciones}</li>' if sustanciacion.constitucion_observaciones else ''}
                </ul>
                """
            
            if sustanciacion.sorteo_fecha:
                message += f"""
                <p><strong>Sorteo de Temas:</strong></p>
                <ul>
                    <li><strong>Fecha:</strong> {sustanciacion.sorteo_fecha.strftime('%d/%m/%Y %H:%M')}</li>
                    <li><strong>Lugar:</strong> {sustanciacion.sorteo_lugar or 'No definido'}</li>
                    {f'<li><strong>Enlace virtual:</strong> <a href="{sustanciacion.sorteo_virtual_link}">{sustanciacion.sorteo_virtual_link}</a></li>' if sustanciacion.sorteo_virtual_link else ''}
                    {f'<li><strong>Observaciones:</strong> {sustanciacion.sorteo_observaciones}</li>' if sustanciacion.sorteo_observaciones else ''}
                </ul>
                """
            
            if sustanciacion.exposicion_fecha:
                message += f"""
                <p><strong>Exposición:</strong></p>
                <ul>
                    <li><strong>Fecha:</strong> {sustanciacion.exposicion_fecha.strftime('%d/%m/%Y %H:%M')}</li>
                    <li><strong>Lugar:</strong> {sustanciacion.exposicion_lugar or 'No definido'}</li>
                    {f'<li><strong>Enlace virtual:</strong> <a href="{sustanciacion.exposicion_virtual_link}">{sustanciacion.exposicion_virtual_link}</a></li>' if sustanciacion.exposicion_virtual_link else ''}
                    {f'<li><strong>Observaciones:</strong> {sustanciacion.exposicion_observaciones}</li>' if sustanciacion.exposicion_observaciones else ''}
                </ul>
                """
            
            if sustanciacion.temas_exposicion:
                message += f"""
                <p><strong>Temas para la exposición:</strong></p>
                <pre>{sustanciacion.temas_exposicion}</pre>
                """

        subject = f"Notificación Sustanciación Concurso #{concurso.id}"
        
        # Send email
        drive_api.send_email(
            to_email=miembro.correo,
            subject=subject,
            html_body=message,
            sender_name='Sistema de Concursos Docentes'
        )
        
        # Update notification status
        if not miembro.notificado:
            miembro.notificado = True
            miembro.fecha_notificacion = datetime.utcnow()
        
        miembro.notificado_sustanciacion = True
        miembro.fecha_notificacion_sustanciacion = datetime.utcnow()
        
        # Add entry to history
        historial = HistorialEstado(
            concurso=concurso,
            estado="MIEMBRO_TRIBUNAL_NOTIFICADO_SUSTANCIACION",
            observaciones=f"Miembro del tribunal {miembro.nombre} {miembro.apellido} notificado de la sustanciación por {current_user.username}"
        )
        db.session.add(historial)
        
        db.session.commit()
        flash(f'Notificación de sustanciación enviada exitosamente a {miembro.nombre} {miembro.apellido}.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al enviar notificación: {str(e)}', 'danger')
    
    return redirect(url_for('tribunal.index', concurso_id=concurso.id))

# Routes for tribunal member portal
@tribunal.route('/acceso', methods=['GET', 'POST'])
def acceso():
    """Login portal for tribunal members."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Find the tribunal member by username
        miembro = TribunalMiembro.query.filter_by(username=username).first()
        
        if miembro and miembro.check_password(password):
            # Store tribunal member id in session
            session['tribunal_miembro_id'] = miembro.id
            session['tribunal_nombre'] = f"{miembro.nombre} {miembro.apellido}"
            session['tribunal_rol'] = miembro.rol  # Store the role in session
            
            # Update last access time
            miembro.ultimo_acceso = datetime.utcnow()
            db.session.commit()
            
            flash(f'Bienvenido/a, {miembro.nombre} {miembro.apellido}', 'success')
            return redirect(url_for('tribunal.portal'))
        
        flash('Usuario o contraseña incorrectos', 'danger')
    
    return render_template('tribunal/acceso.html')

@tribunal.route('/reset/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Handle password reset/setup using a token."""
    # Find tribunal member with this token
    miembro = TribunalMiembro.query.filter_by(reset_token=token).first()
    
    if not miembro or not miembro.check_reset_token(token):
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
            miembro.set_password(password)
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
        
        miembro = TribunalMiembro.query.filter_by(dni=dni, correo=correo).first()
        
        if not miembro:
            flash('No se encontró un miembro del tribunal con esos datos.', 'danger')
            return render_template('tribunal/activar_cuenta.html')
            
        try:
            # Generate reset token for password setup
            reset_token = miembro.generate_reset_token()
            reset_url = url_for('tribunal.reset_password', token=reset_token, _external=True)
            
            subject = f"Activación de Cuenta - Portal de Tribunal"
            message = f"""
            <p>Estimado/a {miembro.nombre} {miembro.apellido}:</p>
            
            <p>Para activar su cuenta y configurar su contraseña, haga clic en el siguiente enlace:</p>
            <p><a href="{reset_url}">Activar Cuenta y Configurar Contraseña</a></p>
            
            <p>Su nombre de usuario es: <strong>{miembro.dni}</strong></p>
            
            <p>Este enlace es válido solo por un tiempo limitado.</p>
            
            <p>Una vez configurada su contraseña, podrá ingresar al sistema desde: 
            <a href="{request.host_url}tribunal/acceso">Portal de Tribunal</a></p>
            """
            
            drive_api.send_email(
                to_email=miembro.correo,
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
        
        # Find tribunal member by DNI and email
        miembro = TribunalMiembro.query.filter_by(dni=dni, correo=correo).first()
        
        if not miembro:
            flash('No se encontró un miembro del tribunal con esos datos.', 'danger')
            return render_template('tribunal/recuperar_password.html')
        
        try:
            # Generate reset token for password setup
            reset_token = miembro.generate_reset_token()
            reset_url = url_for('tribunal.reset_password', token=reset_token, _external=True)
            
            # Save the token to the database
            db.session.commit()
            
            # Prepare email content
            subject = f"Recuperación de Contraseña - Portal de Tribunal"
            message = f"""
            <p>Estimado/a {miembro.nombre} {miembro.apellido}:</p>
            
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
                to_email=miembro.correo,
                subject=subject,
                html_body=message,
                sender_name='Sistema de Concursos Docentes'
            )
            
            flash('Se ha enviado un enlace de restablecimiento de contraseña a su correo electrónico.', 'success')
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
    session.pop('tribunal_miembro_id', None)
    session.pop('tribunal_nombre', None)
    session.pop('tribunal_rol', None)  # Also clear the role from session
    flash('Sesión cerrada exitosamente', 'success')
    return redirect(url_for('tribunal.acceso'))

@tribunal.route('/portal')
def portal():
    """Main portal for tribunal members."""
    # Check if tribunal member is logged in
    if 'tribunal_miembro_id' not in session:
        flash('Debe iniciar sesión para acceder al portal', 'warning')
        return redirect(url_for('tribunal.acceso'))
    
    # Get tribunal member
    miembro_id = session['tribunal_miembro_id']
    miembro = TribunalMiembro.query.get_or_404(miembro_id)
    
    # Get all concursos this member is part of
    concursos = miembro.get_concursos()
    
    return render_template('tribunal/portal.html', 
                          miembro=miembro, 
                          concursos=concursos)

@tribunal.route('/portal/concurso/<int:concurso_id>')
def portal_concurso(concurso_id):
    """View for a tribunal member to see details of a specific concurso."""
    # Check if tribunal member is logged in
    if 'tribunal_miembro_id' not in session:
        flash('Debe iniciar sesión para acceder al portal', 'warning')
        return redirect(url_for('tribunal.acceso'))
    
    # Get tribunal member
    miembro_id = session['tribunal_miembro_id']
    miembro = TribunalMiembro.query.get_or_404(miembro_id)
    
    # Get concurso and verify this member is part of it
    concurso = Concurso.query.get_or_404(concurso_id)
    if not TribunalMiembro.query.filter_by(id=miembro_id, concurso_id=concurso_id).first():
        flash('No tiene permisos para ver este concurso', 'danger')
        return redirect(url_for('tribunal.portal'))
    
    # Get other tribunal members for this concurso
    miembros = TribunalMiembro.query.filter_by(concurso_id=concurso_id).all()
    
    # Get postulantes
    postulantes = concurso.postulantes.all()
    
    # Ensure role is set properly for template checks
    if 'tribunal_rol' in session:
        miembro.rol = session['tribunal_rol']
    
    return render_template('tribunal/portal_concurso.html',
                          miembro=miembro,
                          concurso=concurso,
                          miembros=miembros,
                          postulantes=postulantes)

@tribunal.route('/<int:concurso_id>/documento/<int:documento_id>/subir-firmado', methods=['POST'])
@tribunal_login_required
def subir_documento_presidente(concurso_id, documento_id):
    """Handle signed document upload from tribunal members - President only"""
    
    try:
        concurso = Concurso.query.get_or_404(concurso_id)
        documento = DocumentoConcurso.query.get_or_404(documento_id)
        miembro = TribunalMiembro.query.filter_by(
            id=session['tribunal_miembro_id'],
            concurso_id=concurso_id
        ).first_or_404()
        
        # Verify the document belongs to this concurso
        if documento.concurso_id != concurso_id:
            flash('El documento no pertenece a este concurso.', 'danger')
            return redirect(url_for('tribunal.portal_concurso', concurso_id=concurso_id))
        
        # Only allow Presidente to upload signed documents
        if miembro.rol != 'Presidente':
            flash('Solo el presidente del tribunal puede subir documentos firmados.', 'danger')
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
        base_filename = documento.tipo.lower().replace('_', ' ') + f"_concurso_{concurso.id}"
        filename = secure_filename(f"{base_filename}_firmado.pdf")
        
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
            observaciones=f"Documento {documento.tipo} subido por {miembro.nombre} {miembro.apellido}, pendiente de firma"
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
        miembro = TribunalMiembro.query.filter_by(
            id=session['tribunal_miembro_id'],
            concurso_id=concurso_id
        ).first_or_404()
        
        # Verify the document belongs to this concurso
        if documento.concurso_id != concurso_id:
            flash('El documento no pertenece a este concurso.', 'danger')
            return redirect(url_for('tribunal.portal_concurso', concurso_id=concurso_id))
        
        # Check if document is pending signature - use consistent state
        if documento.estado != 'PENDIENTE DE FIRMA':
            flash('Este documento no está pendiente de firma.', 'danger')
            return redirect(url_for('tribunal.portal_concurso', concurso_id=concurso_id))
        
        # Check if member already signed
        if documento.ya_firmado_por(miembro.id):
            flash('Ya ha firmado este documento.', 'danger')
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
                miembro.apellido,
                miembro.nombre,
                miembro.dni,
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
            
            # Update document status if all tribunal members have signed
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
    """Handle tribunal member uploading a signed document."""
    if 'documento' not in request.files:
        flash('No se seleccionó ningún archivo.', 'danger')
        return redirect(url_for('tribunal.portal_concurso', concurso_id=concurso_id))

    file = request.files['documento']
    if file.filename == '':
        flash('No se seleccionó ningún archivo.', 'danger')
        return redirect(url_for('tribunal.portal_concurso', concurso_id=concurso_id))

    try:
        concurso = Concurso.query.get_or_404(concurso_id)
        documento = DocumentoConcurso.query.get_or_404(documento_id)

        # Upload file to Google Drive
        file_data = file.read()
        file_id, web_link = drive_api.upload_document(
            concurso.documentos_firmados_folder_id,
            file.filename,
            file_data
        )

        # Update document record with consistent state
        documento.url = web_link
        documento.file_id = file_id
        documento.estado = 'PENDIENTE DE FIRMA'  # Using spaces to match template check
        documento.firma_count = 0  # Reset firma count for new document
        
        # Add history entry
        historial = HistorialEstado(
            concurso=concurso,
            estado="DOCUMENTO_SUBIDO",
            observaciones=f"Documento {documento.tipo} subido, pendiente de firma por el tribunal"
        )
        db.session.add(historial)
        
        db.session.commit()

        flash('Documento subido exitosamente.', 'success')
        return redirect(url_for('tribunal.portal_concurso', concurso_id=concurso_id))

    except Exception as e:
        db.session.rollback()
        flash(f'Error al subir el documento: {str(e)}', 'danger')
        return redirect(url_for('tribunal.portal_concurso', concurso_id=concurso_id))

@tribunal.route('/<int:concurso_id>/documento/<int:documento_id>/view', methods=['GET'])
@tribunal_login_required
def ver_documento(concurso_id, documento_id):
    """Display document content in a viewer."""
    try:
        # Get concurso, documento and current tribunal member
        concurso = Concurso.query.get_or_404(concurso_id)
        documento = DocumentoConcurso.query.get_or_404(documento_id)
        miembro = TribunalMiembro.query.filter_by(
            id=session['tribunal_miembro_id'],
            concurso_id=concurso_id
        ).first_or_404()
        
        # Verify the document belongs to this concurso
        if documento.concurso_id != concurso_id:
            flash('El documento no pertenece a este concurso.', 'danger')
            return redirect(url_for('tribunal.portal_concurso', concurso_id=concurso_id))
            
        # Get correct file_id based on document state
        if documento.estado in ['PENDIENTE DE FIRMA', 'FIRMADO'] and documento.file_id:
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
    """Load sorteo temas for a concurso. Only accessible by tribunal presidente."""
    concurso = Concurso.query.get_or_404(concurso_id)
    miembro = TribunalMiembro.query.filter_by(
        id=session['tribunal_miembro_id'],
        concurso_id=concurso_id
    ).first_or_404()
    
    # Ensure role is set from session for proper template checks
    if 'tribunal_rol' in session:
        miembro.rol = session['tribunal_rol']
    
    if request.method == 'POST':
        if miembro.rol != 'Presidente':
            flash('Solo el presidente del tribunal puede cargar los temas de sorteo.', 'danger')
            return redirect(url_for('tribunal.portal_concurso', concurso_id=concurso_id))
        
        temas = request.form.get('temas_exposicion')
        if not temas:
            flash('Debe ingresar al menos un tema.', 'warning')
            return render_template('tribunal/cargar_sorteos.html', concurso=concurso, miembro=miembro)
        
        try:
            # Create or update sustanciacion record
            sustanciacion = concurso.sustanciacion
            if not sustanciacion:
                flash('No existe información de sustanciación para este concurso.', 'danger')
                return redirect(url_for('tribunal.portal_concurso', concurso_id=concurso_id))
            
            # Update temas
            sustanciacion.temas_exposicion = temas
            
            # Add entry to history
            historial = HistorialEstado(
                concurso=concurso,
                estado="TEMAS_SORTEO_CARGADOS",
                observaciones=f"Temas de sorteo cargados por el presidente del tribunal {miembro.nombre} {miembro.apellido}"
            )
            db.session.add(historial)
            db.session.commit()
            
            flash('Temas de sorteo guardados exitosamente.', 'success')
            return redirect(url_for('tribunal.portal_concurso', concurso_id=concurso_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al guardar los temas: {str(e)}', 'danger')
    
    return render_template('tribunal/cargar_sorteos.html', concurso=concurso, miembro=miembro)

@tribunal.route('/<int:concurso_id>/reset-temas', methods=['POST'])
@login_required
def reset_temas(concurso_id):
    """Reset sorteo temas for a concurso. Only accessible by admin."""
    concurso = Concurso.query.get_or_404(concurso_id)
    
    if not concurso.sustanciacion:
        flash('El concurso no tiene información de sustanciación.', 'danger')
        return redirect(url_for('tribunal.portal_concurso', concurso_id=concurso_id))
    
    try:
        concurso.sustanciacion.temas_exposicion = None
        
        # Add entry to history
        historial = HistorialEstado(
            concurso=concurso,
            estado="TEMAS_SORTEO_ELIMINADOS",
            observaciones=f"Temas de sorteo eliminados por administrador {current_user.username}"
        )
        db.session.add(historial)
        db.session.commit()
        
        flash('Temas de sorteo eliminados exitosamente.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar los temas: {str(e)}', 'danger')
    
    return redirect(url_for('tribunal.portal_concurso', concurso_id=concurso_id))