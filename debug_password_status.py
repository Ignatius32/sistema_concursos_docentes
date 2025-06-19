#!/usr/bin/env python3
"""
Debug script to check detailed password status for specific users.
This will help determine if the Keycloak password detection is accurate.
"""

import os
import sys
sys.path.insert(0, os.path.abspath('.'))

from app import create_app
from app.integrations.keycloak_admin_client import get_keycloak_admin
from app.models.models import db, Persona

def debug_user_password_status(user_email):
    """Debug password status for a specific user."""
    print(f"\n🔍 Debugging password status for: {user_email}")
    print("=" * 60)
    
    # Get user from database
    persona = Persona.query.filter_by(correo=user_email).first()
    if not persona:
        print(f"❌ User with email {user_email} not found in database")
        return
    
    print(f"📋 Database Info:")
    print(f"   - Name: {persona.nombre} {persona.apellido}")
    print(f"   - DNI: {persona.dni}")
    print(f"   - Email: {persona.correo}")
    print(f"   - Keycloak User ID: {persona.keycloak_user_id}")
    print(f"   - Local password_hash: {'Yes' if persona.password_hash else 'No'}")
    
    if not persona.keycloak_user_id:
        print("❌ No Keycloak User ID found - user not synced with Keycloak")
        return
    
    # Get Keycloak admin client
    keycloak_admin = get_keycloak_admin()
    if not keycloak_admin:
        print("❌ Could not connect to Keycloak")
        return
    
    print(f"\n🔐 Keycloak Password Status:")
    
    # Get detailed password status
    password_status = keycloak_admin.get_user_password_status(persona.keycloak_user_id)
    
    print(f"   - Has Password: {password_status.get('has_password')}")
    print(f"   - Status: {password_status.get('status')}")
    print(f"   - Details: {password_status.get('details')}")
    print(f"   - Required Actions: {password_status.get('required_actions', [])}")
    print(f"   - Email Verified: {password_status.get('email_verified')}")
    print(f"   - Enabled: {password_status.get('enabled')}")
    print(f"   - Has Password Credential: {password_status.get('has_password_credential')}")
    print(f"   - Is Temp Password: {password_status.get('is_temp_password')}")
    
    # Get raw user data from Keycloak
    print(f"\n📊 Raw Keycloak User Data:")
    try:
        user_data = keycloak_admin.get_user_by_id(persona.keycloak_user_id)
        if user_data:
            print(f"   - Username: {user_data.get('username')}")
            print(f"   - Email: {user_data.get('email')}")
            print(f"   - Enabled: {user_data.get('enabled')}")
            print(f"   - Email Verified: {user_data.get('emailVerified')}")
            print(f"   - Required Actions: {user_data.get('requiredActions', [])}")
            print(f"   - Created Timestamp: {user_data.get('createdTimestamp')}")
            
            # Try to get credentials info
            try:
                credentials = keycloak_admin._admin_client.get_credentials(persona.keycloak_user_id)
                print(f"   - Credentials Count: {len(credentials)}")
                for i, cred in enumerate(credentials):
                    print(f"     * Credential {i+1}: {cred.get('type')} (ID: {cred.get('id')})")
                    if cred.get('type') == 'password':
                        print(f"       - Created: {cred.get('createdDate')}")
                        print(f"       - Temporary: {cred.get('temporary', 'Unknown')}")
            except Exception as e:
                print(f"   - Could not get credentials: {e}")
        else:
            print("   - ❌ User not found in Keycloak")
    except Exception as e:
        print(f"   - ❌ Error getting user data: {e}")
    
    print(f"\n🎯 UI Decision Logic:")
    if password_status.get('has_password'):
        print("   ✅ Will show 'Configurado' badge (no notification buttons)")
        print("   📝 This means user has already set their password")
    else:
        print("   🔔 Will show notification buttons")
        print("   📝 This means user needs to set their password")

def main():
    """Main debug function."""
    print("🔍 Keycloak Password Status Debug Tool")
    print("=" * 50)
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        # Debug specific users from your example
        users_to_debug = [
            "departamento.docente@uncobariloche.com",
            "ignacio.basti@crub.uncoma.edu.ar"
        ]
        
        for user_email in users_to_debug:
            debug_user_password_status(user_email)
        
        print(f"\n" + "=" * 60)
        print("🔍 ANALYSIS:")
        print("If users show 'has_password: True' but you believe they shouldn't,")
        print("then either:")
        print("1. They actually did set their passwords (possibly directly in Keycloak)")
        print("2. The password detection logic needs adjustment")
        print("3. They have temporary passwords that aren't being detected properly")
        print("\nIf you want to force-reset their status, you can:")
        print("1. Add UPDATE_PASSWORD to their required actions in Keycloak")
        print("2. Mark their passwords as temporary")
        print("3. Adjust the detection logic if needed")

if __name__ == "__main__":
    main()
