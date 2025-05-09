from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from app.models.models import db, Persona
from app.integrations.google_drive import GoogleDriveAPI
from werkzeug.utils import secure_filename
from datetime import datetime
from functools import wraps

admin_personas_bp = Blueprint('admin_personas', __name__, url_prefix='/admin/personas')
drive_api = GoogleDriveAPI()

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Acceso no autorizado. Debe iniciar sesión.', 'danger')
            return redirect(url_for('auth.login'))
        
        # Check if user is admin (either is admin user or has admin role)
        if hasattr(current_user, 'is_admin') and current_user.is_admin:
            return f(*args, **kwargs)
        elif hasattr(current_user, 'role') and current_user.role == 'admin':
            return f(*args, **kwargs)
        else:
            flash('Acceso no autorizado. Requiere permisos de administrador.', 'danger')
            return redirect(url_for('concursos.index'))
            
    return decorated_function

@admin_personas_bp.route('/', methods=['GET'])
@login_required
@admin_required
def list_personas():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 15, type=int)
    personas_pagination = Persona.query.order_by(Persona.apellido, Persona.nombre).paginate(page=page, per_page=per_page)
    return render_template('admin/personas/index.html', personas_pagination=personas_pagination)

@admin_personas_bp.route('/<int:persona_id>/editar', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_persona(persona_id):
    persona = Persona.query.get_or_404(persona_id)
    if request.method == 'POST':
        try:            
            persona.nombre = request.form.get('nombre', persona.nombre)
            persona.apellido = request.form.get('apellido', persona.apellido)
            persona.dni = request.form.get('dni', persona.dni)
            persona.correo = request.form.get('correo', persona.correo)
            persona.telefono = request.form.get('telefono', persona.telefono)
            # persona.is_admin = 'is_admin' in request.form # Optional: if you want to manage admin status here

            cv_file = request.files.get('cv_file')
            if cv_file and cv_file.filename != '':
                if not cv_file.filename.lower().endswith('.pdf'):
                    flash('Solo se permiten archivos PDF para el CV.', 'danger')
                    return redirect(url_for('admin_personas.edit_persona', persona_id=persona.id))

                year = datetime.now().year
                filename = secure_filename(f"CV_{persona.apellido}_{persona.nombre}_{year}.pdf")
                
                # Delete old CV if exists
                if persona.cv_drive_file_id:
                    try:
                        drive_api.delete_file(persona.cv_drive_file_id)
                    except Exception as e:
                        flash(f'No se pudo eliminar el CV anterior de Drive: {str(e)}', 'warning')
                    persona.cv_drive_file_id = None
                    persona.cv_drive_web_link = None
                    db.session.commit() # Commit deletion of old CV details

                cv_data = cv_file.read()
                cvs_folder_id = current_app.config.get('GOOGLE_DRIVE_CVS_FOLDER_ID')
                if not cvs_folder_id:
                    flash('La carpeta de CVs en Google Drive no está configurada.', 'danger')
                    return redirect(url_for('admin_personas.edit_persona', persona_id=persona.id))

                file_id, web_link = drive_api.upload_document(cvs_folder_id, filename, cv_data, 'application/pdf')
                persona.cv_drive_file_id = file_id
                persona.cv_drive_web_link = web_link
                flash('CV subido/actualizado exitosamente.', 'success')

            db.session.commit()
            flash('Persona actualizada exitosamente.', 'success')
            return redirect(url_for('admin_personas.edit_persona', persona_id=persona.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar la persona: {str(e)}', 'danger')
    
    return render_template('admin/personas/edit_persona.html', persona=persona)

@admin_personas_bp.route('/nueva', methods=['GET', 'POST'])
@login_required
@admin_required
def nueva_persona():    
    if request.method == 'POST':
        try:
            nueva_persona = Persona(
                nombre=request.form.get('nombre'),
                apellido=request.form.get('apellido'),
                dni=request.form.get('dni'),
                correo=request.form.get('correo'),
                telefono=request.form.get('telefono'),
                is_admin='is_admin' in request.form
            )
            
            # If username is provided, set it and password
            username = request.form.get('username')
            if username and username.strip():
                nueva_persona.username = username
                password = request.form.get('password')
                if password and password.strip():
                    nueva_persona.set_password(password)
            
            db.session.add(nueva_persona)
            
            # Handle CV upload if provided
            cv_file = request.files.get('cv_file')
            if cv_file and cv_file.filename != '':
                if not cv_file.filename.lower().endswith('.pdf'):
                    flash('Solo se permiten archivos PDF para el CV.', 'danger')
                    db.session.rollback()
                    return render_template('admin/personas/nueva_persona.html')

                # First add the persona to get an ID
                db.session.commit()
                
                year = datetime.now().year
                filename = secure_filename(f"CV_{nueva_persona.apellido}_{nueva_persona.nombre}_{year}.pdf")
                
                cv_data = cv_file.read()
                cvs_folder_id = current_app.config.get('GOOGLE_DRIVE_CVS_FOLDER_ID')
                if not cvs_folder_id:
                    flash('La carpeta de CVs en Google Drive no está configurada.', 'danger')
                    return render_template('admin/personas/nueva_persona.html')

                file_id, web_link = drive_api.upload_document(cvs_folder_id, filename, cv_data, 'application/pdf')
                nueva_persona.cv_drive_file_id = file_id
                nueva_persona.cv_drive_web_link = web_link
                db.session.commit()
                flash('CV subido exitosamente.', 'success')
            else:
                db.session.commit()
            
            flash('Persona creada exitosamente.', 'success')
            return redirect(url_for('admin_personas.list_personas'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear la persona: {str(e)}', 'danger')
    
    return render_template('admin/personas/nueva_persona.html')

@admin_personas_bp.route('/<int:persona_id>/cv/eliminar', methods=['POST'])
@login_required
@admin_required
def delete_persona_cv(persona_id):
    persona = Persona.query.get_or_404(persona_id)
    if persona.cv_drive_file_id:
        try:
            drive_api.delete_file(persona.cv_drive_file_id)
            persona.cv_drive_file_id = None
            persona.cv_drive_web_link = None
            db.session.commit()
            flash('CV eliminado exitosamente de Drive y la base de datos.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al eliminar el CV: {str(e)}', 'danger')
    else:
        flash('La persona no tiene un CV cargado para eliminar.', 'info')
    return redirect(url_for('admin_personas.edit_persona', persona_id=persona.id))

@admin_personas_bp.route('/<int:persona_id>/eliminar', methods=['POST'])
@login_required
@admin_required
def eliminar_persona(persona_id):
    persona = Persona.query.get_or_404(persona_id)
    try:
        # Delete CV from Google Drive if it exists
        if persona.cv_drive_file_id:
            try:
                drive_api.delete_file(persona.cv_drive_file_id)
            except Exception as e:
                flash(f'No se pudo eliminar el CV de Drive: {str(e)}', 'warning')
        
        # Store persona info for the success message
        nombre_completo = f"{persona.apellido}, {persona.nombre}"
        
        # Delete the persona from the database
        db.session.delete(persona)
        db.session.commit()
        
        flash(f'Persona "{nombre_completo}" eliminada exitosamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar la persona: {str(e)}', 'danger')
    
    return redirect(url_for('admin_personas.list_personas'))
