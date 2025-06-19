#!/usr/bin/env python3
"""
Quick test to verify the new Keycloak password status integration
"""

import os
from dotenv import load_dotenv
load_dotenv()

from app.integrations.keycloak_admin_client import get_keycloak_admin

def test_integration():
    print("🧪 Testing Keycloak password status integration...")
    print("=" * 60)
    
    admin = get_keycloak_admin()
    if not admin:
        print("❌ Failed to initialize Keycloak admin client")
        return
    
    print("✅ Keycloak admin client initialized successfully")
    
    # Test the methods that will be used in the template
    test_user_id = '3c01bb39-8e79-49f4-b6d8-301c13af9158'  # juancito bastito
    
    print(f"\n🔍 Testing user ID: {test_user_id}")
    
    # Test get_user_password_status - this is what the template will call
    status = admin.get_user_password_status(test_user_id)
    print(f"📊 Password status:")
    print(f"   • has_password: {status['has_password']}")
    print(f"   • status: {status['status']}")
    print(f"   • details: {status['details']}")
    
    # Test has_user_set_password - backup method
    has_password = admin.has_user_set_password(test_user_id)
    print(f"✅ Simple check: {has_password}")
    
    print("\n🎯 Template logic simulation:")
    if status['has_password']:
        print("   Badge: 'Contraseña Activa' (green)")
        print("   Action: 'Configurado' badge")
    elif status['status'] == 'password_required':
        print("   Badge: 'Requiere Contraseña' (warning)")
        print("   Action: Send/Resend button")
    elif status['status'] == 'not_configured':
        print("   Badge: 'No Configurado' (warning)")
        print("   Action: Send/Resend button")
    elif status['status'] == 'disabled':
        print("   Badge: 'Usuario Deshabilitado' (secondary)")
        print("   Action: Error badge")
    else:
        print("   Badge: 'Estado Incierto' (light)")
        print("   Action: Send/Resend button")
    
    print("\n✅ Integration test completed successfully!")

if __name__ == "__main__":
    test_integration()
