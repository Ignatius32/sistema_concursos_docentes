#!/usr/bin/env python3
"""
Fix script to revert server filesystem paths back to /var/www/concursos-docentes/
while keeping browser URL paths as /selecciones-docentes/
"""

import os
import re

def replace_in_file(file_path, old_text, new_text):
    """Replace text in a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        if old_text in content:
            print(f"Fixing: {file_path}")
            print(f"  Reverting: {old_text}")
            print(f"  Back to: {new_text}")
            updated_content = content.replace(old_text, new_text)
            
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(updated_content)
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Fix the filesystem paths while keeping URL paths correct."""
    
    print("Fixing server filesystem paths back to /var/www/concursos-docentes/")
    print("Browser URL paths will remain as /selecciones-docentes/")
    print("=" * 70)
    
    files_fixed = 0
    
    # Fix install.sh - revert all server filesystem paths
    install_fixes = [
        ('cd /var/www/selecciones-docentes', 'cd /var/www/concursos-docentes'),
        ('chown -R www-data:www-data /var/www/selecciones-docentes', 'chown -R www-data:www-data /var/www/concursos-docentes'),
        ('chmod -R 755 /var/www/selecciones-docentes', 'chmod -R 755 /var/www/concursos-docentes'),
        ('chmod -R 644 /var/www/selecciones-docentes/app/static', 'chmod -R 644 /var/www/concursos-docentes/app/static'),
        ('chmod 600 /var/www/selecciones-docentes/.env', 'chmod 600 /var/www/concursos-docentes/.env'),
        ('chmod -R 700 /var/www/selecciones-docentes/instance', 'chmod -R 700 /var/www/concursos-docentes/instance'),
        ('sudo -u www-data /var/www/selecciones-docentes/venv/bin/python', 'sudo -u www-data /var/www/concursos-docentes/venv/bin/python'),
        ("sys.path.insert(0, '/var/www/selecciones-docentes')", "sys.path.insert(0, '/var/www/concursos-docentes')"),
        ('echo "3. Check application logs: sudo tail -f /var/www/selecciones-docentes/app.log"', 'echo "3. Check application logs: sudo tail -f /var/www/concursos-docentes/app.log"'),
    ]
    
    # Fix apache2_deployment_commands.txt
    apache_doc_fixes = [
        ('sudo mkdir -p /var/www/selecciones-docentes', 'sudo mkdir -p /var/www/concursos-docentes'),
        ('sudo cp -r /path/to/local/sistema_concursos_docentes/* /var/www/selecciones-docentes/', 'sudo cp -r /path/to/local/sistema_concursos_docentes/* /var/www/concursos-docentes/'),
        ('sudo chown -R www-data:www-data /var/www/selecciones-docentes', 'sudo chown -R www-data:www-data /var/www/concursos-docentes'),
        ('sudo chmod -R 755 /var/www/selecciones-docentes', 'sudo chmod -R 755 /var/www/concursos-docentes'),
        ('cd /var/www/selecciones-docentes', 'cd /var/www/concursos-docentes'),
        ('sudo nano /var/www/selecciones-docentes/.env', 'sudo nano /var/www/concursos-docentes/.env'),
        ('WSGIDaemonProcess concursos_docentes_app python-home=/var/www/selecciones-docentes/venv python-path=/var/www/selecciones-docentes', 'WSGIDaemonProcess concursos_docentes_app python-home=/var/www/concursos-docentes/venv python-path=/var/www/concursos-docentes'),
    ]
    
    # Apply fixes to install.sh
    if os.path.exists('install.sh'):
        for old_text, new_text in install_fixes:
            if replace_in_file('install.sh', old_text, new_text):
                files_fixed += 1
    
    # Apply fixes to apache2_deployment_commands.txt
    if os.path.exists('apache2_deployment_commands.txt'):
        for old_text, new_text in apache_doc_fixes:
            if replace_in_file('apache2_deployment_commands.txt', old_text, new_text):
                files_fixed += 1
    
    print("=" * 70)
    print(f"Fix completed! Changes made: {files_fixed}")
    
    print(f"\nCurrent configuration:")
    print(f"✓ Browser URLs: /selecciones-docentes/ (what users see)")
    print(f"✓ Server filesystem: /var/www/concursos-docentes/ (where files are stored)")
    print(f"✓ Log file: /var/www/concursos-docentes/app.log")
    print(f"✓ Virtual environment: /var/www/concursos-docentes/venv/")
    
    print(f"\nYour apache_config.conf is correct - it maps:")
    print(f"  Browser: /selecciones-docentes → Server: /var/www/concursos-docentes/")
    
    print(f"\nNext steps:")
    print(f"1. Deploy this fixed code to your server")
    print(f"2. Your server directory /var/www/concursos-docentes/ stays as-is")
    print(f"3. Users will access: https://your-domain.com/selecciones-docentes/")

if __name__ == "__main__":
    main()
