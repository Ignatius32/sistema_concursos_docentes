#!/usr/bin/env python3
"""
Quick test script to debug Keycloak connection and configuration.
"""
import os
import sys
import requests
from dotenv import load_dotenv
from urllib.parse import urlencode

# Load environment variables
load_dotenv()

def test_keycloak_endpoints():
    """Test Keycloak endpoints to verify connectivity."""
    
    # Get configuration from environment
    server_url = os.getenv('KEYCLOAK_SERVER_URL')
    realm = os.getenv('KEYCLOAK_REALM')
    client_id = os.getenv('KEYCLOAK_CLIENT_ID')
    client_secret = os.getenv('KEYCLOAK_CLIENT_SECRET')
    redirect_uri = os.getenv('KEYCLOAK_REDIRECT_URI')
    
    print("=" * 60)
    print("KEYCLOAK CONNECTION TEST")
    print("=" * 60)
    
    print(f"Server URL: {server_url}")
    print(f"Realm: {realm}")
    print(f"Client ID: {client_id}")
    print(f"Client Secret: {'*' * (len(client_secret) if client_secret else 0)}")
    print(f"Redirect URI: {redirect_uri}")
    print()
    
    # Test 1: Check if server is reachable
    print("1. Testing server connectivity...")
    try:
        response = requests.get(f"{server_url}", timeout=10)
        print(f"   ✓ Server is reachable (Status: {response.status_code})")
    except Exception as e:
        print(f"   ✗ Server unreachable: {e}")
        return False
    
    # Test 2: Test realm exists
    print("\n2. Testing realm accessibility...")
    try:
        response = requests.get(f"{server_url}/realms/{realm}", timeout=10)
        print(f"   ✓ Realm accessible (Status: {response.status_code})")
    except Exception as e:
        print(f"   ✗ Realm not accessible: {e}")
        return False
    
    # Test 3: Test well-known configuration
    print("\n3. Testing well-known configuration...")
    try:
        response = requests.get(f"{server_url}/realms/{realm}/.well-known/openid_configuration", timeout=10)
        if response.status_code == 200:
            config = response.json()
            print(f"   ✓ Well-known config available")
            print(f"   - Issuer: {config.get('issuer', 'N/A')}")
            print(f"   - Auth endpoint: {config.get('authorization_endpoint', 'N/A')}")
            print(f"   - Token endpoint: {config.get('token_endpoint', 'N/A')}")
        else:
            print(f"   ✗ Well-known config not available (Status: {response.status_code})")
            print(f"   Response: {response.text[:200]}...")
    except Exception as e:
        print(f"   ✗ Well-known config error: {e}")
    
    # Test 4: Test authorization endpoint
    print("\n4. Testing authorization endpoint...")
    try:
        auth_url = f"{server_url}/realms/{realm}/protocol/openid-connect/auth"
        params = {
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': 'openid profile email'
        }
        
        # Just test if endpoint responds (don't follow redirects)
        response = requests.get(auth_url, params=params, allow_redirects=False, timeout=10)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            print("   ✓ Authorization endpoint works")
        elif response.status_code == 302:
            print("   ✓ Authorization endpoint redirects (expected)")
        elif response.status_code == 400:
            print("   ⚠ Bad request - check client configuration")
            print(f"   Response: {response.text[:300]}...")
        else:
            print(f"   ✗ Unexpected response: {response.text[:300]}...")
            
    except Exception as e:
        print(f"   ✗ Authorization endpoint error: {e}")
    
    # Test 5: Test token endpoint
    print("\n5. Testing token endpoint...")
    try:
        token_url = f"{server_url}/realms/{realm}/protocol/openid-connect/token"
        response = requests.post(token_url, data={}, timeout=10)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 400:
            print("   ✓ Token endpoint accessible (400 expected without proper params)")
        else:
            print(f"   Response: {response.text[:200]}...")
            
    except Exception as e:
        print(f"   ✗ Token endpoint error: {e}")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
    
    return True


def test_flask_config():
    """Test Flask configuration."""
    
    print("\n" + "=" * 60)
    print("FLASK CONFIGURATION TEST")
    print("=" * 60)
    
    try:
        # Import Flask app components
        from app.config.keycloak_config import KeycloakConfig
        
        print("1. Testing KeycloakConfig...")
        print(f"   Server URL: {KeycloakConfig.KEYCLOAK_SERVER_URL}")
        print(f"   Realm: {KeycloakConfig.KEYCLOAK_REALM}")
        print(f"   Client ID: {KeycloakConfig.KEYCLOAK_CLIENT_ID}")
        print(f"   Client Secret: {'*' * len(KeycloakConfig.KEYCLOAK_CLIENT_SECRET) if KeycloakConfig.KEYCLOAK_CLIENT_SECRET else 'NOT SET'}")
        print(f"   Redirect URI: {KeycloakConfig.KEYCLOAK_REDIRECT_URI}")
        
        # Test configuration validation
        print("\n2. Testing configuration validation...")
        config_errors = KeycloakConfig.validate_config()
        if config_errors:
            print("   ✗ Configuration errors found:")
            for error in config_errors:
                print(f"     - {error}")
        else:
            print("   ✓ Configuration validation passed")
            
        # Test OIDC config generation
        print("\n3. Testing OIDC config generation...")
        oidc_config = KeycloakConfig.get_oidc_config()
        print("   ✓ OIDC config generated:")
        for key, value in oidc_config.items():
            print(f"     - {key}: {value}")
            
    except Exception as e:
        print(f"   ✗ Flask config test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("Starting Keycloak connection tests...")
    
    # Test 1: Direct endpoint tests
    test_keycloak_endpoints()
    
    # Test 2: Flask configuration
    test_flask_config()
    
    print("\nTest completed. Check the output above for any issues.")
