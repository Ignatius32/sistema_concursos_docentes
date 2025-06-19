#!/usr/bin/env python3
"""
Test the new password status detection methods
"""

import os
from dotenv import load_dotenv
load_dotenv()

from app.integrations.keycloak_admin_client import get_keycloak_admin

def test_new_methods():
    print("🧪 Testing new password status methods...")
    print("=" * 60)
    
    admin = get_keycloak_admin()
    if not admin:
        print("❌ Failed to initialize Keycloak admin client")
        return
    
    # Test users from our previous test
    test_users = [
        {
            'name': 'juancito bastito (no password)',
            'id': '3c01bb39-8e79-49f4-b6d8-301c13af9158',
            'username': '11111111'
        },
        {
            'name': 'mari tribunello (has password)',
            'id': '8a2c1b77-8bb7-43f7-94c2-dafd254614e8',
            'username': '12345678'
        },
        {
            'name': 'milo jota (has password)',
            'id': '4b7e04d9-c975-440c-877a-831045a42a55',  
            'username': '98765432'
        }
    ]
    
    for user in test_users:
        print(f"\n👤 Testing {user['name']}")
        print(f"   🆔 ID: {user['id']}")
        print(f"   👨‍💼 Username: {user['username']}")
        
        # Test our new methods
        status = admin.get_user_password_status(user['id'])
        has_password = admin.has_user_set_password(user['id'])
        
        print(f"   📊 Detailed status:")
        print(f"      • has_password: {status['has_password']}")
        print(f"      • status: {status['status']}")
        print(f"      • details: {status['details']}")
        print(f"      • required_actions: {status['required_actions']}")
        print(f"      • has_password_credential: {status['has_password_credential']}")
        print(f"   ✅ Simple method result: {has_password}")
        
        print("-" * 50)

if __name__ == "__main__":
    test_new_methods()
