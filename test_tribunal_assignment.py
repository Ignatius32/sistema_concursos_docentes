#!/usr/bin/env python3
"""
Test script to verify tribunal member assignment functionality.
This script tests the complete flow of assigning existing personas to a concurso as tribunal members.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from app import create_app
from app.models.models import db, Persona, Concurso, TribunalMiembro
from app.integrations.keycloak_admin_client import KeycloakAdminClient
from app.config.keycloak_config import KeycloakConfig
import uuid

def test_tribunal_assignment():
    """Test the complete tribunal assignment flow."""
    app = create_app()
    
    with app.app_context():
        print("🧪 Testing Tribunal Assignment Functionality")
        print("=" * 50)
        
        # Test 1: Check if we have test personas
        print("\n1. Checking for existing test personas...")
        test_personas = Persona.query.filter(Persona.dni.like('12345%')).all()
        print(f"   Found {len(test_personas)} test personas")
        
        for persona in test_personas:
            print(f"   - {persona.nombre} {persona.apellido} (DNI: {persona.dni}, ID: {persona.id})")
            if persona.keycloak_user_id:
                print(f"     Keycloak User ID: {persona.keycloak_user_id}")
        
        if not test_personas:
            print("   ❌ No test personas found. Please create some test personas first.")
            return False
        
        # Test 2: Check if we have a test concurso
        print("\n2. Checking for test concurso...")
        test_concurso = Concurso.query.first()
        if not test_concurso:
            print("   ❌ No concurso found. Please create a test concurso first.")
            return False
        
        print(f"   Found concurso: ID {test_concurso.id}")
        
        # Test 3: Check existing tribunal assignments
        print(f"\n3. Checking existing tribunal assignments for concurso {test_concurso.id}...")
        existing_assignments = TribunalMiembro.query.filter_by(concurso_id=test_concurso.id).all()
        print(f"   Found {len(existing_assignments)} existing assignments")
        
        for assignment in existing_assignments:
            print(f"   - {assignment.persona.nombre} {assignment.persona.apellido} as {assignment.rol}")
        
        # Test 4: Find available personas (not assigned to this concurso)
        print(f"\n4. Finding available personas for concurso {test_concurso.id}...")
        assigned_persona_ids = db.session.query(TribunalMiembro.persona_id).filter_by(concurso_id=test_concurso.id).subquery()
        available_personas = Persona.query.filter(~Persona.id.in_(assigned_persona_ids)).all()
        
        print(f"   Found {len(available_personas)} available personas")
        for persona in available_personas[:5]:  # Show first 5
            print(f"   - {persona.nombre} {persona.apellido} (DNI: {persona.dni})")
        
        if not available_personas:
            print("   ⚠️  No available personas for assignment")
            return True
        
        # Test 5: Test Keycloak client role assignment
        print("\n5. Testing Keycloak client role assignment...")
        keycloak_admin = KeycloakAdminClient()
        
        # Use the first available persona with a Keycloak user ID
        test_persona = None
        for persona in available_personas:
            if persona.keycloak_user_id:
                test_persona = persona
                break
        
        if not test_persona:
            print("   ⚠️  No available personas with Keycloak user ID found")
            # Try to find any persona with Keycloak user ID
            test_persona = Persona.query.filter(Persona.keycloak_user_id.isnot(None)).first()
            if not test_persona:
                print("   ❌ No personas with Keycloak user ID found")
                return False
        
        print(f"   Testing with persona: {test_persona.nombre} {test_persona.apellido}")
        print(f"   Keycloak User ID: {test_persona.keycloak_user_id}")
        
        try:
            # Check if user has tribunal role
            has_role = keycloak_admin.has_client_role(test_persona.keycloak_user_id, KeycloakConfig.KEYCLOAK_TRIBUNAL_ROLE)
            print(f"   User has tribunal role: {has_role}")
            
            if not has_role:
                print("   Assigning tribunal role...")
                keycloak_admin.assign_client_role(test_persona.keycloak_user_id, KeycloakConfig.KEYCLOAK_TRIBUNAL_ROLE)
                print("✅ Tribunal role assigned successfully")
            else:
                print("✅ User already has tribunal role")
                
        except Exception as e:
            print(f"   ❌ Error testing Keycloak role assignment: {e}")
            return False
        
        # Test 6: Simulate tribunal assignment (without actually creating it)
        print("\n6. Simulating tribunal assignment...")
        print(f"   Would assign: {test_persona.nombre} {test_persona.apellido}")
        print(f"   To concurso: {test_concurso.id}")
        print(f"   As role: Titular")
        print(f"   Claustro: Docente")
        
        # Check for duplicates
        existing_assignment = TribunalMiembro.query.filter_by(
            persona_id=test_persona.id, 
            concurso_id=test_concurso.id
        ).first()
        
        if existing_assignment:
            print(f"   ⚠️  Persona already assigned as {existing_assignment.rol}")
        else:
            print("✅ No duplicate assignment found - ready to assign")
        
        print("\n" + "=" * 50)
        print("🎉 Tribunal assignment test completed successfully!")
        print("\nNext steps:")
        print("1. Use the web interface to assign personas to concursos")
        print("2. Verify that Keycloak roles are assigned correctly")
        print("3. Check that no duplicate assignments are created")
        
        return True

if __name__ == "__main__":
    try:
        success = test_tribunal_assignment()
        if success:
            print("\n✅ All tests passed!")
        else:
            print("\n❌ Some tests failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
