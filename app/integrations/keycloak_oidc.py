"""
Keycloak OIDC client integration for Flask application.
"""
import logging
import requests
import jwt
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
                g.user_roles = self._extract_roles_from_token(token)  # Extract roles from token
                g.is_authenticated = True
                logger.info(f"User authenticated: {user_info.get('preferred_username', 'unknown')} with roles: {g.user_roles}")
                
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

    def _extract_roles_from_token(self, token: dict) -> list[str]:
        """Extract roles from access token."""
        try:
            access_token = token.get('access_token')
            if not access_token:
                return []            # Decode JWT token to get roles
            
            # Get JWT header to determine key id
            unverified_header = jwt.get_unverified_header(access_token)
            kid = unverified_header.get('kid')
            
            if not kid:
                logger.warning("No key ID found in JWT header")
                return []
            
            # Get public keys from JWKS endpoint
            jwks_uri = KeycloakConfig.get_oidc_config()['jwks_uri']
            response = requests.get(jwks_uri, timeout=10)
            response.raise_for_status()
            jwks = response.json()
            
            # Find the correct key
            public_key = None
            for key in jwks.get('keys', []):
                if key.get('kid') == kid:
                    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
                    break
            
            if not public_key:
                logger.warning(f"No public key found for kid: {kid}")
                return []              # Decode and verify the token (skip audience and issuer validation for now)
            decoded_token = jwt.decode(
                access_token, 
                public_key, 
                algorithms=['RS256'],
                options={
                    "verify_aud": False,  # Skip audience validation
                    "verify_iss": False   # Skip issuer validation for now
                }
            )
              # Extract roles from different possible locations
            roles = []
            
            # Check realm_access roles
            realm_access = decoded_token.get('realm_access', {})
            realm_roles = realm_access.get('roles', [])
            roles.extend(realm_roles)
            logger.info(f"Realm roles found: {realm_roles}")
            
            # Check resource_access roles for our client
            resource_access = decoded_token.get('resource_access', {})
            client_roles = resource_access.get(KeycloakConfig.KEYCLOAK_CLIENT_ID, {})
            client_role_list = client_roles.get('roles', [])
            roles.extend(client_role_list)
            logger.info(f"Client roles found: {client_role_list}")
            
            # Also check for account client roles (common in Keycloak)
            account_roles = resource_access.get('account', {})
            account_role_list = account_roles.get('roles', [])
            roles.extend(account_role_list)
            logger.info(f"Account roles found: {account_role_list}")
            
            logger.info(f"All extracted roles from token: {roles}")
            return roles
            
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token has expired")
            return []
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            return []
        except Exception as e:
            logger.error(f"Failed to extract roles from token: {e}")
            return []

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
              # Debug: log what tokens we received
            logger.info(f"Tokens received: {list(token.keys()) if token else 'None'}")
            if 'id_token' in token:
                logger.info("ID token present for logout")
            else:
                logger.warning("No ID token received - logout might have issues")
            
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
        """Simple local logout - clear session and redirect to login page."""
        
        # Clear all session data
        session.clear()
        
        # Set default redirect URI if not provided
        if not post_logout_redirect_uri:
            post_logout_redirect_uri = KeycloakConfig.KEYCLOAK_POST_LOGOUT_REDIRECT_URI
        
        logger.info("Performing local logout (session cleared)")
        
        # Direct redirect to the post-logout URI without going through Keycloak
        return redirect(post_logout_redirect_uri)
    
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

    def direct_authenticate(self, username: str, password: str) -> bool:
        """
        Authenticate user directly with username/password using Keycloak's token endpoint.
        This uses the Resource Owner Password Credentials (ROPC) flow.
        """
        try:
            # Get token endpoint from OIDC configuration
            oidc_config = KeycloakConfig.get_oidc_config()
            token_endpoint = oidc_config['token_endpoint']
            
            # Prepare the token request
            token_data = {
                'grant_type': 'password',
                'client_id': KeycloakConfig.KEYCLOAK_CLIENT_ID,
                'client_secret': KeycloakConfig.KEYCLOAK_CLIENT_SECRET,
                'username': username,
                'password': password,
                'scope': 'openid email profile'
            }
            
            # Make the token request
            response = requests.post(
                token_endpoint,
                data=token_data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=10
            )
            
            if response.status_code == 200:
                token = response.json()
                
                # Store token in session
                session['keycloak_token'] = token
                
                # Log successful authentication
                logger.info(f"User {username} authenticated successfully via direct login")
                
                # Load user info
                self._load_user_info()
                
                return True
            else:
                # Log authentication failure
                logger.warning(f"Authentication failed for user {username}: {response.status_code}")
                if response.status_code == 401:
                    logger.info("Invalid username or password")
                else:
                    logger.error(f"Token endpoint error: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error during direct authentication: {e}")
            return False

    def reset_password(self, username_or_email: str) -> Dict[str, Any]:
        """
        Initiate password reset for a user via Keycloak admin API.
        Returns a dict with success status and message.
        """
        try:
            # Get admin client
            from app.integrations.keycloak_admin_client import get_keycloak_admin
            admin_client = get_keycloak_admin()
            
            if not admin_client:
                return {
                    'success': False,
                    'message': 'El servicio de restablecimiento de contraseña no está disponible en este momento.'
                }
            
            # Try to find user by username first, then by email
            user = None
            
            # Check if input looks like an email
            if '@' in username_or_email:
                user = admin_client.get_user_by_email(username_or_email)
                user_identifier = f"email {username_or_email}"
            else:
                user = admin_client.get_user_by_username(username_or_email)
                user_identifier = f"username {username_or_email}"
            
            if not user:
                # For security reasons, don't reveal if user exists or not
                logger.info(f"Password reset requested for non-existent user: {username_or_email}")
                return {
                    'success': True,
                    'message': 'Si el usuario existe, se ha enviado un correo con instrucciones para restablecer la contraseña.'
                }
            
            # Send password reset email via Keycloak
            user_id = user.get('id')
            if admin_client.send_execute_actions_email(user_id, ['UPDATE_PASSWORD']):
                logger.info(f"Password reset email sent successfully for user: {user_identifier}")
                return {
                    'success': True,
                    'message': 'Se ha enviado un correo con instrucciones para restablecer la contraseña.'
                }
            else:
                logger.error(f"Failed to send password reset email for user: {user_identifier}")
                return {
                    'success': False,
                    'message': 'Error al enviar el correo de restablecimiento. Intente nuevamente más tarde.'
                }
                
        except Exception as e:
            logger.error(f"Error during password reset request: {e}")
            return {
                'success': False,
                'message': 'Error interno del sistema. Contacte al administrador.'
            }


# Global instance
keycloak_oidc = KeycloakOIDCClient()
