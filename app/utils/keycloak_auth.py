"""
Authorization decorators for Keycloak-based authentication.
"""
from functools import wraps
from flask import redirect, url_for, flash, g, request, session
from app.config.keycloak_config import KeycloakConfig


def keycloak_login_required(f):
    """Decorator to require Keycloak authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not g.get('is_authenticated', False):
            # Store the originally requested URL
            session['next_url'] = request.url
            
            # Redirect to login
            from app.integrations.keycloak_oidc import keycloak_oidc
            return keycloak_oidc.login()
        
        return f(*args, **kwargs)
    return decorated_function


def keycloak_role_required(required_role: str):
    """Decorator to require a specific Keycloak role."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not g.get('is_authenticated', False):
                # Store the originally requested URL
                from flask import session
                session['next_url'] = request.url
                
                # Redirect to login
                from app.integrations.keycloak_oidc import keycloak_oidc
                return keycloak_oidc.login()
            
            user_roles = g.get('user_roles', [])
            if required_role not in user_roles:
                flash(f'Acceso no autorizado. Requiere rol: {required_role}', 'danger')
                return redirect(url_for('public.index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    """Decorator to require admin role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not g.get('is_authenticated', False):
            flash('Acceso no autorizado. Debe iniciar sesión.', 'danger')
            from app.integrations.keycloak_oidc import keycloak_oidc
            return keycloak_oidc.login()
        
        user_roles = g.get('user_roles', [])
        if KeycloakConfig.KEYCLOAK_ADMIN_ROLE not in user_roles:
            flash('Acceso no autorizado. Requiere permisos de administrador.', 'danger')
            return redirect(url_for('public.index'))
        
        return f(*args, **kwargs)
    return decorated_function


def tribunal_required(f):
    """Decorator to require tribunal member role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not g.get('is_authenticated', False):
            flash('Acceso no autorizado. Debe iniciar sesión.', 'danger')
            from app.integrations.keycloak_oidc import keycloak_oidc
            return keycloak_oidc.login()
        
        user_roles = g.get('user_roles', [])
        tribunal_role = KeycloakConfig.KEYCLOAK_TRIBUNAL_ROLE
        admin_role = KeycloakConfig.KEYCLOAK_ADMIN_ROLE
        
        # Allow access if user has tribunal role or admin role
        if tribunal_role not in user_roles and admin_role not in user_roles:
            flash('Acceso no autorizado. Requiere permisos de tribunal.', 'danger')
            return redirect(url_for('public.index'))
        
        return f(*args, **kwargs)
    return decorated_function


def get_current_user_info():
    """Get current user information from Keycloak token."""
    return g.get('oidc_user_info', {})


def get_current_user_roles():
    """Get current user roles."""
    return g.get('user_roles', [])


def is_admin():
    """Check if current user is admin."""
    return KeycloakConfig.KEYCLOAK_ADMIN_ROLE in get_current_user_roles()


def is_tribunal_member():
    """Check if current user is tribunal member."""
    user_roles = get_current_user_roles()
    return (KeycloakConfig.KEYCLOAK_TRIBUNAL_ROLE in user_roles or 
            KeycloakConfig.KEYCLOAK_ADMIN_ROLE in user_roles)


def get_current_username():
    """Get current user's username."""
    user_info = get_current_user_info()
    # Try different possible username fields
    return (user_info.get('preferred_username') or 
            user_info.get('sub') or 
            user_info.get('email', '').split('@')[0] or
            'unknown')


def get_current_user_email():
    """Get current user's email."""
    user_info = get_current_user_info()
    return user_info.get('email', '')


def get_current_user_name():
    """Get current user's full name."""
    user_info = get_current_user_info()
    given_name = user_info.get('given_name', '')
    family_name = user_info.get('family_name', '')
    
    if given_name and family_name:
        return f"{given_name} {family_name}"
    elif user_info.get('name'):
        return user_info.get('name')
    else:
        return get_current_username()
