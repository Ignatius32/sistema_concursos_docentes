#!/usr/bin/env python3
"""
Test script to check what information we can get from Keycloak about user password status.
This will help us determine how to distinguish between users who have set their password
and those who haven't.
"""

import sys
import os
import json
import time
from pprint import pprint

# Add the app directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.integrations.keycloak_admin_client import get_keycloak_admin
from app.models.models import Persona, db


def test_user_password_status():
    """Test what information we can get about user password status from Keycloak."""
    
    print("🔍 Testing Keycloak user password status detection...")
    print("=" * 60)
    
    # Initialize Flask app context
    app = create_app()
    
    with app.app_context():
        keycloak_admin = get_keycloak_admin()
        
        if not keycloak_admin:
            print("❌ Error: Could not initialize Keycloak admin client")
            return
            
        print("✅ Keycloak admin client initialized successfully")
        
        # Get some sample personas to test with
        sample_personas = Persona.query.filter(
            Persona.keycloak_user_id.isnot(None)
        ).limit(5).all()
        
        if not sample_personas:
            print("❌ No personas with Keycloak user IDs found")
            return
            
        print(f"📋 Testing with {len(sample_personas)} sample personas...")
        print()
        
        for i, persona in enumerate(sample_personas, 1):
            print(f"👤 Testing Persona {i}: {persona.nombre} {persona.apellido}")
            print(f"   📧 Email: {persona.correo}")
            print(f"   🆔 Keycloak User ID: {persona.keycloak_user_id}")
            
            try:
                # Get user details from Keycloak
                user_data = keycloak_admin.get_user_by_id(persona.keycloak_user_id)
                
                if not user_data:
                    print("   ❌ User not found in Keycloak")
                    continue
                
                print(f"   📊 Keycloak User Data:")
                print(f"      • Username: {user_data.get('username')}")
                print(f"      • Email: {user_data.get('email')}")
                print(f"      • Enabled: {user_data.get('enabled')}")
                print(f"      • Email Verified: {user_data.get('emailVerified')}")
                print(f"      • Created Timestamp: {user_data.get('createdTimestamp')}")
                
                # Check for password-related fields
                password_related_fields = [
                    'credentials', 'disableableCredentialTypes', 'requiredActions',
                    'notBefore', 'totp', 'access', 'clientRoles', 'realmRoles',
                    'groups', 'serviceAccountClientId', 'federatedIdentities'
                ]
                
                print(f"   🔐 Password-related fields:")
                for field in password_related_fields:
                    if field in user_data:
                        value = user_data[field]
                        if isinstance(value, (dict, list)) and len(str(value)) > 100:
                            print(f"      • {field}: {type(value).__name__} (length: {len(value) if isinstance(value, list) else len(value.keys()) if isinstance(value, dict) else 'N/A'})")
                        else:
                            print(f"      • {field}: {value}")
                
                # Check required actions - this might indicate if password needs to be set
                required_actions = user_data.get('requiredActions', [])
                print(f"   ⚠️  Required Actions: {required_actions}")
                
                # Try to get user credentials (this might not be available for security reasons)
                try:
                    # This API call might not work due to security restrictions
                    credentials = keycloak_admin._admin_client.get_credentials(persona.keycloak_user_id)
                    print(f"   🔑 Credentials info: {credentials}")
                except Exception as cred_error:
                    print(f"   🔑 Credentials info: Not accessible ({str(cred_error)[:50]}...)")
                
                # Check user sessions to see if they've ever logged in
                try:
                    sessions = keycloak_admin._admin_client.get_user_sessions(persona.keycloak_user_id)
                    print(f"   🔄 User Sessions: {len(sessions) if sessions else 0} sessions found")
                    if sessions:
                        latest_session = max(sessions, key=lambda s: s.get('lastAccess', 0))
                        print(f"      • Latest session: {latest_session.get('lastAccess')} (timestamp)")
                except Exception as session_error:
                    print(f"   🔄 User Sessions: Not accessible ({str(session_error)[:50]}...)")
                
                # Check if user has password credential type
                try:
                    # Check available credential types
                    disableable_creds = user_data.get('disableableCredentialTypes', [])
                    print(f"   💳 Disableable Credential Types: {disableable_creds}")
                    
                    # If 'password' is not in disableable credentials, it might mean password is set
                    has_password_cred = 'password' not in disableable_creds
                    print(f"   🔐 Likely has password set: {has_password_cred}")
                    
                except Exception as e:
                    print(f"   💳 Credential type check failed: {e}")
                
            except Exception as e:
                print(f"   ❌ Error getting user data: {e}")
            
            print("-" * 50)
          # Test with a user that definitely hasn't set password (if we can create one)
        print("\n🧪 Testing with a fresh user (if possible)...")
        try:
            test_user_data = {
                'username': f'test_user_{int(time.time())}',
                'email': f'test_{int(time.time())}@test.com',
                'firstName': 'Test',
                'lastName': 'User'
            }
            
            test_user_id = keycloak_admin.create_user(test_user_data)
            if test_user_id:
                print(f"✅ Created test user with ID: {test_user_id}")
                
                # Get fresh user data
                fresh_user_data = keycloak_admin.get_user_by_id(test_user_id)
                print(f"📊 Fresh user data:")
                print(f"   • Required Actions: {fresh_user_data.get('requiredActions', [])}")
                print(f"   • Disableable Creds: {fresh_user_data.get('disableableCredentialTypes', [])}")
                print(f"   • Email Verified: {fresh_user_data.get('emailVerified')}")
                
                # Clean up - delete the test user
                try:
                    keycloak_admin.delete_user(test_user_id)
                    print("🗑️  Test user deleted")
                except:
                    print("⚠️  Could not delete test user - manual cleanup may be needed")
                    
        except Exception as e:
            print(f"❌ Could not create test user: {e}")


