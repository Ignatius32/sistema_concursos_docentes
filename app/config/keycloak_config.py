"""
Keycloak configuration settings for Flask application.
"""
import os
from typing import Optional


class KeycloakConfig:
    """Keycloak configuration class."""
    
    # Keycloak Server Configuration
    _server_url_raw = os.environ.get('KEYCLOAK_SERVER_URL', 'https://huayca.crub.uncoma.edu.ar/keycloak/')
    KEYCLOAK_SERVER_URL: str = _server_url_raw.rstrip('/') + '/'  # Ensure trailing slash
    KEYCLOAK_REALM: str = os.environ.get('KEYCLOAK_REALM', 'CRUB')
    
    # OIDC Client Configuration
    KEYCLOAK_CLIENT_ID: str = os.environ.get('KEYCLOAK_CLIENT_ID', 'flask-client')
    KEYCLOAK_CLIENT_SECRET: str = os.environ.get('KEYCLOAK_CLIENT_SECRET', '')
    
    # Admin API Configuration
    KEYCLOAK_ADMIN_CLIENT_ID: str = os.environ.get('KEYCLOAK_ADMIN_CLIENT_ID', 'flask-admin')
    KEYCLOAK_ADMIN_CLIENT_SECRET: Optional[str] = os.environ.get('KEYCLOAK_ADMIN_CLIENT_SECRET')
    KEYCLOAK_ADMIN_USERNAME: Optional[str] = os.environ.get('KEYCLOAK_ADMIN_USERNAME')
    KEYCLOAK_ADMIN_PASSWORD: Optional[str] = os.environ.get('KEYCLOAK_ADMIN_PASSWORD')    # Application URLs - these can be overridden by environment variables or computed dynamically
    KEYCLOAK_REDIRECT_URI: str = os.environ.get('KEYCLOAK_REDIRECT_URI', 'http://127.0.0.1:5000/auth/callback')
    KEYCLOAK_POST_LOGOUT_REDIRECT_URI: str = os.environ.get('KEYCLOAK_POST_LOGOUT_REDIRECT_URI', 'http://127.0.0.1:5000/')
    
    # Application base path configuration
    APPLICATION_ROOT: str = os.environ.get('APPLICATION_ROOT', '')  # e.g., '/selecciones-docentes' for production
    
    # Password Reset Configuration
    USE_INTERNAL_PASSWORD_RESET: bool = os.environ.get('USE_INTERNAL_PASSWORD_RESET', 'true').lower() == 'true'
    
    # Role Configuration
    KEYCLOAK_ADMIN_ROLE: str = os.environ.get('KEYCLOAK_ADMIN_ROLE', 'app_admin')
    KEYCLOAK_TRIBUNAL_ROLE: str = os.environ.get('KEYCLOAK_TRIBUNAL_ROLE', 'tribunal_member')
    
    @classmethod
    def get_oidc_config(cls) -> dict:
        """Get OIDC configuration dictionary."""
        # Remove trailing slash for URL construction to avoid double slashes
        base_url = cls.KEYCLOAK_SERVER_URL.rstrip('/')
        return {
            'issuer': f"{base_url}/realms/{cls.KEYCLOAK_REALM}",
            'authorization_endpoint': f"{base_url}/realms/{cls.KEYCLOAK_REALM}/protocol/openid-connect/auth",            
            'token_endpoint': f"{base_url}/realms/{cls.KEYCLOAK_REALM}/protocol/openid-connect/token",
            'userinfo_endpoint': f"{base_url}/realms/{cls.KEYCLOAK_REALM}/protocol/openid-connect/userinfo",
            'end_session_endpoint': f"{base_url}/realms/{cls.KEYCLOAK_REALM}/protocol/openid-connect/logout",
            'jwks_uri': f"{base_url}/realms/{cls.KEYCLOAK_REALM}/protocol/openid-connect/certs",
            'introspection_endpoint': f"{base_url}/realms/{cls.KEYCLOAK_REALM}/protocol/openid-connect/token/introspect"
        }
    
    @classmethod
    def get_admin_api_base_url(cls) -> str:
        """Get Keycloak Admin API base URL."""
        base_url = cls.KEYCLOAK_SERVER_URL.rstrip('/')
        return f"{base_url}/admin/realms/{cls.KEYCLOAK_REALM}"
    
    @classmethod
    def validate_oidc_config(cls) -> list[str]:
        """Validate required OIDC configuration only."""
        errors = []
        
        if not cls.KEYCLOAK_SERVER_URL:
            errors.append("KEYCLOAK_SERVER_URL is required")
        
        if not cls.KEYCLOAK_REALM:
            errors.append("KEYCLOAK_REALM is required")
            
        if not cls.KEYCLOAK_CLIENT_ID:
            errors.append("KEYCLOAK_CLIENT_ID is required")
            
        if not cls.KEYCLOAK_CLIENT_SECRET:
            errors.append("KEYCLOAK_CLIENT_SECRET is required")
            
        return errors
    
    @classmethod
    def validate_config(cls) -> list[str]:
        """Validate required configuration and return list of missing/invalid items."""
        errors = []
        
        if not cls.KEYCLOAK_SERVER_URL:
            errors.append("KEYCLOAK_SERVER_URL is required")
        
        if not cls.KEYCLOAK_REALM:
            errors.append("KEYCLOAK_REALM is required")
            
        if not cls.KEYCLOAK_CLIENT_ID:
            errors.append("KEYCLOAK_CLIENT_ID is required")
            
        if not cls.KEYCLOAK_CLIENT_SECRET:
            errors.append("KEYCLOAK_CLIENT_SECRET is required")
              # Admin API validation - at least one method should be configured
        has_client_credentials = cls.KEYCLOAK_ADMIN_CLIENT_SECRET is not None
        has_user_credentials = cls.KEYCLOAK_ADMIN_USERNAME and cls.KEYCLOAK_ADMIN_PASSWORD
        
        if not (has_client_credentials or has_user_credentials):
            errors.append("Either KEYCLOAK_ADMIN_CLIENT_SECRET or (KEYCLOAK_ADMIN_USERNAME + KEYCLOAK_ADMIN_PASSWORD) must be configured for Admin API access")
        
        return errors
    
    @classmethod
    def get_dynamic_redirect_uri(cls, request=None) -> str:
        """
        Get the callback redirect URI dynamically based on the current request.
        This handles both local development and production with base paths.
        """
        # If explicitly set in environment, use that
        redirect_uri = os.environ.get('KEYCLOAK_REDIRECT_URI')
        if redirect_uri:
            return redirect_uri
        
        # Otherwise, build it dynamically from Flask request
        if request is None:
            from flask import request as flask_request
            request = flask_request
        
        if request:
            # Build the base URL from the request
            scheme = request.scheme
            host = request.host
            
            # Get application root from environment or Flask config
            root_path = cls.APPLICATION_ROOT.strip('/') or os.environ.get('APPLICATION_ROOT', '').strip('/')
            if root_path:
                base_url = f"{scheme}://{host}/{root_path}"
            else:
                base_url = f"{scheme}://{host}"
            
            return f"{base_url}/auth/callback"
          # Fallback to configured default with APPLICATION_ROOT
        root_path = cls.APPLICATION_ROOT.strip('/') or os.environ.get('APPLICATION_ROOT', '').strip('/')
        if root_path:
            # For production fallback, assume HTTPS and construct with APPLICATION_ROOT
            return f"https://{os.environ.get('PRODUCTION_HOST', 'your-domain.com')}/{root_path}/auth/callback"
        
        return cls.KEYCLOAK_REDIRECT_URI
    
    @classmethod
    def get_dynamic_post_logout_redirect_uri(cls, request=None) -> str:
        """
        Get the post-logout redirect URI dynamically based on the current request.
        This handles both local development and production with base paths.
        """
        # If explicitly set in environment, use that
        post_logout_uri = os.environ.get('KEYCLOAK_POST_LOGOUT_REDIRECT_URI')
        if post_logout_uri:
            return post_logout_uri
        
        # Otherwise, build it dynamically from Flask request
        if request is None:
            from flask import request as flask_request
            request = flask_request
        
        if request:
            # Build the base URL from the request
            scheme = request.scheme
            host = request.host
            
            # Get application root from environment or Flask config
            root_path = cls.APPLICATION_ROOT.strip('/') or os.environ.get('APPLICATION_ROOT', '').strip('/')
            if root_path:
                base_url = f"{scheme}://{host}/{root_path}"
            else:
                base_url = f"{scheme}://{host}"
            
            return f"{base_url}/"
        
        # Fallback to configured default with APPLICATION_ROOT
        root_path = cls.APPLICATION_ROOT.strip('/') or os.environ.get('APPLICATION_ROOT', '').strip('/')
        if root_path:
            # For production fallback, assume HTTPS and construct with APPLICATION_ROOT
            return f"https://{os.environ.get('PRODUCTION_HOST', 'your-domain.com')}/{root_path}/"
        
        return cls.KEYCLOAK_POST_LOGOUT_REDIRECT_URI
