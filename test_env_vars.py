"""
Test environment variables loading
"""
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

print("Environment Variables Test")
print("=" * 40)

keycloak_vars = [
    'KEYCLOAK_SERVER_URL',
    'KEYCLOAK_REALM', 
    'KEYCLOAK_CLIENT_ID',
    'KEYCLOAK_CLIENT_SECRET',
    'KEYCLOAK_ADMIN_CLIENT_ID',
    'KEYCLOAK_ADMIN_CLIENT_SECRET'
]

for var in keycloak_vars:
    value = os.environ.get(var, 'NOT SET')
    if 'SECRET' in var and value != 'NOT SET':
        print(f"{var}: {'*' * len(value)} (length: {len(value)})")
    else:
        print(f"{var}: {value}")

print("\nTesting Keycloak Config Import...")
try:
    from app.config.keycloak_config import KeycloakConfig
    print(f"✓ Config Server URL: {KeycloakConfig.KEYCLOAK_SERVER_URL}")
    print(f"✓ Config Realm: {KeycloakConfig.KEYCLOAK_REALM}")
    print(f"✓ Config Client ID: {KeycloakConfig.KEYCLOAK_CLIENT_ID}")
    print(f"✓ Config has client secret: {bool(KeycloakConfig.KEYCLOAK_CLIENT_SECRET)}")
    print(f"✓ Config has admin secret: {bool(KeycloakConfig.KEYCLOAK_ADMIN_CLIENT_SECRET)}")
except Exception as e:
    print(f"✗ Error importing config: {e}")

print("\nNext steps:")
print("1. Set your actual Keycloak client secret in the .env file")
print("2. Restart your Flask application")
print("3. Test the persona creation again")
