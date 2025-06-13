"""
Debug script to test python-keycloak library directly
"""
import os
import logging
from keycloak import KeycloakAdmin, KeycloakOpenIDConnection

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_keycloak_library():
    # Try both with and without /auth to see which works
    server_urls = [
        "https://huayca.crub.uncoma.edu.ar/auth",
        "https://huayca.crub.uncoma.edu.ar/auth/",
        "https://huayca.crub.uncoma.edu.ar",
    ]
    
    realm = "CRUB"
    client_id = "selecciones-docentes"
    client_secret = os.environ.get('KEYCLOAK_ADMIN_CLIENT_SECRET', '')
    
    if not client_secret:
        print("ERROR: KEYCLOAK_ADMIN_CLIENT_SECRET not set")
        return
    
    for server_url in server_urls:
        print(f"\n{'='*60}")
        print(f"Testing with server URL: {server_url}")
        print(f"{'='*60}")
        
        try:
            print("1. Creating KeycloakOpenIDConnection...")
            keycloak_connection = KeycloakOpenIDConnection(
                server_url=server_url,
                realm_name=realm,
                client_id=client_id,
                client_secret_key=client_secret,
                verify=True
            )
            print("✓ KeycloakOpenIDConnection created successfully")
            
            print("2. Creating KeycloakAdmin...")
            admin_client = KeycloakAdmin(
                connection=keycloak_connection,
                realm_name=realm
            )
            print("✓ KeycloakAdmin created successfully")
            
            print("3. Testing get_realm...")
            realm_info = admin_client.get_realm(realm)
            print(f"✓ get_realm successful: {realm_info.get('realm', 'Unknown')}")
            
            print(f"SUCCESS with server URL: {server_url}")
            return server_url
            
        except Exception as e:
            print(f"✗ Error with {server_url}: {e}")
            continue
    
    print("All server URLs failed!")
    return None

if __name__ == "__main__":
    test_keycloak_library()
