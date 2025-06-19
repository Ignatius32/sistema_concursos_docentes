#!/usr/bin/env python3
"""
Debug script to test Keycloak configuration and environment variables.
Run this script to verify that the environment is properly configured.
"""

import os
import sys
from pathlib import Path

# Add the application directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
from dotenv import load_dotenv
env_path = Path(__file__).resolve().parent / '.env'
load_dotenv(env_path)

print("=== Environment Variables Debug ===")
print(f"Loading .env from: {env_path}")
print(f"File exists: {env_path.exists()}")
print()

# Check key environment variables
env_vars = [
    'APPLICATION_ROOT',
    'KEYCLOAK_SERVER_URL',
    'KEYCLOAK_REALM',
    'KEYCLOAK_CLIENT_ID',
    'KEYCLOAK_CLIENT_SECRET',
    'KEYCLOAK_ADMIN_CLIENT_ID',
    'KEYCLOAK_ADMIN_CLIENT_SECRET',
    'SECRET_KEY'
]

print("=== Key Environment Variables ===")
for var in env_vars:
    value = os.environ.get(var)
    if var in ['SECRET_KEY', 'KEYCLOAK_CLIENT_SECRET', 'KEYCLOAK_ADMIN_CLIENT_SECRET']:
        # Mask sensitive values
        masked_value = value[:4] + '...' + value[-4:] if value and len(value) > 8 else '***MASKED***' if value else 'NOT SET'
        print(f"{var}: {masked_value}")
    else:
        print(f"{var}: {value}")
print()

# Test Keycloak configuration
print("=== Keycloak Configuration Test ===")
try:
    from app.config.keycloak_config import KeycloakConfig
    
    print("KeycloakConfig imported successfully")
    print(f"Server URL: {KeycloakConfig.KEYCLOAK_SERVER_URL}")
    print(f"Realm: {KeycloakConfig.KEYCLOAK_REALM}")
    print(f"Client ID: {KeycloakConfig.KEYCLOAK_CLIENT_ID}")
    print(f"Has Client Secret: {bool(KeycloakConfig.KEYCLOAK_CLIENT_SECRET)}")
    
    # Test OIDC config validation
    print("\n=== OIDC Configuration Validation ===")
    oidc_errors = KeycloakConfig.validate_oidc_config()
    if oidc_errors:
        print("OIDC Configuration Errors:")
        for error in oidc_errors:
            print(f"  - {error}")
    else:
        print("OIDC Configuration: OK")
    
    # Test dynamic URL generation
    print("\n=== Dynamic URL Generation Test ===")
    print(f"APPLICATION_ROOT: {KeycloakConfig.APPLICATION_ROOT}")
    
    # Test OIDC endpoints
    print("\n=== OIDC Endpoints ===")
    oidc_config = KeycloakConfig.get_oidc_config()
    for key, value in oidc_config.items():
        print(f"{key}: {value}")
        
except Exception as e:
    print(f"Error testing Keycloak configuration: {e}")
    import traceback
    traceback.print_exc()

print("\n=== Keycloak Admin Client Test ===")
try:
    from app.integrations.keycloak_admin_client import get_keycloak_admin
    
    admin_client = get_keycloak_admin()
    if admin_client:
        print("Keycloak Admin Client: Initialized successfully")
    else:
        print("Keycloak Admin Client: Failed to initialize")
        
except Exception as e:
    print(f"Error testing Keycloak Admin Client: {e}")
    import traceback
    traceback.print_exc()

print("\n=== Test Complete ===")
