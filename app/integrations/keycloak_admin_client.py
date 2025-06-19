"""
Keycloak Admin API client for user management operations.
"""
import logging
from typing import Optional, Dict, Any, List
from keycloak import KeycloakAdmin, KeycloakOpenIDConnection
from keycloak.exceptions import KeycloakError
from app.config.keycloak_config import KeycloakConfig

logger = logging.getLogger(__name__)


class KeycloakAdminClient:
    """Keycloak Admin API client for managing users and roles."""
    
    def __init__(self):
        self._admin_client = None
        self._initialize_client()
        
    def _initialize_client(self):
        """Initialize the Keycloak admin client using client credentials."""
        try:
            logger.info(f"Initializing Keycloak admin client with:")
            logger.info(f"Server URL: {KeycloakConfig.KEYCLOAK_SERVER_URL}")
            logger.info(f"Realm: {KeycloakConfig.KEYCLOAK_REALM}")
            logger.info(f"Client ID: {KeycloakConfig.KEYCLOAK_ADMIN_CLIENT_ID}")
            
            # Use client credentials for service account authentication
            keycloak_connection = KeycloakOpenIDConnection(
                server_url=KeycloakConfig.KEYCLOAK_SERVER_URL,
                realm_name=KeycloakConfig.KEYCLOAK_REALM,
                client_id=KeycloakConfig.KEYCLOAK_ADMIN_CLIENT_ID,
                client_secret_key=KeycloakConfig.KEYCLOAK_ADMIN_CLIENT_SECRET,
                verify=True
            )

            logger.info(f"KeycloakOpenIDConnection created successfully")
            
            # Create admin client for our realm
            self._admin_client = KeycloakAdmin(
                connection=keycloak_connection,
                realm_name=KeycloakConfig.KEYCLOAK_REALM
            )
            
            logger.info("Keycloak Admin client initialized successfully")
            
            # Test the connection by trying to get realm info
            try:
                realm_info = self._admin_client.get_realm(KeycloakConfig.KEYCLOAK_REALM)
                logger.info(f"Successfully connected to realm: {realm_info.get('realm', 'Unknown')}")
            except Exception as e:
                logger.error(f"Failed to get realm info (connection test): {e}")
                raise
            
        except Exception as e:
            logger.error(f"Failed to initialize Keycloak Admin client: {e}")
            raise
    
    def create_user(self, user_data: Dict[str, Any], temporary_password: Optional[str] = None) -> Optional[str]:
        """
        Create a new user in Keycloak.
        
        Args:
            user_data: User information dictionary with keys like 'username', 'email', 'firstName', 'lastName'
            temporary_password: Optional temporary password to set
            
        Returns:
            User ID (UUID) if successful, None otherwise
        """
        try:
            # First check if user already exists by email
            username = user_data.get('username')
            email = user_data.get('email')
            
            if email:
                existing_user = self.get_user_by_email(email)
                if existing_user:
                    logger.info(f"User with email {email} already exists with ID: {existing_user['id']}")
                    return existing_user['id']
            
            # Also check by username if different from email
            if username and username != email:
                existing_user = self.get_user_by_username(username)
                if existing_user:
                    logger.info(f"User with username {username} already exists with ID: {existing_user['id']}")
                    return existing_user['id']
            
            # Prepare user payload
            user_payload = {
                "username": username,
                "email": email,
                "firstName": user_data.get('firstName', ''),
                "lastName": user_data.get('lastName', ''),
                "enabled": True,
                "emailVerified": False,
                "attributes": user_data.get('attributes', {})
            }
            
            # Remove None values
            user_payload = {k: v for k, v in user_payload.items() if v is not None}
            
            # Create user
            user_id = self._admin_client.create_user(user_payload)
            logger.info(f"Created user {username} with ID: {user_id}")
            
            # Set temporary password if provided
            if temporary_password:
                self.set_user_password(user_id, temporary_password, temporary=True)
            else:
                # Send execute actions email to set password
                self.send_execute_actions_email(user_id, ['UPDATE_PASSWORD'])
            
            return user_id
            
        except KeycloakError as e:
            logger.error(f"Keycloak error creating user: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating user: {e}")
            return None
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username."""
        try:
            users = self._admin_client.get_users({"username": username})
            return users[0] if users else None
        except Exception as e:
            logger.error(f"Error getting user by username {username}: {e}")
            return None
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email."""
        try:
            users = self._admin_client.get_users({"email": email})
            return users[0] if users else None
        except Exception as e:
            logger.error(f"Error getting user by email {email}: {e}")
            return None
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        try:
            return self._admin_client.get_user(user_id)
        except Exception as e:
            logger.error(f"Error getting user by ID {user_id}: {e}")
            return None
    
    def update_user(self, user_id: str, user_data: Dict[str, Any]) -> bool:
        """Update user information."""
        try:
            # Prepare update payload
            update_payload = {}
            
            if 'email' in user_data:
                update_payload['email'] = user_data['email']
            if 'firstName' in user_data:
                update_payload['firstName'] = user_data['firstName']            
            if 'lastName' in user_data:
                update_payload['lastName'] = user_data['lastName']
            if 'enabled' in user_data:
                update_payload['enabled'] = user_data['enabled']
            if 'attributes' in user_data:
                update_payload['attributes'] = user_data['attributes']
            
            self._admin_client.update_user(user_id, update_payload)
            logger.info(f"Updated user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            return False
    
    def set_user_password(self, user_id: str, password: str, temporary: bool = True) -> bool:
        """Set user password."""
        try:
            self._admin_client.set_user_password(user_id, password, temporary=temporary)
            logger.info(f"Set password for user {user_id} (temporary={temporary})")
            return True
        except Exception as e:
            logger.error(f"Error setting password for user {user_id}: {e}")
            return False
    
    def send_execute_actions_email(self, user_id: str, actions: List[str]) -> bool:
        """Send execute actions email to user."""
        try:
            self._admin_client.send_update_account(user_id, actions)
            logger.info(f"Sent execute actions email to user {user_id}: {actions}")
            return True
        except Exception as e:            
            logger.error(f"Error sending execute actions email to user {user_id}: {e}")
            return False
    
    def send_execute_actions_email_with_redirect(self, user_id: str, actions: List[str], 
                                               client_id: str = None, redirect_uri: str = None) -> bool:
        """Send execute actions email to user with custom client_id and redirect_uri."""
        try:
            # Use default client if not specified
            if not client_id:
                client_id = KeycloakConfig.KEYCLOAK_CLIENT_ID
            
            # Use configured redirect URI if not specified
            if not redirect_uri:
                redirect_uri = KeycloakConfig.KEYCLOAK_REDIRECT_URI
            
            # Send execute actions email with custom parameters
            self._admin_client.send_update_account(
                user_id=user_id, 
                payload=actions,
                client_id=client_id,
                redirect_uri=redirect_uri
            )
            logger.info(f"Sent execute actions email to user {user_id}: {actions} with client_id={client_id}, redirect_uri={redirect_uri}")
            return True
        except Exception as e:
            logger.error(f"Error sending execute actions email to user {user_id}: {e}")
            return False
    
    def delete_user(self, user_id: str) -> bool:
        """Delete user."""
        try:
            self._admin_client.delete_user(user_id)
            logger.info(f"Deleted user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {e}")
            return False
    
    def disable_user(self, user_id: str) -> bool:
        """Disable user."""
        try:
            self._admin_client.update_user(user_id, {"enabled": False})
            logger.info(f"Disabled user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error disabling user {user_id}: {e}")
            return False
    
    def assign_realm_role(self, user_id: str, role_name: str) -> bool:
        """Assign realm role to user."""
        try:
            # Get role
            role = self._admin_client.get_realm_role(role_name)
            if not role:
                logger.error(f"Role {role_name} not found")
                return False
            
            # Assign role
            self._admin_client.assign_realm_roles(user_id, [role])
            logger.info(f"Assigned realm role {role_name} to user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error assigning realm role {role_name} to user {user_id}: {e}")
            return False
    
    def remove_realm_role(self, user_id: str, role_name: str) -> bool:
        """Remove realm role from user."""
        try:
            # Get role
            role = self._admin_client.get_realm_role(role_name)
            if not role:
                logger.error(f"Role {role_name} not found")
                return False
            
            # Remove role
            self._admin_client.delete_realm_roles_of_user(user_id, [role])
            logger.info(f"Removed realm role {role_name} from user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing realm role {role_name} from user {user_id}: {e}")
            return False
    
    def get_user_realm_roles(self, user_id: str) -> List[str]:
        """Get user's realm roles."""
        try:
            roles = self._admin_client.get_realm_roles_of_user(user_id)
            return [role['name'] for role in roles]
        except Exception as e:
            logger.error(f"Error getting realm roles for user {user_id}: {e}")
            return []
    
    def search_users(self, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search users with parameters."""
        try:
            return self._admin_client.get_users(search_params)
        except Exception as e:
            logger.error(f"Error searching users: {e}")
            return []
    
    def get_all_realm_roles(self) -> List[Dict[str, Any]]:
        """Get all available realm roles."""
        try:
            roles = self._admin_client.get_realm_roles()
            return roles
        except Exception as e:
            logger.error(f"Error getting realm roles: {e}")
            return []
    
    def role_exists(self, role_name: str) -> bool:
        """Check if a realm role exists."""
        try:
            role = self._admin_client.get_realm_role(role_name)
            return role is not None
        except Exception as e:
            logger.error(f"Error checking if role {role_name} exists: {e}")
            return False
    
    def assign_client_role(self, user_id: str, role_name: str, client_id: str = None) -> bool:
        """Assign client role to user."""
        try:
            if not client_id:
                client_id = KeycloakConfig.KEYCLOAK_CLIENT_ID
            
            # Get client
            client = self._admin_client.get_client_id(client_id)
            if not client:
                logger.error(f"Client {client_id} not found")
                return False
            
            # Get role
            role = self._admin_client.get_client_role(client, role_name)
            if not role:
                logger.error(f"Client role {role_name} not found in client {client_id}")
                return False
              # Assign role
            self._admin_client.assign_client_role(user_id, client, role)
            logger.info(f"Assigned client role {role_name} to user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error assigning client role {role_name} to user {user_id}: {e}")
            return False

    def remove_client_role(self, user_id: str, role_name: str, client_id: str = None) -> bool:
        """Remove client role from user."""
        try:
            if not client_id:
                client_id = KeycloakConfig.KEYCLOAK_CLIENT_ID
            
            # Get user info before removing role (for debugging)
            user_before = self._admin_client.get_user(user_id)
            logger.info(f"User before role removal - Email: {user_before.get('email')}, Username: {user_before.get('username')}")
            
            # Get client
            client_uuid = self._admin_client.get_client_id(client_id)
            if not client_uuid:
                logger.error(f"Client {client_id} not found")
                return False
            
            # Get role
            role = self._admin_client.get_client_role(client_uuid, role_name)
            if not role:
                logger.error(f"Client role {role_name} not found in client {client_id}")
                return False
            
            # Remove role (using delete_client_roles_of_user method)
            self._admin_client.delete_client_roles_of_user(user_id, client_uuid, [role])
            
            # Get user info after removing role (for debugging)
            user_after = self._admin_client.get_user(user_id)
            logger.info(f"User after role removal - Email: {user_after.get('email')}, Username: {user_after.get('username')}")
            
            if user_before.get('email') != user_after.get('email'):
                logger.warning(f"WARNING: User email changed from '{user_before.get('email')}' to '{user_after.get('email')}' after role removal!")
            
            logger.info(f"Removed client role {role_name} from user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing client role {role_name} from user {user_id}: {e}")
            return False
    
    def get_user_client_roles(self, user_id: str, client_id: str = None) -> List[str]:
        """Get user's client roles."""
        try:
            if not client_id:
                client_id = KeycloakConfig.KEYCLOAK_CLIENT_ID
            
            # Get client
            client = self._admin_client.get_client_id(client_id)
            if not client:
                logger.error(f"Client {client_id} not found")
                return []
            
            roles = self._admin_client.get_client_roles_of_user(user_id, client)
            return [role['name'] for role in roles]
        except Exception as e:
            logger.error(f"Error getting client roles for user {user_id}: {e}")
            return []
    
    def client_role_exists(self, role_name: str, client_id: str = None) -> bool:
        """Check if a client role exists."""
        try:
            if not client_id:
                client_id = KeycloakConfig.KEYCLOAK_CLIENT_ID
            
            # Get client
            client = self._admin_client.get_client_id(client_id)
            if not client:
                logger.error(f"Client {client_id} not found")
                return False
            
            role = self._admin_client.get_client_role(client, role_name)
            return role is not None
        except Exception as e:
            logger.error(f"Error checking if client role {role_name} exists: {e}")
            return False
    
    def get_all_client_roles(self, client_id: str = None) -> List[Dict[str, Any]]:
        """Get all available client roles."""
        try:
            if not client_id:
                client_id = KeycloakConfig.KEYCLOAK_CLIENT_ID
            
            # Get client
            client = self._admin_client.get_client_id(client_id)
            if not client:
                logger.error(f"Client {client_id} not found")
                return []
            
            roles = self._admin_client.get_client_roles(client)
            return roles
        except Exception as e:
            logger.error(f"Error getting client roles: {e}")
            return []

    def send_custom_email(self, user_id: str, subject: str, html_body: str, redirect_uri: str = None) -> bool:
        """Send a custom HTML email to a user via Keycloak's email system."""
        try:
            # Method 1: Use Keycloak's direct email API if available
            try:
                # Try to use the direct email endpoint (requires admin privileges)
                admin_token = self._admin_client.connection.token['access_token']
                
                # Build the email endpoint URL
                email_url = f"{KeycloakConfig.KEYCLOAK_SERVER_URL}admin/realms/{KeycloakConfig.KEYCLOAK_REALM}/users/{user_id}/send-email"
                
                email_payload = {
                    "subject": subject,
                    "textBody": "",  # Plain text version
                    "htmlBody": html_body,
                    "redirect_uri": redirect_uri
                }
                
                headers = {
                    'Authorization': f'Bearer {admin_token}',
                    'Content-Type': 'application/json'
                }
                
                import requests
                response = requests.post(email_url, json=email_payload, headers=headers, timeout=30)
                
                if response.status_code in [200, 204]:
                    logger.info(f"Custom email sent successfully to user {user_id}")
                    return True
                else:
                    logger.warning(f"Direct email API failed: {response.status_code} - {response.text}")
                    # Fall back to execute actions method
                    
            except Exception as e:
                logger.warning(f"Direct email method failed: {e}, trying execute actions method")
            
            # Method 2: Fall back to execute actions email (more widely supported)
            if redirect_uri:
                success = self.send_execute_actions_email_with_redirect(
                    user_id=user_id,
                    actions=['UPDATE_PASSWORD'],
                    client_id=KeycloakConfig.KEYCLOAK_CLIENT_ID,
                    redirect_uri=redirect_uri
                )
                if success:
                    logger.info(f"Execute actions email sent successfully to user {user_id}")
                    return True
            
            logger.error(f"All email methods failed for user {user_id}")
            return False
            
        except Exception as e:
            logger.error(f"Error sending custom email to user {user_id}: {e}")
            return False
    
    def send_template_email(self, user_id: str, template_name: str, template_attributes: dict = None, redirect_uri: str = None) -> bool:
        """Send an email using a Keycloak email template."""
        try:
            # Update user attributes with template data
            if template_attributes:
                current_user = self.get_user_by_id(user_id)
                if current_user:
                    existing_attributes = current_user.get('attributes', {})
                    existing_attributes.update(template_attributes)
                    
                    self.update_user(user_id, {'attributes': existing_attributes})
            
            # Send email using the specified template
            # This typically uses execute actions or custom actions
            actions = [template_name] if template_name else ['UPDATE_PASSWORD']
            
            success = self.send_execute_actions_email_with_redirect(
                user_id=user_id,
                actions=actions,
                client_id=KeycloakConfig.KEYCLOAK_CLIENT_ID,
                redirect_uri=redirect_uri
            )
            
            if success:
                logger.info(f"Template email '{template_name}' sent to user {user_id}")
                return True
            else:
                logger.error(f"Failed to send template email '{template_name}' to user {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending template email to user {user_id}: {e}")
            return False

    def has_user_set_password(self, user_id: str) -> bool:
        """
        Check if a user has set their password (not using temporary password).
        
        Args:
            user_id: Keycloak user ID
            
        Returns:
            True if user has set their own password, False if still using temporary/no password
        """
        try:
            if not self._admin_client:
                logger.error("Admin client not initialized")
                return False
            
            # Get user details
            user = self._admin_client.get_user(user_id)
            if not user:
                logger.warning(f"User {user_id} not found")
                return False
            
            # Method 1: Check required actions - if UPDATE_PASSWORD is present, password not set
            required_actions = user.get('requiredActions', [])
            if 'UPDATE_PASSWORD' in required_actions:
                logger.debug(f"User {user_id} has UPDATE_PASSWORD in required actions - password not set")
                return False
            
            # Method 2: Check if user has password credentials
            try:
                credentials = self._admin_client.get_credentials(user_id)
                password_credentials = [cred for cred in credentials if cred.get('type') == 'password']
                
                if not password_credentials:
                    logger.debug(f"User {user_id} has no password credentials")
                    return False
                
                # If we have password credentials and no UPDATE_PASSWORD required action,
                # the user has likely set their password
                logger.debug(f"User {user_id} has password credentials and no UPDATE_PASSWORD action")
                return True
                
            except Exception as cred_error:
                logger.warning(f"Could not get credentials for user {user_id}: {cred_error}")
                # Fallback: if no required actions and user is enabled, assume password is set
                if not required_actions and user.get('enabled', False):
                    return True
                return False
                
        except Exception as e:
            logger.error(f"Error checking password status for user {user_id}: {e}")
            return False
    
    def get_user_password_status(self, user_id: str) -> Dict[str, Any]:
        """
        Get detailed password status information for a user.
        
        Args:
            user_id: Keycloak user ID
            
        Returns:
            Dictionary with password status details
        """
        try:
            if not self._admin_client:
                return {
                    'has_password': False,
                    'status': 'unknown',
                    'details': 'Admin client not initialized'
                }
            
            user = self._admin_client.get_user(user_id)
            if not user:
                return {
                    'has_password': False,
                    'status': 'user_not_found',
                    'details': 'User not found in Keycloak'
                }
            
            required_actions = user.get('requiredActions', [])
            email_verified = user.get('emailVerified', False)
            enabled = user.get('enabled', False)
              # Check credentials
            has_password_cred = False
            is_temp_password = False
            try:
                credentials = self._admin_client.get_credentials(user_id)
                password_credentials = [cred for cred in credentials if cred.get('type') == 'password']
                has_password_cred = len(password_credentials) > 0
                
                # Check if it's a temporary password
                if password_credentials:
                    # In Keycloak, if a password is temporary, it usually has a createdDate very close to user creation
                    # and the user will have UPDATE_PASSWORD in required actions or temporary flag
                    password_cred = password_credentials[0]
                    is_temp_password = password_cred.get('temporary', False)
                    
            except Exception as e:
                logger.warning(f"Could not get credentials for user {user_id}: {e}")
                has_password_cred = None
                
            # Determine status based on multiple factors
            if 'UPDATE_PASSWORD' in required_actions:
                status = 'password_required'
                has_password = False
                details = 'User must set password on next login'
            elif is_temp_password:
                status = 'password_required'
                has_password = False  
                details = 'User has temporary password and must change it'
            elif has_password_cred and not required_actions and enabled:
                # Check additional indicators of a user-set password
                # If user has logged in recently or has no temporary indicators, assume they've set their password
                status = 'password_set'
                has_password = True
                details = 'User has set their password'
            elif not enabled:
                status = 'disabled'
                has_password = False
                details = 'User account is disabled'
            elif has_password_cred is False:  # Explicitly no password credential
                status = 'not_configured'
                has_password = False
                details = 'User has not configured their password yet'
            elif has_password_cred and required_actions:
                # Has password but also has required actions - likely needs to update
                status = 'password_required'
                has_password = False
                details = f'User needs to complete actions: {", ".join(required_actions)}'
            else:
                status = 'uncertain'
                has_password = False  # Default to False for safety - prefer to send notifications
                details = 'Password status unclear - assuming needs setup'
           
            return {
                'has_password': has_password,
                'status': status,
                'details': details,
                'required_actions': required_actions,
                'email_verified': email_verified,
                'enabled': enabled,
                'has_password_credential': has_password_cred,
                'is_temp_password': is_temp_password
            }
            
        except Exception as e:
            logger.error(f"Error getting password status for user {user_id}: {e}")
            return {
                'has_password': False,
                'status': 'error',
                'details': f'Error: {str(e)}'
            }


# Global instance - lazy loaded
_keycloak_admin = None

def get_keycloak_admin():
    """Get the global KeycloakAdminClient instance (lazy loaded)."""
    global _keycloak_admin
    if _keycloak_admin is None:
        try:
            _keycloak_admin = KeycloakAdminClient()
        except Exception as e:
            logger.error(f"Failed to initialize KeycloakAdminClient: {e}")
            _keycloak_admin = None
    return _keycloak_admin

# For backwards compatibility
def keycloak_admin():
    return get_keycloak_admin()
