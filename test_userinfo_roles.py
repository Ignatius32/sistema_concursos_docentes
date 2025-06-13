#!/usr/bin/env python3
"""
Test script to verify userinfo endpoint response and role extraction.
"""
import os
import sys
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_userinfo_endpoint():
    """Test the userinfo endpoint with a sample token."""
    print("Testing Keycloak userinfo endpoint...")
    
    # We'll need to get this from the app's session after login
    print("Note: This test requires an actual access token from a login session.")
    print("You can get this by:")
    print("1. Login to the app")
    print("2. Check the session storage in browser dev tools")
    print("3. Look for keycloak_token.access_token")
    print()
    
    # Get userinfo endpoint URL
    keycloak_server_url = os.getenv('KEYCLOAK_SERVER_URL')
    keycloak_realm = os.getenv('KEYCLOAK_REALM')
    
    userinfo_url = f"{keycloak_server_url}/realms/{keycloak_realm}/protocol/openid-connect/userinfo"
    print(f"Userinfo URL: {userinfo_url}")
    
    # Prompt for access token
    token = input("Enter access token (or 'skip' to skip): ").strip()
    
    if token.lower() == 'skip':
        print("Skipping token test.")
        return
    
    if not token:
        print("No token provided.")
        return
    
    try:
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(userinfo_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            user_info = response.json()
            print("✅ Successfully retrieved user info!")
            print(f"User info keys: {list(user_info.keys())}")
            print()
            
            # Check for various role locations
            print("Checking for roles in userinfo response:")
            
            if 'roles' in user_info:
                print(f"  - Direct roles: {user_info['roles']}")
            
            if 'realm_access' in user_info:
                realm_access = user_info['realm_access']
                print(f"  - Realm access: {realm_access}")
                if isinstance(realm_access, dict) and 'roles' in realm_access:
                    print(f"  - Realm roles: {realm_access['roles']}")
            
            if 'resource_access' in user_info:
                resource_access = user_info['resource_access']
                print(f"  - Resource access: {resource_access}")
            
            if 'groups' in user_info:
                print(f"  - Groups: {user_info['groups']}")
            
            print()
            print("Full userinfo response:")
            import json
            print(json.dumps(user_info, indent=2))
            
        else:
            print(f"❌ Failed to get user info: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error testing userinfo endpoint: {e}")

def main():
    print("=== Keycloak Userinfo Role Extraction Test ===")
    print()
    test_userinfo_endpoint()

if __name__ == "__main__":
    main()
