"""
Keycloak OIDC client integration for Flask application.
"""
import logging
from typing import Optional, Dict, Any
from urllib.parse import urlencode
from flask import Flask, session, request, redirect, url_for, g
from authlib.integrations.flask_client import OAuth
from authlib.integrations.base_client.errors import OAuthError
from app.config.keycloak_config import KeycloakConfig

logger = logging.getLogger(__name__)


class KeycloakOIDCClient:
    """Keycloak OIDC client for Flask application."""
    
    def __init__(self, app: Optional[Flask] = None):
        self.oauth = OAuth()
        self.keycloak_client = None
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Initialize the Keycloak OIDC client with Flask app."""
        
        # Validate Keycloak OIDC configuration
        config_errors = KeycloakConfig.validate_oidc_config()
        if config_errors:
            logger.error(f"Keycloak OIDC configuration errors: {config_errors}")
            raise ValueError(f"Invalid Keycloak configuration: {', '.join(config_errors)}")
        
        # Initialize OAuth with Flask app
        self.oauth.init_app(app)
        
        # Register Keycloak client with manual endpoint configuration
        oidc_config = KeycloakConfig.get_oidc_config()
        self.keycloak_client = self.oauth.register(
            name='keycloak',
            client_id=KeycloakConfig.KEYCLOAK_CLIENT_ID,
            client_secret=KeycloakConfig.KEYCLOAK_CLIENT_SECRET,
            authorize_url=oidc_config['authorization_endpoint'],
            access_token_url=oidc_config['token_endpoint'],
            userinfo_endpoint=oidc_config['userinfo_endpoint'],
            jwks_uri=oidc_config['jwks_uri'],
            client_kwargs={
                'scope': 'openid email profile'
            }
        )
        
        # Store reference to the client in app context
        app.keycloak_oidc = self
        
        # Add before_request handler to load user info
        app.before_request(self._load_user_info)
        
        logger.info("Keycloak OIDC client initialized successfully")
    
    def _load_user_info(self):
        """Load user information from token if available."""
        g.oidc_user_info = None
        g.user_roles = []
        g.is_authenticated = False
        
        # Check if we have tokens in session
        token = session.get('keycloak_token')
        if not token:
            return
        
        try:
            # Get user info from the userinfo endpoint
            user_info = self._get_user_info_from_token(token)
            if user_info:
                g.oidc_user_info = user_info
                g.user_roles = []  # Temporarily empty - will fix role extraction later
                g.is_authenticated = True
                logger.info(f"User authenticated: {user_info.get('preferred_username', 'unknown')}")
                
        except Exception as e:
            logger.warning(f"Failed to load user info: {e}")
            # Clear invalid token
            session.pop('keycloak_token', None)
    
    def _get_user_info_from_token(self, token: dict) -> Optional[Dict[str, Any]]:
        """Get user information using the access token and userinfo endpoint."""
        try:
            access_token = token.get('access_token')
            if not access_token:
                return None
            
            # Use the userinfo endpoint to get user information
            import requests
            userinfo_url = KeycloakConfig.get_oidc_config()['userinfo_endpoint']
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(userinfo_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Failed to get user info from token: {e}")
            return None

    def login(self, redirect_uri: Optional[str] = None) -> str:
        """Initiate OIDC login flow."""
        if not redirect_uri:
            redirect_uri = KeycloakConfig.KEYCLOAK_REDIRECT_URI
        
        return self.keycloak_client.authorize_redirect(redirect_uri)
    
    def handle_callback(self):
        """Handle OIDC callback and exchange code for tokens."""
        try:
            # Exchange authorization code for tokens
            token = self.keycloak_client.authorize_access_token()
            
            # Store tokens in session
            session['keycloak_token'] = token
            session.permanent = True
            
            logger.info("User successfully authenticated via Keycloak")
            return True
            
        except OAuthError as e:
            logger.error(f"OAuth error during callback: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during callback: {e}")
            return False
    
    def callback(self):
        """Handle callback (wrapper for handle_callback for compatibility)."""
        return self.handle_callback()
        
    def logout(self, post_logout_redirect_uri: Optional[str] = None):
        """Logout user from Keycloak and clear session."""
        
        # Get ID token for logout
        token = session.get('keycloak_token', {})
        id_token = token.get('id_token')
        
        # Clear local session
        session.clear()
        
        # Build Keycloak logout URL
        if not post_logout_redirect_uri:
            post_logout_redirect_uri = KeycloakConfig.KEYCLOAK_POST_LOGOUT_REDIRECT_URI
        
        logout_params = {
            'post_logout_redirect_uri': post_logout_redirect_uri
        }
        
        if id_token:
            logout_params['id_token_hint'] = id_token
        
        logout_url = f"{KeycloakConfig.get_oidc_config()['end_session_endpoint']}?{urlencode(logout_params)}"
        
        return redirect(logout_url)
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated."""
        return g.get('is_authenticated', False)
    
    def get_user_info(self) -> Optional[Dict[str, Any]]:
        """Get current user information."""
        return g.get('oidc_user_info')
    
    def get_user_roles(self) -> list[str]:
        """Get current user roles."""
        return g.get('user_roles', [])
    
    def has_role(self, role: str) -> bool:
        """Check if current user has specific role."""
        return role in self.get_user_roles()
    
    def before_request(self):
        """Manually trigger user info loading (for compatibility)."""
        self._load_user_info()


# Global instance
keycloak_oidc = KeycloakOIDCClient()
