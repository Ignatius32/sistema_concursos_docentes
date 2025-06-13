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
            
            # Remove role
            self._admin_client.delete_client_role_from_user(user_id, client, role)
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
