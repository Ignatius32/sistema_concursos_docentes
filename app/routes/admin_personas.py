from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, g
from app.models.models import db, Persona
from app.integrations.google_drive import GoogleDriveAPI
from app.integrations.keycloak_admin_client import get_keycloak_admin
from app.config.keycloak_config import KeycloakConfig
from app.utils.keycloak_auth import keycloak_login_required, admin_required, get_current_user_info
from werkzeug.utils import secure_filename
from datetime import datetime
import logging
import secrets

logger = logging.getLogger(__name__)
admin_personas_bp = Blueprint('admin_personas', __name__, url_prefix='/admin/personas')
drive_api = GoogleDriveAPI()

# Enable Keycloak admin client
keycloak_admin = get_keycloak_admin()

@admin_personas_bp.route('/', methods=['GET'])
@keycloak_login_required
@admin_required
def list_personas():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 15, type=int)
    personas_pagination = Persona.query.order_by(Persona.apellido, Persona.nombre).paginate(page=page, per_page=per_page)
    return render_template('admin/personas/index.html', personas_pagination=personas_pagination)

@admin_personas_bp.route('/<int:persona_id>/editar', methods=['GET', 'POST'])
@keycloak_login_required
@admin_required
def edit_persona(persona_id):
    persona = Persona.query.get_or_404(persona_id)
    
    if request.method == 'POST':
        try:
            # Get original values
            old_is_admin = persona.is_admin
            
            # Update persona data
            persona.nombre = request.form.get('nombre', persona.nombre)
            persona.apellido = request.form.get('apellido', persona.apellido)
            persona.dni = request.form.get('dni', persona.dni)
            persona.correo = request.form.get('correo', persona.correo)
            persona.telefono = request.form.get('telefono', persona.telefono)
            
            is_admin_checked = 'is_admin' in request.form
            persona.is_admin = is_admin_checked
            
            if is_admin_checked:
                persona.cargo = request.form.get('cargo', persona.cargo)
            else:
                persona.cargo = None # Clear cargo if not admin            # Update Keycloak user if linked
            if persona.keycloak_user_id and keycloak_admin:
                # Prepare update data - only include email if persona has one
                update_data = {
                    'firstName': persona.nombre,
                    'lastName': persona.apellido,
                    'attributes': {
                        'dni': persona.dni,
                        'telefono': persona.telefono or '',
                        'cargo': persona.cargo or ''
                    }
                }
                
                # Only update email if persona has a valid email (don't overwrite with empty values)
                if persona.correo:
                    update_data['email'] = persona.correo
                
                # Update user attributes in Keycloak
                update_success = keycloak_admin.update_user(
                    persona.keycloak_user_id,
                    update_data
                )
                
                if not update_success:
                    flash('Advertencia: No se pudo actualizar la información en Keycloak.', 'warning')                # Handle admin role changes
                if old_is_admin != is_admin_checked and keycloak_admin:
                    admin_role = KeycloakConfig.KEYCLOAK_ADMIN_ROLE
                    if keycloak_admin.client_role_exists(admin_role):
                        if is_admin_checked:
                            # Assign admin role
                            if not keycloak_admin.assign_client_role(persona.keycloak_user_id, admin_role):
                                flash(f'Advertencia: No se pudo asignar el rol de cliente {admin_role} en Keycloak.', 'warning')
                        else:
                            # Remove admin role
                            if not keycloak_admin.remove_client_role(persona.keycloak_user_id, admin_role):
                                flash(f'Advertencia: No se pudo remover el rol de cliente {admin_role} en Keycloak.', 'warning')
                    else:
                        flash(f'Error: El rol de cliente {admin_role} no existe en Keycloak.', 'danger')
                
                # Ensure tribunal_member role is assigned (in case it wasn't assigned before)
                if keycloak_admin:
                    tribunal_role = KeycloakConfig.KEYCLOAK_TRIBUNAL_ROLE
                    if keycloak_admin.client_role_exists(tribunal_role):
                        if not keycloak_admin.assign_client_role(persona.keycloak_user_id, tribunal_role):
                            # This might fail if role is already assigned, which is fine
                            pass
                    else:
                        logger.error(f"Client role {tribunal_role} does not exist in Keycloak")

            # Handle CV upload
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
            logger.error(f'Error updating persona {persona_id}: {e}')
            flash(f'Error al actualizar la persona: {str(e)}', 'danger')
    
    return render_template('admin/personas/edit_persona.html', persona=persona)

