#!/usr/bin/env python3
"""
Script to migrate from /concursos-docentes/ to /selecciones-docentes/
This script replaces all occurrences of the old path with the new one.
"""

import os
import re
import glob
from pathlib import Path

def replace_in_file(file_path, old_text, new_text):
    """Replace text in a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Check if the file contains the old text
        if old_text in content:
            print(f"Updating: {file_path}")
            updated_content = content.replace(old_text, new_text)
            
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(updated_content)
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Main function to perform the migration."""
    
    # Define the replacements
    replacements = [
        # URL paths
        ('/concursos-docentes', '/selecciones-docentes'),
        ('concursos-docentes', 'selecciones-docentes'),
        # Server directory paths (these should stay the same for the server filesystem)
        # We'll handle Apache config separately
    ]
    
    # Files to process
    files_to_process = [
        # Configuration files
        'wsgi.py',
        'app/__init__.py',
        'app/config/keycloak_config.py',
        
        # Installation and deployment files
        'install.sh',
        'apache2_deployment_commands.txt',
        
        # Template files with JavaScript
        'app/templates/concursos/nuevo.html',
        'app/templates/concursos/editar.html',
    ]
    
    # Special handling for apache_config.conf - we need to be more selective
    apache_replacements = [
        ('<Location /concursos-docentes>', '<Location /selecciones-docentes>'),
        ('WSGIScriptAlias /concursos-docentes', 'WSGIScriptAlias /selecciones-docentes'),
        ('Alias /concursos-docentes/static', 'Alias /selecciones-docentes/static'),
    ]
    
    print("Starting migration from /concursos-docentes/ to /selecciones-docentes/")
    print("=" * 60)
    
    # Process regular files
    files_updated = 0
    for file_path in files_to_process:
        if os.path.exists(file_path):
            for old_text, new_text in replacements:
                if replace_in_file(file_path, old_text, new_text):
                    files_updated += 1
        else:
            print(f"Warning: File not found: {file_path}")
    
    # Special handling for Apache config
    apache_config_path = 'apache_config.conf'
    if os.path.exists(apache_config_path):
        print(f"Updating Apache config: {apache_config_path}")
        try:
            with open(apache_config_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            updated_content = content
            for old_text, new_text in apache_replacements:
                updated_content = updated_content.replace(old_text, new_text)
            
            with open(apache_config_path, 'w', encoding='utf-8') as file:
                file.write(updated_content)
            files_updated += 1
        except Exception as e:
            print(f"Error processing Apache config: {e}")
    
    # Search for any remaining references in other files
    print("\nSearching for any remaining references...")
    remaining_files = []
    
    # Search in Python files
    for py_file in glob.glob('**/*.py', recursive=True):
        if py_file != __file__:  # Skip this script
            try:
                with open(py_file, 'r', encoding='utf-8') as file:
                    content = file.read()
                if '/concursos-docentes' in content or 'concursos-docentes' in content:
                    remaining_files.append(py_file)
            except Exception:
                pass
    
    # Search in HTML files
    for html_file in glob.glob('**/*.html', recursive=True):
        try:
            with open(html_file, 'r', encoding='utf-8') as file:
                content = file.read()
            if '/concursos-docentes' in content or 'concursos-docentes' in content:
                remaining_files.append(html_file)
        except Exception:
            pass
    
    # Search in config files
    for config_file in ['apache_config.conf', 'apache2_deployment_commands.txt', 'install.sh']:
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as file:
                    content = file.read()
                if 'concursos-docentes' in content:
                    remaining_files.append(config_file)
            except Exception:
                pass
    
    print("=" * 60)
    print(f"Migration completed!")
    print(f"Files updated: {files_updated}")
    
    if remaining_files:
        print(f"\nFiles that still contain 'concursos-docentes' references:")
        for file_path in set(remaining_files):
            print(f"  - {file_path}")
        print("\nThese might need manual review to determine if they should be updated.")
        print("Some references (like server filesystem paths) might need to stay the same.")
    else:
        print("\nNo remaining references found!")
    
    print(f"\nNext steps:")
    print(f"1. Review the updated files")
    print(f"2. Update your .env file APPLICATION_ROOT to '/selecciones-docentes'")
    print(f"3. Deploy the updated apache_config.conf to your server")
    print(f"4. Reload Apache configuration")
    print(f"5. Test the application at the new URL")

if __name__ == "__main__":
    main()
