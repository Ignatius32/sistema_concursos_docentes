#!/usr/bin/env python3
"""
Test Keycloak client configuration specifically.
"""
import os
import requests
from dotenv import load_dotenv
from urllib.parse import urlencode

load_dotenv()

def test_client_config():
    """Test if the client configuration is correct."""
    
    server_url = os.getenv('KEYCLOAK_SERVER_URL')
    realm = os.getenv('KEYCLOAK_REALM')
    client_id = os.getenv('KEYCLOAK_CLIENT_ID')
    client_secret = os.getenv('KEYCLOAK_CLIENT_SECRET')
    redirect_uri = os.getenv('KEYCLOAK_REDIRECT_URI')
    
    print("=" * 60)
    print("KEYCLOAK CLIENT CONFIGURATION TEST")
    print("=" * 60)
    
    print(f"Testing client: {client_id}")
    print(f"Redirect URI: {redirect_uri}")
    print()
    
    # Test 1: Try to get a token using client credentials
    print("1. Testing client credentials...")
    try:
        token_url = f"{server_url}/realms/{realm}/protocol/openid-connect/token"
        
        data = {
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret
        }
        
        response = requests.post(token_url, data=data, timeout=10)
        
        if response.status_code == 200:
            print("   ✓ Client credentials are valid")
            token_data = response.json()
            print(f"   - Access token received (length: {len(token_data.get('access_token', ''))})")
        else:
            print(f"   ✗ Client credentials failed (Status: {response.status_code})")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"   ✗ Client credentials test failed: {e}")
    
    # Test 2: Check if redirect URI is valid by testing auth endpoint
    print("\n2. Testing authorization endpoint with redirect URI...")
    try:
        auth_url = f"{server_url}/realms/{realm}/protocol/openid-connect/auth"
        
        params = {
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': 'openid profile email',
            'state': 'test_state'
        }
        
        # Test with a HEAD request to avoid full redirect
        response = requests.head(auth_url, params=params, allow_redirects=False, timeout=10)
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code in [200, 302]:
            print("   ✓ Authorization endpoint accepts the configuration")
        elif response.status_code == 400:
            print("   ✗ Bad request - likely invalid redirect_uri or client_id")
        else:
            print(f"   ⚠ Unexpected status: {response.status_code}")
            
        if 'Location' in response.headers:
            print(f"   Redirect to: {response.headers['Location'][:100]}...")
            
    except Exception as e:
        print(f"   ✗ Authorization endpoint test failed: {e}")
    
    print("\n" + "=" * 60)
    print("RECOMMENDATIONS:")
    print("=" * 60)
    
    print("If client credentials failed, check in Keycloak Admin Console:")
    print("1. Go to Clients → selecciones-docentes")
    print("2. Verify 'Client ID' matches:", client_id)
    print("3. Check 'Access Type' is set to 'confidential'")
    print("4. Verify 'Secret' in Credentials tab matches your .env file")
    print("5. Ensure 'Service Accounts Enabled' is ON")
    print()
    print("If redirect URI failed, check:")
    print("1. Valid Redirect URIs should include:", redirect_uri)
    print("2. Also add: http://127.0.0.1:5000/*")
    print("3. And: http://localhost:5000/*")

if __name__ == "__main__":
    test_client_config()