@admin_personas_bp.route('/nueva', methods=['GET', 'POST'])
@keycloak_login_required
@admin_required
def nueva_persona():
    if request.method == 'POST':
        try:
            # Get form data
            nombre = request.form.get('nombre')
            apellido = request.form.get('apellido')
            dni = request.form.get('dni')
            correo = request.form.get('correo')
            telefono = request.form.get('telefono')
            is_admin_checked = 'is_admin' in request.form
            cargo_persona = request.form.get('cargo') if is_admin_checked else None
              # Validate required fields
            if not all([nombre, apellido, dni]):
                flash('Nombre, apellido y DNI son campos obligatorios.', 'danger')
                return render_template('admin/personas/nueva_persona.html')
            
            # Check for duplicate DNI (always unique)
            existing_dni = Persona.query.filter_by(dni=dni).first()
            if existing_dni:
                flash(f'Ya existe una persona con el DNI {dni}.', 'danger')
                return render_template('admin/personas/nueva_persona.html')
            
            # Check for duplicate email if provided (only if not empty)
            if correo and correo.strip():
                existing_email = Persona.query.filter_by(correo=correo).first()
                if existing_email:
                    flash(f'Ya existe una persona con el correo electrónico {correo}.', 'danger')
                    return render_template('admin/personas/nueva_persona.html')
            
            # Check for duplicate username (will use DNI as username)
            username = dni  # Use DNI as username
            existing_username = Persona.query.filter_by(username=username).first()
            if existing_username:
                flash(f'Ya existe una persona con el nombre de usuario {username}.', 'danger')
                return render_template('admin/personas/nueva_persona.html')            # Step 1: Check if user already exists in Keycloak and create if necessary
            # username is already set to dni above
            keycloak_user_id = None
            temporary_password = None
            real_keycloak_data = None  # Will store the real user data from Keycloak
            
            # Check for existing user in Keycloak first by email
            if keycloak_admin:
                # Check if user already exists in Keycloak by email
                existing_keycloak_user = keycloak_admin.get_user_by_email(correo)
                if existing_keycloak_user:
                    keycloak_user_id = existing_keycloak_user['id']
                    real_keycloak_data = existing_keycloak_user
                    logger.info(f"Found existing Keycloak user with email {correo}: {keycloak_user_id}")
                    flash(f'Usuario encontrado en Keycloak con email {correo}. Se utilizarán los datos reales del usuario.', 'info')
                else:
                    # Also check by username (DNI) if different from email
                    existing_keycloak_user = keycloak_admin.get_user_by_username(username)
                    if existing_keycloak_user:
                        keycloak_user_id = existing_keycloak_user['id']
                        real_keycloak_data = existing_keycloak_user
                        logger.info(f"Found existing Keycloak user with username {username}: {keycloak_user_id}")
                        flash(f'Usuario encontrado en Keycloak con DNI {username}. Se utilizarán los datos reales del usuario.', 'info')
                    else:
                        # Create new user in Keycloak
                        temporary_password = secrets.token_urlsafe(12)
                        
                        keycloak_user_id = keycloak_admin.create_user(
                            user_data={
                                'username': username,
                                'email': correo,
                                'firstName': nombre,
                                'lastName': apellido,
                                'attributes': {
                                    'dni': dni,
                                    'telefono': telefono or '',
                                    'cargo': cargo_persona or ''
                                }
                            },
                            temporary_password=temporary_password
                        )
                        
                        if keycloak_user_id:
                            logger.info(f"Created new Keycloak user: {keycloak_user_id}")
                        else:
                            logger.error("Failed to create user in Keycloak")
                            flash('Error: No se pudo crear el usuario en Keycloak. Usuario creado solo localmente.', 'warning')
            
            if not keycloak_user_id:
                logger.warning("Keycloak admin client not available or user creation failed")
                flash('Aviso: Usuario creado localmente, pero no se pudo sincronizar con Keycloak.', 'warning')            # Step 2: Assign roles if user exists in Keycloak
            if keycloak_admin and keycloak_user_id:
                roles_assigned = []
                roles_failed = []
                
                # Assign admin role if checked
                if is_admin_checked:
                    admin_role = KeycloakConfig.KEYCLOAK_ADMIN_ROLE  # 'app_admin'
                    # Check if client role exists first
                    if keycloak_admin.client_role_exists(admin_role):
                        if keycloak_admin.assign_client_role(keycloak_user_id, admin_role):
                            roles_assigned.append(admin_role)
                            logger.info(f"Assigned client role {admin_role} to user {keycloak_user_id}")
                        else:
                            roles_failed.append(admin_role)
                            logger.warning(f"Failed to assign client role {admin_role} to user {keycloak_user_id}")
                    else:
                        roles_failed.append(f"{admin_role} (no existe en cliente)")
                        logger.error(f"Client role {admin_role} does not exist in Keycloak client")
                
                # Always assign tribunal_member role for all new personas
                tribunal_role = KeycloakConfig.KEYCLOAK_TRIBUNAL_ROLE  # 'tribunal_member'
                # Check if client role exists first
                if keycloak_admin.client_role_exists(tribunal_role):
                    if keycloak_admin.assign_client_role(keycloak_user_id, tribunal_role):
                        roles_assigned.append(tribunal_role)
                        logger.info(f"Assigned client role {tribunal_role} to user {keycloak_user_id}")
                    else:
                        roles_failed.append(tribunal_role)
                        logger.warning(f"Failed to assign client role {tribunal_role} to user {keycloak_user_id}")
                else:
                    roles_failed.append(f"{tribunal_role} (no existe en cliente)")
                    logger.error(f"Client role {tribunal_role} does not exist in Keycloak client")
                
                # Report role assignment results
                if roles_assigned:
                    flash(f'Roles de cliente asignados exitosamente: {", ".join(roles_assigned)}', 'success')
                if roles_failed:
                    flash(f'Error al asignar roles de cliente: {", ".join(roles_failed)}', 'warning')
              # Step 3: Create local Persona record
            # Use real Keycloak data if available, otherwise use admin-inputted data
            if real_keycloak_data:
                # Extract real data from Keycloak user
                real_nombre = real_keycloak_data.get('firstName', '') or nombre
                real_apellido = real_keycloak_data.get('lastName', '') or apellido
                real_correo = real_keycloak_data.get('email', '') or correo
                
                # Extract attributes if available
                attributes = real_keycloak_data.get('attributes', {})
                real_telefono = attributes.get('telefono', [None])[0] if 'telefono' in attributes else telefono
                real_dni = attributes.get('dni', [None])[0] if 'dni' in attributes else dni
                
                logger.info(f"Using real Keycloak data for persona creation:")
                logger.info(f"  Real name: {real_nombre} {real_apellido}")
                logger.info(f"  Real email: {real_correo}")
                logger.info(f"  Real telefono: {real_telefono}")
                logger.info(f"  Real DNI: {real_dni}")
                
                flash(f'Utilizando datos reales de Keycloak: {real_nombre} {real_apellido} ({real_correo})', 'info')
            else:
                # Use admin-inputted data for new users
                real_nombre = nombre
                real_apellido = apellido
                real_correo = correo
                real_telefono = telefono
                real_dni = dni
            
            nueva_persona = Persona(
                nombre=real_nombre,
                apellido=real_apellido,
                dni=real_dni,  # Use real DNI from Keycloak if available
                correo=real_correo,
                telefono=real_telefono,
                username=username,
                keycloak_user_id=keycloak_user_id,
                is_admin=is_admin_checked,
                cargo=cargo_persona
            )
            
            db.session.add(nueva_persona)
            
            # Handle CV upload if provided
            cv_file = request.files.get('cv_file')
            if cv_file and cv_file.filename != '':
                if not cv_file.filename.lower().endswith('.pdf'):
                    flash('Solo se permiten archivos PDF para el CV.', 'danger')
                    db.session.rollback()                # Should also clean up Keycloak user here
                if keycloak_admin and keycloak_user_id:
                    keycloak_admin.delete_user(keycloak_user_id)
                    return render_template('admin/personas/nueva_persona.html')

                # First commit the persona to get an ID
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
            else:                db.session.commit()
            
            # Step 4: Persona created successfully (no email sent)
            if keycloak_user_id:
                flash('Persona creada exitosamente y vinculada con usuario de Keycloak.', 'success')
            else:
                flash('Persona creada exitosamente.', 'success')
            
            return redirect(url_for('admin_personas.list_personas'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f'Error creating persona: {e}')
            flash(f'Error al crear la persona: {str(e)}', 'danger')
    
    return render_template('admin/personas/nueva_persona.html')

@admin_personas_bp.route('/<int:persona_id>/cv/eliminar', methods=['POST'])
@keycloak_login_required
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
@keycloak_login_required
@admin_required
def eliminar_persona(persona_id):
    persona = Persona.query.get_or_404(persona_id)
    try:
        # Check if persona has tribunal assignments
        tribunal_assignments = persona.asignaciones.count()
        if tribunal_assignments > 0:
            flash(f'No se puede eliminar la persona "{persona.apellido}, {persona.nombre}" porque tiene {tribunal_assignments} asignación(es) de tribunal. Primero elimine las asignaciones.', 'danger')
            return redirect(url_for('admin_personas.list_personas'))
        
        # Delete CV from Google Drive if it exists
        if persona.cv_drive_file_id:
            try:
                drive_api.delete_file(persona.cv_drive_file_id)
            except Exception as e:
                flash(f'No se pudo eliminar el CV de Drive: {str(e)}', 'warning')        # Remove tribunal_member role from Keycloak user (but keep the user account)
        if persona.keycloak_user_id and keycloak_admin:
            # Safety check: Get current user info to avoid accidentally removing roles from current user
            current_user_info = get_current_user_info()
            current_user_id = current_user_info.get('sub')  # 'sub' is the user ID in Keycloak tokens
            
            logger.info(f"About to remove roles from user ID: {persona.keycloak_user_id} for persona: {persona.apellido}, {persona.nombre}")
            logger.info(f"Current logged-in user ID: {current_user_id}")
            
            # Safety check: Don't remove roles from the current user
            if persona.keycloak_user_id == current_user_id:
                flash('Error: No se puede eliminar una persona que corresponde al usuario actualmente logueado.', 'danger')
                return redirect(url_for('admin_personas.list_personas'))
            
            tribunal_role = KeycloakConfig.KEYCLOAK_TRIBUNAL_ROLE
            if keycloak_admin.client_role_exists(tribunal_role):
                if not keycloak_admin.remove_client_role(persona.keycloak_user_id, tribunal_role):
                    flash(f'Advertencia: No se pudo remover el rol {tribunal_role} del usuario en Keycloak.', 'warning')
                else:
                    flash(f'Rol {tribunal_role} removido exitosamente del usuario en Keycloak.', 'info')
            else:
                flash(f'El rol {tribunal_role} no existe en Keycloak.', 'warning')
            
            # Also remove admin role if the user had it
            if persona.is_admin:
                admin_role = KeycloakConfig.KEYCLOAK_ADMIN_ROLE
                if keycloak_admin.client_role_exists(admin_role):
                    if not keycloak_admin.remove_client_role(persona.keycloak_user_id, admin_role):
                        flash(f'Advertencia: No se pudo remover el rol {admin_role} del usuario en Keycloak.', 'warning')
                    else:
                        flash(f'Rol {admin_role} removido exitosamente del usuario en Keycloak.', 'info')
                else:
                    flash(f'El rol {admin_role} no existe en Keycloak.', 'warning')
        else:
            logger.info(f"No Keycloak user ID found for persona: {persona.apellido}, {persona.nombre} - skipping role removal")
        
        # Store persona info for the success message
        nombre_completo = f"{persona.apellido}, {persona.nombre}"
        
        # Delete the persona from the database
        db.session.delete(persona)
        db.session.commit()
        
        flash(f'Persona "{nombre_completo}" eliminada exitosamente.', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error deleting persona {persona_id}: {e}')
        flash(f'Error al eliminar la persona: {str(e)}', 'danger')
    
    return redirect(url_for('admin_personas.list_personas'))
