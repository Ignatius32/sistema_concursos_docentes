#!/usr/bin/env python3
"""
Simple test to check Keycloak admin connection
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

print("Testing Keycloak Admin Connection...")
print(f"Server URL: {os.environ.get('KEYCLOAK_SERVER_URL')}")
print(f"Realm: {os.environ.get('KEYCLOAK_REALM')}")
print(f"Client ID: {os.environ.get('KEYCLOAK_ADMIN_CLIENT_ID')}")
print(f"Has Client Secret: {'Yes' if os.environ.get('KEYCLOAK_ADMIN_CLIENT_SECRET') else 'No'}")

try:
    from keycloak import KeycloakOpenIDConnection, KeycloakAdmin
    
    # Test basic connection
    print("\n1. Testing connection...")
    connection = KeycloakOpenIDConnection(
        server_url=os.environ.get('KEYCLOAK_SERVER_URL'),
        realm_name=os.environ.get('KEYCLOAK_REALM'),
        client_id=os.environ.get('KEYCLOAK_ADMIN_CLIENT_ID'),
        client_secret_key=os.environ.get('KEYCLOAK_ADMIN_CLIENT_SECRET'),
        verify=True
    )
    print("✅ Connection object created")
    
    # Test admin client
    print("\n2. Testing admin client...")
    admin = KeycloakAdmin(
        connection=connection,
        realm_name=os.environ.get('KEYCLOAK_REALM')
    )
    print("✅ Admin client created")
    
    # Test getting users (this will fail if service account doesn't have permissions)
    print("\n3. Testing permissions...")
    users = admin.get_users()
    print(f"✅ Successfully retrieved {len(users)} users")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print(f"Error type: {type(e)}")
