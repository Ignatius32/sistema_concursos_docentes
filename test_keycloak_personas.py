"""
Test script for Keycloak admin personas integration
"""
import os
import sys

# Add the parent directory to the path to import the app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.integrations.keycloak_admin_client import get_keycloak_admin
from app.config.keycloak_config import KeycloakConfig

def test_keycloak_admin_connection():
    """Test Keycloak admin client connection."""
    print("Testing Keycloak Admin Client connection...")
    
    try:
        keycloak_admin = get_keycloak_admin()
        if keycloak_admin:
            print("✓ Keycloak Admin Client initialized successfully")
            
            # Test role existence in client
            admin_role = KeycloakConfig.KEYCLOAK_ADMIN_ROLE
            tribunal_role = KeycloakConfig.KEYCLOAK_TRIBUNAL_ROLE
            client_id = KeycloakConfig.KEYCLOAK_CLIENT_ID
            
            print(f"Checking client role existence in client '{client_id}':")
            print(f"- {admin_role}: {'EXISTS' if keycloak_admin.client_role_exists(admin_role) else 'NOT FOUND'}")
            print(f"- {tribunal_role}: {'EXISTS' if keycloak_admin.client_role_exists(tribunal_role) else 'NOT FOUND'}")
            
            # List all available client roles
            all_client_roles = keycloak_admin.get_all_client_roles()
            print(f"\nAvailable client roles in '{client_id}':")
            for role in all_client_roles[:10]:  # Limit to first 10 roles
                print(f"- {role.get('name', 'Unknown')}: {role.get('description', 'No description')}")
            if len(all_client_roles) > 10:
                print(f"... and {len(all_client_roles) - 10} more client roles")
            
            # Also check realm roles for comparison
            print(f"\nChecking realm role existence (for comparison):")
            print(f"- {admin_role}: {'EXISTS' if keycloak_admin.role_exists(admin_role) else 'NOT FOUND'}")
            print(f"- {tribunal_role}: {'EXISTS' if keycloak_admin.role_exists(tribunal_role) else 'NOT FOUND'}")
            
            # List some realm roles
            all_realm_roles = keycloak_admin.get_all_realm_roles()
            print(f"\nAvailable realm roles:")
            for role in all_realm_roles[:5]:  # Limit to first 5 roles
                print(f"- {role.get('name', 'Unknown')}")
            if len(all_realm_roles) > 5:
                print(f"... and {len(all_realm_roles) - 5} more realm roles")
                
        else:
            print("✗ Failed to initialize Keycloak Admin Client")
            
    except Exception as e:
        print(f"✗ Error testing Keycloak Admin Client: {e}")

def print_configuration():
    """Print current Keycloak configuration."""
    print("Current Keycloak Configuration:")
    print(f"- Server URL: {KeycloakConfig.KEYCLOAK_SERVER_URL}")
    print(f"- Realm: {KeycloakConfig.KEYCLOAK_REALM}")
    print(f"- Client ID: {KeycloakConfig.KEYCLOAK_CLIENT_ID}")
    print(f"- Admin Client ID: {KeycloakConfig.KEYCLOAK_ADMIN_CLIENT_ID}")
    print(f"- Admin Role: {KeycloakConfig.KEYCLOAK_ADMIN_ROLE}")
    print(f"- Tribunal Role: {KeycloakConfig.KEYCLOAK_TRIBUNAL_ROLE}")
    print()

if __name__ == "__main__":
    print("=" * 60)
    print("KEYCLOAK INTEGRATION TEST")
    print("=" * 60)
    
    print_configuration()
    test_keycloak_admin_connection()
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
