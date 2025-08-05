#!/usr/bin/env python3
"""
Script to change only the browser URL paths from /concursos-docentes/ to /selecciones-docentes/
This keeps all server filesystem paths unchanged (like /var/www/concursos-docentes/)
"""

import os
import re

def replace_in_file(file_path, old_text, new_text):
    """Replace text in a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Check if the file contains the old text
        if old_text in content:
            print(f"Updating: {file_path}")
            print(f"  Replacing: {old_text}")
            print(f"  With: {new_text}")
            updated_content = content.replace(old_text, new_text)
            
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(updated_content)
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Main function to perform the URL path migration only."""
    
    print("Migrating ONLY browser URL paths from /concursos-docentes/ to /selecciones-docentes/")
    print("Server filesystem paths (/var/www/concursos-docentes/) will remain unchanged")
    print("=" * 80)
    
    files_updated = 0
    
    # 1. Update APPLICATION_ROOT default values in Python files
    updates = [
        {
            'file': 'app/__init__.py',
            'old': "os.environ.get('APPLICATION_ROOT', '/concursos-docentes')",
            'new': "os.environ.get('APPLICATION_ROOT', '/selecciones-docentes')"
        },
        {
            'file': 'wsgi.py',
            'old': "os.environ.setdefault('APPLICATION_ROOT', '/concursos-docentes')",
            'new': "os.environ.setdefault('APPLICATION_ROOT', '/selecciones-docentes')"
        },
        {
            'file': 'app/config/keycloak_config.py',
            'old': "# e.g., '/concursos-docentes' for production",
            'new': "# e.g., '/selecciones-docentes' for production"
        }
    ]
    
    # 2. Update JavaScript functions that detect the URL path
    js_updates = [
        {
            'file': 'app/templates/concursos/nuevo.html',
            'old': "// Check if we're deployed under /concursos-docentes",
            'new': "// Check if we're deployed under /selecciones-docentes"
        },
        {
            'file': 'app/templates/concursos/nuevo.html',
            'old': "if (path.includes('/concursos-docentes')) {",
            'new': "if (path.includes('/selecciones-docentes')) {"
        },
        {
            'file': 'app/templates/concursos/nuevo.html',
            'old': "return '/concursos-docentes/concursos';",
            'new': "return '/selecciones-docentes/concursos';"
        },
        {
            'file': 'app/templates/concursos/editar.html',
            'old': "// Check if we're deployed under /concursos-docentes",
            'new': "// Check if we're deployed under /selecciones-docentes"
        },
        {
            'file': 'app/templates/concursos/editar.html',
            'old': "if (path.includes('/concursos-docentes')) {",
            'new': "if (path.includes('/selecciones-docentes')) {"
        },
        {
            'file': 'app/templates/concursos/editar.html',
            'old': "return '/concursos-docentes/concursos';",
            'new': "return '/selecciones-docentes/concursos';"
        }
    ]
    
    # 3. Update Apache configuration (URL mappings only)
    apache_updates = [
        {
            'file': 'apache_config.conf',
            'old': '<Location /concursos-docentes>',
            'new': '<Location /selecciones-docentes>'
        },
        {
            'file': 'apache_config.conf',
            'old': 'WSGIScriptAlias /concursos-docentes /var/www/concursos-docentes/wsgi.py',
            'new': 'WSGIScriptAlias /selecciones-docentes /var/www/concursos-docentes/wsgi.py'
        },
        {
            'file': 'apache_config.conf',
            'old': 'Alias /concursos-docentes/static /var/www/concursos-docentes/app/static',
            'new': 'Alias /selecciones-docentes/static /var/www/concursos-docentes/app/static'
        }
    ]
    
    # 4. Update documentation files
    doc_updates = [
        {
            'file': 'apache2_deployment_commands.txt',
            'old': 'https://huayca.crub.uncoma.edu.ar/concursos-docentes/',
            'new': 'https://huayca.crub.uncoma.edu.ar/selecciones-docentes/'
        },
        {
            'file': 'install.sh',
            'old': 'echo "1. Check the application at: https://your-domain.com/concursos-docentes/"',
            'new': 'echo "1. Check the application at: https://your-domain.com/selecciones-docentes/"'
        }
    ]
    
    # Apply all updates
    all_updates = updates + js_updates + apache_updates + doc_updates
    
    for update in all_updates:
        file_path = update['file']
        if os.path.exists(file_path):
            if replace_in_file(file_path, update['old'], update['new']):
                files_updated += 1
        else:
            print(f"Warning: File not found: {file_path}")
    
    print("=" * 80)
    print(f"URL path migration completed!")
    print(f"Files updated: {files_updated}")
    
    print(f"\nWhat was changed:")
    print(f"✓ Browser URL paths: /concursos-docentes → /selecciones-docentes")
    print(f"✓ JavaScript path detection updated")
    print(f"✓ Apache URL mappings updated")
    print(f"✓ APPLICATION_ROOT default values updated")
    print(f"✓ Documentation updated")
    
    print(f"\nWhat was NOT changed (intentionally):")
    print(f"✓ Server directory paths: /var/www/concursos-docentes/ (kept as-is)")
    print(f"✓ Database paths and other filesystem references")
    print(f"✓ Python package names and internal references")
    
    print(f"\nNext steps:")
    print(f"1. Update your .env file: APPLICATION_ROOT=/selecciones-docentes")
    print(f"2. Deploy the updated apache_config.conf to your server")
    print(f"3. Reload Apache: sudo systemctl reload apache2")
    print(f"4. Test at: https://your-domain.com/selecciones-docentes/")
    print(f"5. Your server files stay in /var/www/concursos-docentes/ (no need to move anything)")

if __name__ == "__main__":
    main()
