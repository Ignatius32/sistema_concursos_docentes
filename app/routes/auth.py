from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from app.models.models import Persona, db, TribunalMiembro
from app.integrations.keycloak_oidc import keycloak_oidc
from app.integrations.keycloak_admin_client import get_keycloak_admin, KeycloakAdminClient
from app.utils.keycloak_auth import get_current_user_info, is_admin, keycloak_login_required, get_current_user_roles
from app.config.keycloak_config import KeycloakConfig
from app.services.password_reset_service import password_reset_service
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
auth = Blueprint('auth', __name__, url_prefix='/auth')

@auth.route('/login', methods=['GET', 'POST'])
def login():
    """
    Main login route - handles both direct form and Keycloak OIDC authentication
    """
    # Check if already authenticated via Keycloak
    if keycloak_oidc.is_authenticated():
        return redirect(url_for('concursos.index'))
    
    # Store the next URL in session for after login
    next_url = request.args.get('next')
    if next_url:
        session['next_url'] = next_url
    
    if request.method == 'POST':
        # Check if this is a direct form login
        username = request.form.get('username')
        password = request.form.get('password')
        
        logger.info(f"Login attempt for username: {username}")
        
        if username and password:
            # Direct authentication using username/password
            logger.info("Attempting direct authentication via Keycloak")
            if keycloak_oidc.direct_authenticate(username, password):
                logger.info("Direct authentication successful")
                # Get user info from Keycloak
                user_info = get_current_user_info()
                
                if user_info:
                    logger.info(f"Got user info: {user_info.get('preferred_username')}")
                    # Sync with local Persona model
                    persona = sync_keycloak_user_with_persona(user_info)
                    
                    if persona:
                        logger.info(f"Synced with persona ID: {persona.id}")
                    else:
                        logger.warning("Failed to sync with persona")
                  # Check for next URL and redirect appropriately
                    next_url = session.pop('next_url', None)
                    if next_url:
                        logger.info(f"Redirecting to next URL: {next_url}")
                        return redirect(next_url)
                    
                    # Redirect based on user role
                    redirect_url = get_post_login_redirect()
                    logger.info(f"Redirecting to: {redirect_url}")
                    return redirect(redirect_url)
                else:
                    logger.error("No user info received after authentication")
                    flash('Error al obtener información del usuario.', 'danger')
            else:
                logger.warning(f"Direct authentication failed for user: {username}")
                flash('Usuario o contraseña incorrectos.', 'danger')
        
        # Check if user wants Keycloak OIDC flow
        elif request.form.get('keycloak') == 'true':
            logger.info("Initiating Keycloak OIDC flow")
            return keycloak_oidc.login()
    
    # For GET requests or failed authentication, show login page
    return render_template('auth/login.html')


@auth.route('/keycloak-login')
def keycloak_login():
    """Initiate Keycloak OIDC login flow."""
    return keycloak_oidc.login()


@auth.route('/callback')
def callback():
    """Handle Keycloak OIDC callback."""
    try:
        if keycloak_oidc.handle_callback():
            # Get user info from Keycloak
            user_info = get_current_user_info()
            
            if user_info:
                # Sync with local Persona model
                persona = sync_keycloak_user_with_persona(user_info)
                
                if persona:
                    logger.info(f"User {user_info.get('preferred_username')} logged in successfully")
                    flash('Sesión iniciada exitosamente.', 'success')
                else:
                    logger.warning(f"Failed to sync user {user_info.get('preferred_username')} with local database")
                    flash('Sesión iniciada, pero hubo un problema al sincronizar con la base de datos.', 'warning')
              # Redirect to next page or appropriate portal based on role
            next_url = session.pop('next_url', None)
            if next_url:
                return redirect(next_url)
            else:
                return redirect(get_post_login_redirect())
        else:
            flash('Error durante la autenticación. Intente nuevamente.', 'danger')
            return redirect(url_for('auth.login'))
    
    except Exception as e:
        logger.error(f"Error in OIDC callback: {e}")
        flash('Error durante la autenticación. Intente nuevamente.', 'danger')
        return redirect(url_for('auth.login'))

