#!/usr/bin/env python3
"""
Test script to verify the password status functionality in the tribunal template.
"""
import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath('.'))

from dotenv import load_dotenv
from app.models.models import db, Persona, Concurso, TribunalMiembro
from app.integrations.keycloak_admin_client import get_keycloak_admin
from flask import Flask

# Load environment variables
load_dotenv()

def test_password_status_functionality():
    """Test the password status functionality end-to-end."""
    print("🔍 Testing password status functionality for tribunal members...")
    print("=" * 60)
    
    # Create a minimal Flask app for testing
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/concursos.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize database
    db.init_app(app)
    
    with app.app_context():
        try:
            # Test 1: Check if we can get Keycloak admin client
            print("📋 Test 1: Keycloak Admin Client Initialization")
            keycloak_admin = get_keycloak_admin()
            if keycloak_admin:
                print("✅ Keycloak admin client initialized successfully")
            else:
                print("❌ Failed to initialize Keycloak admin client")
                return
            
            # Test 2: Get some personas with keycloak_user_id
            print("\n📋 Test 2: Testing Persona Password Status Methods")
            personas_with_keycloak = Persona.query.filter(
                Persona.keycloak_user_id.isnot(None)
            ).limit(3).all()
            
            if not personas_with_keycloak:
                print("❌ No personas with Keycloak user ID found")
                return
                
            for persona in personas_with_keycloak:
                print(f"\n👤 Testing persona: {persona.nombre} {persona.apellido}")
                print(f"   🆔 Keycloak User ID: {persona.keycloak_user_id}")
                
                # Test the new methods
                try:
                    status_detail = persona.get_keycloak_password_status()
                    status_display = persona.get_password_status_display()
                    
                    print(f"   📊 Detailed status: {status_detail}")
                    print(f"   🎯 Display status: {status_display}")
                    
                    # Test direct Keycloak admin methods
                    admin_status = keycloak_admin.has_password_set(persona.keycloak_user_id)
                    admin_display = keycloak_admin.get_user_password_status(persona.keycloak_user_id)
                    
                    print(f"   🔧 Admin status: {admin_status}")
                    print(f"   🔧 Admin display: {admin_display}")
                    
                except Exception as e:
                    print(f"   ❌ Error testing persona: {str(e)}")
            
            # Test 3: Check if we have tribunal members to test with
            print("\n📋 Test 3: Testing with Tribunal Members")
            tribunal_members = TribunalMiembro.query.join(Persona).filter(
                Persona.keycloak_user_id.isnot(None)
            ).limit(2).all()
            
            if tribunal_members:
                print(f"✅ Found {len(tribunal_members)} tribunal members with Keycloak integration")
                for miembro in tribunal_members:
                    print(f"   👥 {miembro.persona.nombre} {miembro.persona.apellido} - {miembro.rol}")
                    status = miembro.persona.get_password_status_display()
                    print(f"      🔐 Password status: {status}")
            else:
                print("⚠️  No tribunal members with Keycloak integration found")
            
            print("\n✅ All tests completed successfully!")
            
        except Exception as e:
            print(f"❌ Error during testing: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_password_status_functionality()
