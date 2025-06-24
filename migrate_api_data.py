"""
Migration script to populate local database with external API data.
This script fetches data from external APIs and stores it locally.
"""

import os
import sys
import json
import traceback
from datetime import datetime

# Add the parent directory to sys.path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from app import create_app
from app.models.models import db, Considerandos, DepartamentoHead

def load_json_data(filename):
    """Load data from JSON file."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"File {filename} not found. Please run test_external_apis.py first.")
        return None
    except Exception as e:
        print(f"Error loading {filename}: {str(e)}")
        return None

def migrate_considerandos_data():
    """Migrate considerandos data from JSON to database."""
    print("Migrating considerandos data...")
    
    data = load_json_data('considerandos_response.json')
    if not data:
        return False
    
    try:
        # Clear existing data
        Considerandos.query.delete()
        
        # Insert new data
        for item in data:
            considerando = Considerandos(
                document_type=item['document_type'],
                visibility=item['visibility'],
                unique=item['unique'],
                considerandos_data=item['considerandos']
            )
            db.session.add(considerando)
        
        db.session.commit()
        print(f"Successfully migrated {len(data)} considerandos entries.")
        return True
        
    except Exception as e:
        print(f"Error migrating considerandos data: {str(e)}")
        traceback.print_exc()
        db.session.rollback()
        return False

def migrate_departamento_heads_data():
    """Migrate departamento heads data from JSON to database."""
    print("Migrating departamento heads data...")
    
    data = load_json_data('depto_heads_response.json')
    if not data:
        return False
    
    try:
        # Clear existing data
        DepartamentoHead.query.delete()
        
        # Insert new data
        for item in data:
            head = DepartamentoHead(
                departamento=item['departamento'],
                responsable=item.get('responsable', ''),
                correo=item.get('correo', ''),
                prefijo=item.get('prefijo', '')
            )
            db.session.add(head)
        
        db.session.commit()
        print(f"Successfully migrated {len(data)} departamento heads entries.")
        return True
        
    except Exception as e:
        print(f"Error migrating departamento heads data: {str(e)}")
        traceback.print_exc()
        db.session.rollback()
        return False

def verify_migration():
    """Verify that the migration was successful."""
    print("\nVerifying migration...")
    
    # Check considerandos
    considerandos_count = Considerandos.query.count()
    print(f"Considerandos entries in database: {considerandos_count}")
    
    if considerandos_count > 0:
        # Show sample
        sample = Considerandos.query.first()
        print(f"Sample considerando: {sample.document_type}")
    
    # Check departamento heads
    heads_count = DepartamentoHead.query.count()
    print(f"Departamento heads entries in database: {heads_count}")
    
    if heads_count > 0:
        # Show sample
        sample = DepartamentoHead.query.first()
        print(f"Sample departamento head: {sample.departamento} - {sample.responsable}")
    
    return considerandos_count > 0 and heads_count > 0

def main():
    """Main migration function."""
    print(f"Starting data migration - {datetime.now()}")
    print("=" * 60)
    
    # Create Flask app and setup database
    app = create_app()
    
    with app.app_context():
        # Create tables if they don't exist
        db.create_all()
        
        # Migrate data
        considerandos_success = migrate_considerandos_data()
        heads_success = migrate_departamento_heads_data()
        
        if considerandos_success and heads_success:
            # Verify migration
            if verify_migration():
                print("\n" + "=" * 60)
                print("MIGRATION COMPLETED SUCCESSFULLY!")
                print("=" * 60)
                print("The external API data has been successfully migrated to the local database.")
                print("You can now update api_services.py to use local data instead of external APIs.")
            else:
                print("\nMIGRATION VERIFICATION FAILED!")
        else:
            print("\nMIGRATION FAILED!")
            print("Please check the error messages above and try again.")

if __name__ == "__main__":
    main()
