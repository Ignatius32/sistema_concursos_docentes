#!/usr/bin/env python3
"""
Script to update notification logic from legacy password reset to Keycloak-centered approach.
"""

import re

def update_tribunal_notifications():
    """Update the tribunal.py file to use Keycloak notifications."""
    
    file_path = 'app/routes/tribunal.py'
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace the remaining legacy references in the else blocks
    # Pattern 1: Fix the else block in bulk notification
    bulk_pattern = r'(\s+else:\s+# Generate reset token for password setup\s+reset_token = persona\.generate_reset_token\(\)\s+reset_url = url_for\(\'tribunal\.reset_password\', token=reset_token, _external=True\)\s+subject = f"Designación en Tribunal - Concurso #{concurso\.id} - Configuración de Acceso")'
    
    bulk_replacement = '''        else:
            # Send password setup email via Keycloak
            keycloak_admin.send_execute_actions_email(user_id, ['UPDATE_PASSWORD'])
            
            # Prepare custom notification
            login_url = url_for('auth.login', _external=True)
            subject = f"Designación en Tribunal - Concurso #{concurso.id} - Configuración de Acceso"'''
    
    content = re.sub(bulk_pattern, bulk_replacement, content, flags=re.MULTILINE | re.DOTALL)
    
    # Pattern 2: Fix remaining reset_url references
    content = re.sub(r'reset_url = url_for\(\'tribunal\.reset_password\', token=reset_token, _external=True\)', 
                     'login_url = url_for(\'auth.login\', _external=True)', content)
    
    # Pattern 3: Fix reset_url references in HTML templates  
    content = re.sub(r'<a href="{reset_url}"[^>]*><strong>Hacer clic aquí</strong></a>', 
                     'Recibirá un correo de configuración de contraseña desde nuestro sistema de autenticación.', content)
                     
    content = re.sub(r'<a href="{reset_url}"[^>]*>Configurar Contraseña</a>', 
                     'Recibirá un correo de configuración de contraseña desde nuestro sistema de autenticación.', content)
                     
    content = re.sub(r'<a href="{reset_url}"[^>]*>Activar Cuenta y Configurar Contraseña</a>', 
                     'Recibirá un correo de configuración de contraseña desde nuestro sistema de autenticación.', content)
                     
    content = re.sub(r'<a href="{reset_url}"[^>]*>Configurar Nueva Contraseña</a>', 
                     'Recibirá un correo de configuración de contraseña desde nuestro sistema de autenticación.', content)
    
    # Pattern 4: Fix legacy references
    content = re.sub(r'url_for\(\'tribunal\.acceso\', _external=True\)', 
                     'url_for(\'auth.login\', _external=True)', content)
    
    # Pattern 5: Update message template references
    content = re.sub(r'Portal de Tribunal</a>', 'Portal de Acceso</a>', content)
    
    # Write back the updated content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Updated tribunal.py notifications to use Keycloak")

if __name__ == '__main__':
    update_tribunal_notifications()