def analyze_password_detection_methods():
    """Analyze different methods to detect password status."""
    
    print("\n" + "=" * 60)
    print("📋 SUMMARY: Methods to detect password status")
    print("=" * 60)
    
    methods = [
        {
            'method': 'Required Actions',
            'description': 'Check if "UPDATE_PASSWORD" is in requiredActions array',
            'pros': 'Direct indication that password needs to be set',
            'cons': 'May be cleared after first login attempt',
            'reliability': 'High for fresh users'
        },
        {
            'method': 'Disableable Credential Types',
            'description': 'Check if "password" is NOT in disableableCredentialTypes',
            'pros': 'Indicates password credential exists',
            'cons': 'May not distinguish between set vs temporary password',
            'reliability': 'Medium'
        },
        {
            'method': 'User Sessions',
            'description': 'Check if user has any login sessions',
            'pros': 'Shows actual usage',
            'cons': 'User might have set password but never logged in',
            'reliability': 'Medium'
        },
        {
            'method': 'Email Verified + Actions',
            'description': 'Combine email verification status with required actions',
            'pros': 'More comprehensive check',
            'cons': 'Complex logic needed',
            'reliability': 'High'
        }
    ]
    
    for i, method in enumerate(methods, 1):
        print(f"\n{i}. {method['method']}")
        print(f"   📝 Description: {method['description']}")
        print(f"   ✅ Pros: {method['pros']}")
        print(f"   ❌ Cons: {method['cons']}")
        print(f"   🎯 Reliability: {method['reliability']}")


if __name__ == "__main__":
    test_user_password_status()
    analyze_password_detection_methods()
    
    print("\n" + "=" * 60)
    print("✨ RECOMMENDATION")
    print("=" * 60)
    print("""
    Based on typical Keycloak behavior, the best approach would be:
    
    1. Check 'requiredActions' array for 'UPDATE_PASSWORD'
    2. Fallback to checking user sessions count
    3. Consider email verification status as additional context
    
    We should add a method to KeycloakAdminClient to check password status
    and then use it in the tribunal template.
    """)