@auth.route('/logout')
def logout():
    """Handle logout - always use Keycloak logout now."""
    # Clear any local session data
    session.clear()
    
    # Check if user is authenticated via Keycloak
    if keycloak_oidc.is_authenticated():
        # Logout from Keycloak (this will redirect to Keycloak's logout endpoint)
        return keycloak_oidc.logout()
    else:
        # If not authenticated via Keycloak, just redirect to login
        flash('Sesión cerrada exitosamente.', 'info')
        return redirect(url_for('auth.login'))

@auth.route('/debug')
def debug_auth():
    """Debug route to check authentication status"""
    from flask import g
    from app.utils.keycloak_auth import get_current_user_info, get_current_user_roles, is_admin
    
    # Get authentication info
    user_info = get_current_user_info()
    user_roles = get_current_user_roles()
    is_authenticated = g.get('is_authenticated', False)
    admin_status = is_admin()
    
    debug_info = {
        'is_authenticated': is_authenticated,
        'user_info': user_info,
        'user_roles': user_roles,
        'is_admin': admin_status,
        'g_user_roles': g.get('user_roles', []),
        'g_is_authenticated': g.get('is_authenticated', False),
        'session_token_present': 'keycloak_token' in session,
        'session_keys': list(session.keys()) if session else []
    }
    
    return f"""
    <h1>Keycloak Authentication Debug</h1>
    <pre style="background: #f5f5f5; padding: 10px; border-radius: 5px;">
{debug_info}
    </pre>
    
    <h2>Template Context Variables:</h2>
    <p><strong>keycloak_is_authenticated:</strong> {is_authenticated}</p>
    <p><strong>keycloak_is_admin:</strong> {admin_status}</p>
    <p><strong>keycloak_user_roles:</strong> {user_roles}</p>
    
    <h2>Expected Admin Role:</h2>
    <p><strong>KEYCLOAK_ADMIN_ROLE:</strong> app_admin</p>
    
    <hr>
    <a href="/">Back to Home</a> | 
    <a href="/auth/login">Login</a> | 
    <a href="/auth/logout">Logout</a>
    """

@auth.route('/clear-session')
def clear_session():
    """Clear the session for debugging"""
    session.clear()
    flash('Session cleared. Please login again.', 'info')
    return redirect(url_for('auth.login'))

@auth.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    """Handle password reset requests using Drive-based system."""
    if request.method == 'POST':
        username_or_email = request.form.get('username_or_email', '').strip()
        
        if not username_or_email:
            flash('Por favor ingrese su usuario o correo electrónico.', 'danger')
            return render_template('auth/reset_password.html')
        
        try:
            # Initialize Keycloak admin client
            keycloak_admin = KeycloakAdminClient()
            
            # Try to find user by email first, then by username
            keycloak_user = None
            persona = None
            
            # Check if input looks like an email
            if '@' in username_or_email:
                # Try to find by email in Keycloak
                keycloak_user = keycloak_admin.get_user_by_email(username_or_email)
                if keycloak_user:
                    # Find corresponding persona
                    persona = Persona.query.filter_by(correo=username_or_email).first()
            else:
                # Try to find persona by DNI/username first
                persona = Persona.query.filter(
                    (Persona.dni == username_or_email) | 
                    (Persona.username == username_or_email)
                ).first()
                
                if persona and persona.correo:
                    # Find corresponding Keycloak user
                    keycloak_user = keycloak_admin.get_user_by_email(persona.correo)
            
            if not persona or not keycloak_user:
                # Don't reveal whether user exists or not for security
                flash('Si el usuario existe en el sistema, recibirá un correo con instrucciones para restablecer su contraseña.', 'info')
                return render_template('auth/reset_password.html')
              # Use the Drive-based password reset email system
            success = password_reset_service.send_password_reset_email(persona, keycloak_user['id'])
            
            if success:
                flash('Si el usuario existe en el sistema, recibirá un correo con instrucciones para restablecer su contraseña.', 'success')
            else:
                flash('Si el usuario existe en el sistema, recibirá un correo con instrucciones para restablecer su contraseña.', 'info')
            
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            logger.error(f"Error in password reset: {e}")
            # Don't reveal specific error details to user
            flash('Si el usuario existe en el sistema, recibirá un correo con instrucciones para restablecer su contraseña.', 'info')
    
    return render_template('auth/reset_password.html')

