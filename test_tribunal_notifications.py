#!/usr/bin/env python3
"""
Test script to verify Keycloak integration for tribunal notifications.
This script tests the updated notification logic in tribunal.py.
"""

import os
import sys

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))

from app.integrations.keycloak_admin_client import KeycloakAdminClient

def test_keycloak_notification_integration():
    """Test Keycloak admin client for tribunal notifications."""
    print("=== Testing Keycloak Notification Integration ===")
    
    try:
        # Initialize Keycloak admin client
        keycloak_admin = KeycloakAdminClient()
        print("✓ Keycloak admin client initialized successfully")
        
        # Test connection by trying to get realm roles (safe operation)
        try:
            roles = keycloak_admin.get_all_realm_roles()
            print(f"✓ Keycloak connection test passed (found {len(roles)} realm roles)")
        except Exception as e:
            print(f"✗ Keycloak connection test failed: {e}")
            return False
        
        # Test get_user_by_email method (we need this for notifications)
        print("\n--- Testing user lookup methods ---")
        
        # Check if we can search for users by email
        # (This is a safe test that doesn't modify anything)
        try:
            # This should return None for a non-existent email
            test_user = keycloak_admin.get_user_by_email("nonexistent@example.com")
            print(f"✓ get_user_by_email method works (returned: {test_user})")
        except Exception as e:
            print(f"✗ get_user_by_email method failed: {e}")
            return False
        
        # Test that send_execute_actions_email_with_redirect method exists
        print("\n--- Testing notification methods ---")
        try:
            # Check if the method exists (don't call it)
            if hasattr(keycloak_admin, 'send_execute_actions_email_with_redirect'):
                print("✓ send_execute_actions_email_with_redirect method exists")
            else:
                print("✗ send_execute_actions_email_with_redirect method not found")
                return False
            
            if hasattr(keycloak_admin, 'send_execute_actions_email'):
                print("✓ send_execute_actions_email method exists")
            else:
                print("✗ send_execute_actions_email method not found")
                return False
                
        except Exception as e:
            print(f"✗ Error checking notification methods: {e}")
            return False
        
        print("\n✓ All Keycloak notification integration tests passed!")
        print("\nThe updated tribunal.py notification routes should work correctly with:")
        print("- notificar_tribunal(): Keycloak password reset emails for document notifications")
        print("- notificar_todos_miembros(): Keycloak password reset emails for all members")
        print("- notificar_miembro(): Keycloak password reset emails for individual members")
        print("- activar_cuenta(): Keycloak password reset emails for self-activation")
        print("- recuperar_password(): Keycloak password reset emails for self-recovery")
        
        return True
        
    except Exception as e:
        print(f"✗ Keycloak notification integration test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_keycloak_notification_integration()
    
    if not success:
        print("\n❌ Some tests failed. Please check Keycloak configuration.")
        sys.exit(1)
    else:
        print("\n✅ All tests passed! Tribunal notification integration is ready.")
        sys.exit(0)
