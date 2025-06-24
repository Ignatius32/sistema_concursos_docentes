"""
Initialize considerandos and departamento heads data from legacy Google Scripts.
This script fetches all existing data from the external APIs and populates the local database.
"""

import os
import sys
import json
import requests
import traceback
from datetime import datetime

# Add the parent directory to sys.path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from app import create_app
from app.models.models import db, Considerandos, DepartamentoHead

# Legacy API URLs
CONSIDERANDOS_API_URL = "https://script.google.com/macros/s/AKfycbz48ziHckZ-Ir6_gmXnUZF_S42AapQLnvpjktJXTnSbD1ps1lWimgkrxTzLXyiH_Eorlw/exec"
DEPTO_HEADS_API_URL = "https://script.google.com/macros/s/AKfycbyWU4h92lRGefLzLRSS82JhytafKIZl0jey3DuuoiCUicQcVf_1u1vzZzx7mI-0HTOg4w/exec"

def fetch_considerandos_from_api():
    """Fetch considerandos data from the legacy Google Script API."""
    print("Fetching considerandos data from legacy API...")
    
    try:
        response = requests.get(CONSIDERANDOS_API_URL, timeout=30)
        
        if response.status_code != 200:
            print(f"Error: HTTP {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return None
        
        data = response.json()
        print(f"Successfully fetched {len(data)} considerandos entries")
        
        # Save raw data for backup
        with open('considerandos_backup.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print("Backup saved to considerandos_backup.json")
        
        return data
        
    except requests.exceptions.Timeout:
        print("Error: Request timeout while fetching considerandos data")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error: Network error while fetching considerandos data: {str(e)}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON response from considerandos API: {str(e)}")
        return None
    except Exception as e:
        print(f"Error: Unexpected error fetching considerandos data: {str(e)}")
        traceback.print_exc()
        return None

def fetch_depto_heads_from_api():
    """Fetch departamento heads data from the legacy Google Script API."""
    print("Fetching departamento heads data from legacy API...")
    
    try:
        response = requests.get(DEPTO_HEADS_API_URL, timeout=30)
        
        if response.status_code != 200:
            print(f"Error: HTTP {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return None
        
        data = response.json()
        print(f"Successfully fetched {len(data)} departamento heads entries")
        
        # Save raw data for backup
        with open('depto_heads_backup.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print("Backup saved to depto_heads_backup.json")
        
        return data
        
    except requests.exceptions.Timeout:
        print("Error: Request timeout while fetching departamento heads data")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error: Network error while fetching departamento heads data: {str(e)}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON response from departamento heads API: {str(e)}")
        return None
    except Exception as e:
        print(f"Error: Unexpected error fetching departamento heads data: {str(e)}")
        traceback.print_exc()
        return None

def populate_considerandos_table(data):
    """Populate the considerandos table with fetched data."""
    print("Populating considerandos table...")
    
    try:
        # Clear existing data
        deleted_count = Considerandos.query.delete()
        print(f"Cleared {deleted_count} existing considerandos entries")
        
        # Insert new data
        created_count = 0
        for item in data:
            try:
                # Validate required fields
                if not item.get('document_type'):
                    print(f"Warning: Skipping item without document_type: {item}")
                    continue
                
                considerando = Considerandos(
                    document_type=item['document_type'],
                    visibility=item.get('visibility', 'both'),
                    considerandos_data=item.get('considerandos', {})
                )
                
                db.session.add(considerando)
                created_count += 1
                print(f"Added considerando: {item['document_type']}")
                
            except Exception as e:
                print(f"Error processing considerando item {item.get('document_type', 'unknown')}: {str(e)}")
                continue
        
        db.session.commit()
        print(f"Successfully populated considerandos table with {created_count} entries")
        return True
        
    except Exception as e:
        print(f"Error populating considerandos table: {str(e)}")
        traceback.print_exc()
        db.session.rollback()
        return False

def populate_depto_heads_table(data):
    """Populate the departamento heads table with fetched data."""
    print("Populating departamento heads table...")
    
    try:
        # Clear existing data
        deleted_count = DepartamentoHead.query.delete()
        print(f"Cleared {deleted_count} existing departamento heads entries")
        
        # Insert new data
        created_count = 0
        for item in data:
            try:
                # Validate required fields
                if not item.get('departamento'):
                    print(f"Warning: Skipping item without departamento: {item}")
                    continue
                
                head = DepartamentoHead(
                    departamento=item['departamento'],
                    responsable=item.get('responsable', ''),
                    correo=item.get('correo', ''),
                    prefijo=item.get('prefijo', '')
                )
                
                db.session.add(head)
                created_count += 1
                print(f"Added departamento head: {item['departamento']} - {item.get('responsable', 'N/A')}")
                
            except Exception as e:
                print(f"Error processing departamento head item {item.get('departamento', 'unknown')}: {str(e)}")
                continue
        
        db.session.commit()
        print(f"Successfully populated departamento heads table with {created_count} entries")
        return True
        
    except Exception as e:
        print(f"Error populating departamento heads table: {str(e)}")
        traceback.print_exc()
        db.session.rollback()
        return False

def validate_migration():
    """Validate that the migration was successful."""
    print("\n" + "="*60)
    print("VALIDATING MIGRATION")
    print("="*60)
    
    # Check considerandos
    considerandos_count = Considerandos.query.count()
    print(f"Considerandos entries in database: {considerandos_count}")
    
    if considerandos_count > 0:
        print("\nConsiderandos Summary:")
        for considerando in Considerandos.query.all():
            print(f"  - {considerando.document_type} ({considerando.visibility})")
            print(f"    Considerandos count: {len(considerando.considerandos_data) if considerando.considerandos_data else 0}")
    
    # Check departamento heads
    heads_count = DepartamentoHead.query.count()
    print(f"\nDepartamento heads entries in database: {heads_count}")
    
    if heads_count > 0:
        print("\nDepartamento Heads Summary:")
        for head in DepartamentoHead.query.all():
            status = "✓" if head.responsable else "⚠"
            print(f"  {status} {head.departamento}")
            if head.responsable:
                print(f"    Responsable: {head.responsable}")
                print(f"    Correo: {head.correo or 'N/A'}")
                print(f"    Prefijo: {head.prefijo or 'N/A'}")
    
    # Summary
    print(f"\n" + "="*60)
    if considerandos_count > 0 and heads_count > 0:
        print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
        print(f"   - {considerandos_count} considerandos entries")
        print(f"   - {heads_count} departamento heads entries")
        print("\nThe legacy Google Script APIs can now be safely replaced with local database queries.")
    else:
        print("❌ MIGRATION INCOMPLETE!")
        print("Some data may not have been migrated successfully.")
    
    return considerandos_count > 0 and heads_count > 0

def show_api_comparison():
    """Show before/after comparison of API usage."""
    print("\n" + "="*60)
    print("API MIGRATION SUMMARY")
    print("="*60)
    
    print("BEFORE (External APIs):")
    print(f"  - Considerandos: {CONSIDERANDOS_API_URL}")
    print(f"  - Depto Heads:   {DEPTO_HEADS_API_URL}")
    print("  - Network dependent")
    print("  - Slower response times")
    print("  - External service reliability issues")
    
    print("\nAFTER (Local Database):")
    print("  - Considerandos: Local SQLite/PostgreSQL database")
    print("  - Depto Heads:   Local SQLite/PostgreSQL database")
    print("  - No network dependency")
    print("  - Faster response times")
    print("  - Full control over data")
    print("  - Admin interface for data management")
    
    print("\nNext Steps:")
    print("1. ✅ Data has been migrated to local database")
    print("2. ✅ Admin interface is available at /admin/api-data/")
    print("3. ✅ API functions updated to use local data")
    print("4. 🔄 Test the application to ensure everything works")
    print("5. 🔄 Remove external API URLs from configuration (optional)")

def main():
    """Main initialization function."""
    print("="*60)
    print("LEGACY API DATA MIGRATION")
    print("="*60)
    print(f"Starting migration at {datetime.now()}")
    print("This script will migrate data from legacy Google Scripts to local database.")
    print()
    
    # Confirm with user
    response = input("Do you want to proceed with the migration? (y/N): ")
    if response.lower() not in ['y', 'yes']:
        print("Migration cancelled by user.")
        return
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        # Ensure tables exist
        db.create_all()
        
        # Fetch data from APIs
        print("\n" + "="*60)
        print("STEP 1: FETCHING DATA FROM LEGACY APIS")
        print("="*60)
        
        considerandos_data = fetch_considerandos_from_api()
        depto_heads_data = fetch_depto_heads_from_api()
        
        if not considerandos_data:
            print("❌ Failed to fetch considerandos data")
            return
        
        if not depto_heads_data:
            print("❌ Failed to fetch departamento heads data")
            return
        
        # Populate database
        print("\n" + "="*60)
        print("STEP 2: POPULATING LOCAL DATABASE")
        print("="*60)
        
        considerandos_success = populate_considerandos_table(considerandos_data)
        heads_success = populate_depto_heads_table(depto_heads_data)
        
        if not considerandos_success or not heads_success:
            print("❌ Failed to populate database")
            return
        
        # Validate migration
        print("\n" + "="*60)
        print("STEP 3: VALIDATING MIGRATION")
        print("="*60)
        
        if validate_migration():
            show_api_comparison()
            
            print("\n" + "="*60)
            print("🎉 MIGRATION COMPLETED SUCCESSFULLY!")
            print("="*60)
            print("Your application now uses local database instead of external APIs.")
            print("You can manage this data through the admin interface at:")
            print("  - /admin/api-data/considerandos")
            print("  - /admin/api-data/departamento-heads")
        else:
            print("❌ Migration validation failed")

if __name__ == "__main__":
    main()
    main()