def sync_keycloak_user_with_persona(keycloak_user_info):
    """
    Sync Keycloak user information with local Persona model.
    Creates or updates local Persona record based on Keycloak user data.
    """
    try:
        keycloak_user_id = keycloak_user_info.get('sub')  # Keycloak user ID
        email = keycloak_user_info.get('email')
        username = keycloak_user_info.get('preferred_username')
        first_name = keycloak_user_info.get('given_name', '')
        last_name = keycloak_user_info.get('family_name', '')
        
        if not keycloak_user_id:
            logger.error("No Keycloak user ID found in user info")
            return None
        
        # First, try to find existing Persona by keycloak_user_id
        persona = Persona.query.filter_by(keycloak_user_id=keycloak_user_id).first()
        
        if not persona and email:
            # If not found by keycloak_user_id, try to find by email for migration
            persona = Persona.query.filter_by(correo=email).first()
            if persona:
                # Link existing persona to Keycloak user
                persona.keycloak_user_id = keycloak_user_id
                logger.info(f"Linked existing persona {persona.id} to Keycloak user {keycloak_user_id}")
        
        if not persona:
            # Check if user has admin role or tribunal_member role
            # Use token directly instead of userinfo for more complete role information
            from flask import session
            token_roles = {}
            token_realm_roles = []
            
            # Try to get roles from the raw token if available
            if 'keycloak_token' in session:
                try:
                    import jwt
                    token = session['keycloak_token']['access_token']
                    decoded = jwt.decode(token, options={"verify_signature": False})
                    token_realm_roles = decoded.get('realm_access', {}).get('roles', [])
                    token_roles = decoded.get('resource_access', {})
                    logger.info(f"Debug - Token realm roles: {token_realm_roles}")
                    logger.info(f"Debug - Token resource_access: {token_roles}")
                except Exception as e:
                    logger.warning(f"Could not decode token for role extraction: {e}")
            
            # Fallback to userinfo if token parsing failed
            if not token_roles:
                roles = keycloak_user_info.get('realm_access', {}).get('roles', [])
                client_roles = keycloak_user_info.get('resource_access', {}).get(
                    KeycloakConfig.KEYCLOAK_CLIENT_ID, {}
                ).get('roles', [])
                logger.info(f"Debug - Using userinfo - Realm roles: {roles}")
                logger.info(f"Debug - Using userinfo - Client roles for {KeycloakConfig.KEYCLOAK_CLIENT_ID}: {client_roles}")
            else:
                # Use token data
                roles = token_realm_roles
                client_roles = token_roles.get(KeycloakConfig.KEYCLOAK_CLIENT_ID, {}).get('roles', [])
                logger.info(f"Debug - Using token - Realm roles: {roles}")
                logger.info(f"Debug - Using token - Client roles for {KeycloakConfig.KEYCLOAK_CLIENT_ID}: {client_roles}")
            
            # Check if user has tribunal_member role in the specific client
            has_tribunal_role = KeycloakConfig.KEYCLOAK_TRIBUNAL_ROLE in client_roles
            
            # Check if user has admin role in the specific client or realm roles
            has_admin_role = (KeycloakConfig.KEYCLOAK_ADMIN_ROLE in roles or 
                             KeycloakConfig.KEYCLOAK_ADMIN_ROLE in client_roles)
            
            logger.info(f"Debug - has_tribunal_role: {has_tribunal_role}")
            logger.info(f"Debug - has_admin_role: {has_admin_role}")
            logger.info(f"Debug - Checking ONLY client {KeycloakConfig.KEYCLOAK_CLIENT_ID} for roles")
            
            if (has_tribunal_role or has_admin_role) and email and username:
                # Validate for duplicates before creating
                validation_errors = []
                
                # Check for duplicate DNI
                existing_dni = Persona.query.filter_by(dni=username).first()
                if existing_dni:
                    validation_errors.append(f"DNI {username} already exists")
                
                # Check for duplicate email
                existing_email = Persona.query.filter_by(correo=email).first()
                if existing_email:
                    validation_errors.append(f"Email {email} already exists")
                
                # Check for duplicate username
                existing_username = Persona.query.filter_by(username=username).first()
                if existing_username:
                    validation_errors.append(f"Username {username} already exists")
                
                # Only create if no duplicates found
                if not validation_errors:
                    persona = Persona(
                        keycloak_user_id=keycloak_user_id,
                        correo=email,
                        username=username,
                        nombre=first_name,
                        apellido=last_name,
                        dni=username,  # Assuming username is DNI, adjust as needed
                        is_admin=has_admin_role  # Set admin status based on roles
                    )
                    db.session.add(persona)
                    if has_admin_role:
                        logger.info(f"Created new persona for admin user {keycloak_user_id}")
                    else:
                        logger.info(f"Created new persona for tribunal member {keycloak_user_id}")
                else:
                    logger.warning(f"Cannot create persona for {keycloak_user_id}: {'; '.join(validation_errors)}")
            else:
                # Don't create personas for users without admin or tribunal_member role
                logger.info(f"User {keycloak_user_id} does not have admin or tribunal_member role - no persona created")
                return None
        else:
            # Update existing persona with current Keycloak data
            if email and persona.correo != email:
                persona.correo = email
            if username and persona.username != username:
                persona.username = username
            if first_name and persona.nombre != first_name:
                persona.nombre = first_name
            if last_name and persona.apellido != last_name:
                persona.apellido = last_name
            
            logger.info(f"Updated persona {persona.id} with Keycloak data")
        
        # Update ultimo_acceso only if persona exists
        if persona:
            persona.ultimo_acceso = datetime.utcnow()
            
            # Check if user has admin role in Keycloak (use token for accurate role info)
            from flask import session
            token_roles = {}
            token_realm_roles = []
            
            # Try to get roles from the raw token if available
            if 'keycloak_token' in session:
                try:
                    import jwt
                    token = session['keycloak_token']['access_token']
                    decoded = jwt.decode(token, options={"verify_signature": False})
                    token_realm_roles = decoded.get('realm_access', {}).get('roles', [])
                    token_roles = decoded.get('resource_access', {})
                except Exception as e:
                    logger.warning(f"Could not decode token for admin role check: {e}")
            
            # Use token data if available, otherwise fall back to userinfo
            if token_roles:
                roles = token_realm_roles
                client_roles = token_roles.get(KeycloakConfig.KEYCLOAK_CLIENT_ID, {}).get('roles', [])
            else:
                roles = keycloak_user_info.get('realm_access', {}).get('roles', [])
                client_roles = keycloak_user_info.get('resource_access', {}).get(
                    KeycloakConfig.KEYCLOAK_CLIENT_ID, {}
                ).get('roles', [])
            
            # Check admin role in realm or the specific client only
            has_admin_role_final = (KeycloakConfig.KEYCLOAK_ADMIN_ROLE in roles or 
                                   KeycloakConfig.KEYCLOAK_ADMIN_ROLE in client_roles)
            
            persona.is_admin = has_admin_role_final
            
            db.session.commit()
            return persona
        else:
            return None
        
    except Exception as e:
        logger.error(f"Error syncing Keycloak user with persona: {e}")
        db.session.rollback()
        return None

