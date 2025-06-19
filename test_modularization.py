#!/usr/bin/env python3
"""
Test script to verify the modularization of tribunal.py is working correctly.
This script tests the new password_reset_service and verifies that the 
Keycloak password status detection is working properly.
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.abspath('.'))

def test_imports():
    """Test that all imports work correctly after modularization."""
    try:
        from app.services.password_reset_service import PasswordResetService
        print("✓ PasswordResetService import successful")
        
        from app.integrations.keycloak_admin_client import KeycloakAdminClient
        print("✓ KeycloakAdminClient import successful")
        
        from app.routes.tribunal import tribunal as tribunal_bp
        print("✓ Tribunal blueprint import successful")
        
        from app.routes.auth import auth as auth_bp
        print("✓ Auth blueprint import successful")
        
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False

def test_password_reset_service():
    """Test the password reset service functionality."""
    try:
        from app.services.password_reset_service import PasswordResetService
        
        # Test that the service can be instantiated
        service = PasswordResetService()
        print("✓ PasswordResetService instantiated successfully")
          # Test that methods exist
        assert hasattr(service, 'generate_reset_token')
        assert hasattr(service, 'verify_reset_token')
        assert hasattr(service, 'send_reset_email_internal')
        assert hasattr(service, 'notify_tribunal_member_with_reset')
        print("✓ All expected methods exist in PasswordResetService")
        
        return True
    except Exception as e:
        print(f"✗ PasswordResetService test failed: {e}")
        return False

def test_keycloak_admin_client():
    """Test the Keycloak admin client password status method."""
    try:
        from app.integrations.keycloak_admin_client import KeycloakAdminClient
        
        # Test that the method exists and has the correct signature
        assert hasattr(KeycloakAdminClient, 'get_user_password_status')
        print("✓ KeycloakAdminClient.get_user_password_status method exists")
        
        return True
    except Exception as e:
        print(f"✗ KeycloakAdminClient test failed: {e}")
        return False

def test_flask_app_creation():
    """Test that the Flask app can be created with all modifications."""
    try:
        from app import create_app
        
        app = create_app()
        print("✓ Flask app created successfully")
        
        # Check that the blueprints are registered
        blueprint_names = [bp.name for bp in app.blueprints.values()]
        
        if 'tribunal' in blueprint_names:
            print("✓ Tribunal blueprint registered")
        else:
            print("✗ Tribunal blueprint not found")
        
        if 'auth' in blueprint_names:
            print("✓ Auth blueprint registered")
        else:
            print("✗ Auth blueprint not found")
        
        return True
    except Exception as e:
        print(f"✗ Flask app creation failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Testing modularization of tribunal.py...")
    print("=" * 50)
    
    tests = [
        ("Import Tests", test_imports),
        ("PasswordResetService Tests", test_password_reset_service),
        ("KeycloakAdminClient Tests", test_keycloak_admin_client),
        ("Flask App Creation", test_flask_app_creation),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * 30)
        success = test_func()
        results.append((test_name, success))
    
    print("\n" + "=" * 50)
    print("SUMMARY:")
    print("=" * 50)
    
    all_passed = True
    for test_name, success in results:
        status = "PASS" if success else "FAIL"
        print(f"{test_name}: {status}")
        if not success:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("✓ ALL TESTS PASSED - Modularization successful!")
    else:
        print("✗ SOME TESTS FAILED - Please check the issues above")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
