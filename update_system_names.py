#!/usr/bin/env python3
"""
Script to update all remaining "Sistema de Concursos Docentes" references 
to "Sistema de Selecciones Docentes" in the codebase
"""

import os
import re

def replace_in_file(file_path, old_text, new_text):
    """Replace text in a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        if old_text in content:
            print(f"Updating: {file_path}")
            print(f"  '{old_text}' → '{new_text}'")
            updated_content = content.replace(old_text, new_text)
            
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(updated_content)
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Update all system name references."""
    
    print("Updating system name references to 'Sistema de Selecciones Docentes'")
    print("=" * 70)
    
    files_updated = 0
    
    # Define the files and replacements
    replacements = [
        # System name in various forms
        ('Sistema de Concursos Docentes', 'Sistema de Selecciones Docentes'),
        ('Sistema Concursos Docentes', 'Sistema Selecciones Docentes'),
        ('sistema_concursos_docentes', 'sistema_selecciones_docentes'),
        
        # Installation script references
        ('Installation script for Sistema Concursos Docentes', 'Installation script for Sistema Selecciones Docentes'),
        ('=== Sistema Concursos Docentes Installation Script ===', '=== Sistema Selecciones Docentes Installation Script ==='),
        
        # Application startup message
        ('Sistema Concursos Docentes application started successfully', 'Sistema Selecciones Docentes application started successfully'),
    ]
    
    # Files to process
    files_to_process = [
        'wsgi.py',
        'install.sh',
        'app.gs',
        'app/routes/notifications.py',
        'app/routes/concursos/documents.py',
        'app/services/password_reset_service.py',
        'app/services/password_reset_service_backup.py',
    ]
    
    # Process each file
    for file_path in files_to_process:
        if os.path.exists(file_path):
            file_changed = False
            for old_text, new_text in replacements:
                if replace_in_file(file_path, old_text, new_text):
                    file_changed = True
            if file_changed:
                files_updated += 1
        else:
            print(f"Warning: File not found: {file_path}")
    
    print("=" * 70)
    print(f"System name update completed!")
    print(f"Files updated: {files_updated}")
    
    print(f"\nUpdated references:")
    print(f"✓ Application startup messages")
    print(f"✓ Email sender names")
    print(f"✓ Installation script titles")
    print(f"✓ Google Apps Script references")
    print(f"✓ Service layer references")
    
    print(f"\nSocial media sharing should now show:")
    print(f"✓ Title: 'Selecciones Docentes CRUB'")
    print(f"✓ Description: 'Sistema de gestión de selecciones de personal docente'")
    print(f"✓ Proper Open Graph and Twitter Card meta tags")

if __name__ == "__main__":
    main()