def get_post_login_redirect():
    """Determine where to redirect user after login based on their roles."""
    user_roles = get_current_user_roles()
    
    # Check for admin role first
    if KeycloakConfig.KEYCLOAK_ADMIN_ROLE in user_roles:
        return url_for('concursos.index')  # Admin goes to admin concursos page
    
    # Check for tribunal role
    elif KeycloakConfig.KEYCLOAK_TRIBUNAL_ROLE in user_roles:
        # Get current user info to sync with Persona and set up tribunal session
        user_info = get_current_user_info()
        if user_info:
            persona = sync_keycloak_user_with_persona(user_info)
            if persona:
                # Set up tribunal session
                session['persona_id'] = persona.id
                
                # Find the most recent tribunal assignment
                miembro = TribunalMiembro.query.filter_by(persona_id=persona.id).order_by(TribunalMiembro.id.desc()).first()
                if miembro:
                    session['tribunal_miembro_id'] = miembro.id
                    session['tribunal_rol'] = miembro.rol
                
                return url_for('tribunal.portal')  # Tribunal member goes to tribunal portal
        
        # Fallback if sync failed
        flash('Error al configurar sesión de tribunal. Contacte al administrador.', 'warning')
        return url_for('auth.login')
    
    # Default redirect for users without specific roles
    else:
        flash('No tiene permisos asignados en el sistema. Contacte al administrador.', 'warning')
        return url_for('auth.login')