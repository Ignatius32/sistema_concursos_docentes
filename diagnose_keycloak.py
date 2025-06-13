"""
Enhanced Keycloak Configuration Diagnostic Script
"""
import requests
import os
import json
from urllib.parse import urljoin

def test_url(url, description, expected_status=200):
    """Test a URL and return the result"""
    try:
        response = requests.get(url, timeout=10)
        status = response.status_code
        success = status == expected_status
        print(f"{'✓' if success else '✗'} {description}: {url}")
        print(f"  Status: {status} {'(OK)' if success else '(FAILED)'}")
        
        if not success:
            if len(response.text) < 500:
                print(f"  Response: {response.text[:200]}...")
            else:
                print(f"  Response length: {len(response.text)} characters")
        
        return success, response
    except Exception as e:
        print(f"✗ {description}: {url}")
        print(f"  Error: {e}")
        return False, None

def test_admin_api_with_credentials():
    """Test admin API access with client credentials"""
    server_url = os.environ.get('KEYCLOAK_SERVER_URL', 'https://huayca.crub.uncoma.edu.ar/auth')
    realm = os.environ.get('KEYCLOAK_REALM', 'CRUB')
    client_id = os.environ.get('KEYCLOAK_ADMIN_CLIENT_ID', 'selecciones-docentes')
    client_secret = os.environ.get('KEYCLOAK_ADMIN_CLIENT_SECRET', '')
    
    if not client_secret:
        print("⚠ KEYCLOAK_ADMIN_CLIENT_SECRET not set - skipping authenticated tests")
        return False
    
    print(f"\nTesting Admin API with client credentials...")
    print(f"Client ID: {client_id}")
    print(f"Client Secret: {'*' * len(client_secret) if client_secret else 'NOT SET'}")
    
    # Get token
    token_url = f"{server_url}/realms/{realm}/protocol/openid-connect/token"
    token_data = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret
    }
    
    try:
        token_response = requests.post(token_url, data=token_data, timeout=10)
        print(f"Token request status: {token_response.status_code}")
        
        if token_response.status_code == 200:
            token_info = token_response.json()
            access_token = token_info.get('access_token')
            print("✓ Successfully obtained access token")
            
            # Test admin API endpoints
            headers = {'Authorization': f'Bearer {access_token}'}
            
            admin_tests = [
                (f"{server_url}/admin/realms/{realm}/users", "List users"),
                (f"{server_url}/admin/realms/{realm}/roles", "List roles"),
                (f"{server_url}/admin/realms/{realm}", "Realm info"),
            ]
            
            for url, description in admin_tests:
                success, response = test_url_with_auth(url, description, headers)
                if success and response:
                    try:
                        data = response.json()
                        if isinstance(data, list):
                            print(f"    Found {len(data)} items")
                        elif isinstance(data, dict):
                            print(f"    Response contains {len(data)} fields")
                    except:
                        pass
            
            return True
        else:
            print(f"✗ Failed to get token: {token_response.status_code}")
            try:
                error_info = token_response.json()
                print(f"  Error: {error_info}")
            except:
                print(f"  Response: {token_response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"✗ Error testing admin API: {e}")
        return False

def test_url_with_auth(url, description, headers):
    """Test URL with authentication headers"""
    try:
        response = requests.get(url, headers=headers, timeout=10)
        status = response.status_code
        success = status == 200
        print(f"{'✓' if success else '✗'} {description}: {status}")
        return success, response
    except Exception as e:
        print(f"✗ {description}: Error - {e}")
        return False, None

def check_oidc_endpoints():
    """Check OIDC configuration and endpoints"""
    server_url = os.environ.get('KEYCLOAK_SERVER_URL', 'https://huayca.crub.uncoma.edu.ar/auth')
    realm = os.environ.get('KEYCLOAK_REALM', 'CRUB')
    
    print("\nChecking OIDC endpoints...")
    
    # Try different possible paths for OIDC configuration
    oidc_paths = [
        f"/realms/{realm}/.well-known/openid_configuration",
        f"/realms/{realm}/.well-known/openid-configuration/",
        f"/auth/realms/{realm}/.well-known/openid_configuration",
    ]
    
    for path in oidc_paths:
        url = f"{server_url.rstrip('/')}{path}"
        success, response = test_url(url, f"OIDC Config ({path})")
        
        if success and response:
            try:
                config = response.json()
                if 'authorization_endpoint' in config:
                    print("  ✓ Valid OIDC configuration found!")
                    print(f"    Authorization: {config.get('authorization_endpoint', 'N/A')}")
                    print(f"    Token: {config.get('token_endpoint', 'N/A')}")
                    print(f"    Userinfo: {config.get('userinfo_endpoint', 'N/A')}")
                    return True
                else:
                    print(f"  ⚠ Response doesn't look like OIDC config: {list(config.keys())}")
            except json.JSONDecodeError:
                print("  ⚠ Response is not valid JSON")
    
    return False

def main():
    # Get configuration from environment
    server_url = os.environ.get('KEYCLOAK_SERVER_URL', 'https://huayca.crub.uncoma.edu.ar/auth')
    realm = os.environ.get('KEYCLOAK_REALM', 'CRUB')
    client_id = os.environ.get('KEYCLOAK_CLIENT_ID', 'selecciones-docentes')
    admin_client_id = os.environ.get('KEYCLOAK_ADMIN_CLIENT_ID', 'selecciones-docentes')
    client_secret = os.environ.get('KEYCLOAK_ADMIN_CLIENT_SECRET', '')
    
    print("=" * 80)
    print("ENHANCED KEYCLOAK DIAGNOSTIC")
    print("=" * 80)
    print(f"Server URL: {server_url}")
    print(f"Realm: {realm}")
    print(f"OIDC Client ID: {client_id}")
    print(f"Admin Client ID: {admin_client_id}")
    print(f"Client Secret: {'SET' if client_secret else 'NOT SET'}")
    print()
    
    # Basic connectivity tests
    print("1. BASIC CONNECTIVITY TESTS")
    print("-" * 40)
    
    basic_tests = [
        (f"{server_url}/", "Base Keycloak URL"),
        (f"{server_url}/realms/{realm}", "Realm base URL"),
    ]
    
    basic_results = {}
    for url, description in basic_tests:
        basic_results[description], _ = test_url(url, description)
    
    # OIDC configuration tests
    print("\n2. OIDC CONFIGURATION TESTS")
    print("-" * 40)
    oidc_works = check_oidc_endpoints()
    
    # Admin API tests (unauthenticated)
    print("\n3. ADMIN API TESTS (Unauthenticated)")
    print("-" * 40)
    admin_tests = [
        (f"{server_url}/admin/realms/{realm}", "Admin API base", 401),  # Expect 401
        (f"{server_url}/admin/realms/{realm}/users", "Admin API users", 401),
        (f"{server_url}/admin/realms/{realm}/roles", "Admin API roles", 401),
    ]
    
    for url, description, expected in admin_tests:
        test_url(url, description, expected)
    
    # Admin API tests (authenticated)
    if client_secret:
        print("\n4. ADMIN API TESTS (Authenticated)")
        print("-" * 40)
        admin_works = test_admin_api_with_credentials()
    else:
        admin_works = False
        print("\n4. ADMIN API TESTS (Authenticated)")
        print("-" * 40)
        print("⚠ Skipping authenticated tests - KEYCLOAK_ADMIN_CLIENT_SECRET not set")
    
    # Summary and recommendations
    print("\n" + "=" * 80)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 80)
    
    if basic_results.get("Base Keycloak URL", False):
        print("✓ Keycloak server is accessible")
    else:
        print("✗ Keycloak server is not accessible")
        
    if basic_results.get("Realm base URL", False):
        print("✓ Realm exists and is accessible")
    else:
        print("✗ Realm not accessible - check realm name")
        
    if oidc_works:
        print("✓ OIDC configuration is working")
    else:
        print("✗ OIDC configuration not accessible")
        
    if admin_works:
        print("✓ Admin API is working with authentication")
    else:
        print("✗ Admin API authentication failed")
    
    print("\nRECOMMENDATIONS:")
    print("-" * 40)
    
    if not client_secret:
        print("1. ⚠ Set KEYCLOAK_ADMIN_CLIENT_SECRET environment variable")
        print("   Get this from: Keycloak Admin → Clients → selecciones-docentes → Credentials")
    
    if not oidc_works:
        print("2. ⚠ OIDC configuration issue detected")
        print("   Check if the realm 'CRUB' is correctly configured")
        print("   Verify realm is active and accessible")
    
    if not admin_works:
        print("3. ⚠ Admin API access issue")
        print("   Ensure your client has 'Service accounts roles' enabled")
        print("   Assign proper roles to the service account (realm-admin or manage-users)")
    
    print("\nNEXT STEPS:")
    print("1. Configure your Keycloak client following KEYCLOAK_CLIENT_SETUP.md")
    print("2. Set the KEYCLOAK_ADMIN_CLIENT_SECRET environment variable")
    print("3. Run this diagnostic again to verify the setup")

if __name__ == "__main__":
    main()
