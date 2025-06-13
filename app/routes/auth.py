from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from app.models.models import Persona, db, TribunalMiembro
from app.integrations.keycloak_oidc import keycloak_oidc
from app.integrations.keycloak_admin_client import get_keycloak_admin
from app.utils.keycloak_auth import get_current_user_info, is_admin, keycloak_login_required, get_current_user_roles
from app.config.keycloak_config import KeycloakConfig
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
        
        if username and password:
            # Direct authentication using username/password
            if keycloak_oidc.direct_authenticate(username, password):
                # Get user info from Keycloak
                user_info = get_current_user_info()
                
                if user_info:
                    # Sync with local Persona model
                    persona = sync_keycloak_user_with_persona(user_info)
                      # Check for next URL and redirect appropriately
                    next_url = session.pop('next_url', None)
                    if next_url:
                        return redirect(next_url)
                    
                    # Redirect based on user role
                    return redirect(get_post_login_redirect())
                else:
                    flash('Error al obtener información del usuario.', 'danger')
            else:
                flash('Usuario o contraseña incorrectos.', 'danger')
        
        # Check if user wants Keycloak OIDC flow
        elif request.form.get('keycloak') == 'true':
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
    """Handle password reset requests."""
    if request.method == 'POST':
        username_or_email = request.form.get('username_or_email', '').strip()
        
        if not username_or_email:
            flash('Por favor ingrese su usuario o correo electrónico.', 'danger')
            return render_template('auth/reset_password.html')
        
        # Initiate password reset via Keycloak
        result = keycloak_oidc.reset_password(username_or_email)
        
        if result['success']:
            flash(result['message'], 'success')
            return redirect(url_for('auth.login'))
        else:
            flash(result['message'], 'danger')
    
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
            # Create new persona if not found
            # Note: For admin users, they should be created through admin interface
            # This is mainly for tribunal members who might be created on-the-fly
            if email and username:
                persona = Persona(
                    keycloak_user_id=keycloak_user_id,
                    correo=email,
                    username=username,
                    nombre=first_name,
                    apellido=last_name,
                    dni=username,  # Assuming username is DNI, adjust as needed
                    is_admin=False  # Will be set through role assignment
                )
                db.session.add(persona)
                logger.info(f"Created new persona for Keycloak user {keycloak_user_id}")
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
        
        # Update ultimo_acceso
        persona.ultimo_acceso = datetime.utcnow()
        
        # Check if user has admin role in Keycloak
        roles = keycloak_user_info.get('realm_access', {}).get('roles', [])
        persona.is_admin = 'app_admin' in roles
        
        db.session.commit()
        return persona
        
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