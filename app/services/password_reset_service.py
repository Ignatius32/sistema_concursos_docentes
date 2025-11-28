"""
Password reset service for tribunal members.

This module handles password reset token generation, verification, and email sending
for tribunal members using Google Drive integration.
"""

import secrets
import hashlib
import os
import base64
from datetime import datetime, timedelta
from typing import Dict, Optional
from flask import url_for, current_app, flash

from app.models.models import Persona
from app.integrations.google_drive import GoogleDriveAPI
from app.integrations.keycloak_admin_client import KeycloakAdminClient
from app.services.placeholder_resolver import get_core_placeholders


class PasswordResetService:
    """Service class for handling password reset functionality."""
    
    def __init__(self):
        self.drive_api = GoogleDriveAPI()
    
    def generate_reset_token(self, user_id: str, expiry_hours: int = 24) -> str:
        """Generate a secure reset token for password reset."""
        # Create a random token
        random_token = secrets.token_urlsafe(32)
        
        # Create expiry timestamp
        expiry = datetime.utcnow() + timedelta(hours=expiry_hours)
        expiry_str = expiry.isoformat()
        
        # Create the payload: user_id|expiry|random_token
        payload = f"{user_id}|{expiry_str}|{random_token}"
        
        # Create a hash using a secret key (you should store this in config)
        secret_key = os.environ.get('RESET_TOKEN_SECRET', 'your-secret-key-here')
        signature = hashlib.sha256(f"{payload}|{secret_key}".encode()).hexdigest()
        
        # Combine payload and signature
        token = f"{payload}|{signature}"
        
        # URL-safe base64 encode
        return base64.urlsafe_b64encode(token.encode()).decode()

    def verify_reset_token(self, token: str) -> Dict:
        """Verify and decode a reset token."""
        try:
            # Decode from base64
            decoded = base64.urlsafe_b64decode(token.encode()).decode()
            
            # Split the token
            parts = decoded.split('|')
            if len(parts) != 4:
                return {'valid': False, 'error': 'Invalid token format'}
            
            user_id, expiry_str, random_token, signature = parts
            
            # Verify signature
            secret_key = os.environ.get('RESET_TOKEN_SECRET', 'your-secret-key-here')
            expected_signature = hashlib.sha256(f"{user_id}|{expiry_str}|{random_token}|{secret_key}".encode()).hexdigest()
            
            if signature != expected_signature:
                return {'valid': False, 'error': 'Invalid token signature'}
            
            # Check expiry
            expiry = datetime.fromisoformat(expiry_str)
            if datetime.utcnow() > expiry:
                return {'valid': False, 'error': 'Token has expired'}
            
            return {
                'valid': True,
                'user_id': user_id,
                'expiry': expiry
            }
        except Exception as e:
            return {'valid': False, 'error': f'Token verification failed: {str(e)}'}    
    def send_login_reminder_email(self, persona: Persona, concurso_id: int = None) -> bool:
        """Send login reminder email for users who already have their password configured."""
        try:
            # Build login URL pointing to tribunal login page
            login_url = url_for('tribunal.acceso', _external=True)
            
            # Get concurso placeholders if concurso_id is provided
            concurso_placeholders = {}
            if concurso_id:
                from app.services.placeholder_resolver import get_core_placeholders
                concurso_placeholders = get_core_placeholders(concurso_id, persona.id)
            
            # Use Google Drive email system
            try:
                # Email subject with concurso info
                if concurso_id and 'categoria_nombre' in concurso_placeholders:
                    subject = f"Portal de Tribunal - Acceso a Concurso {concurso_placeholders.get('categoria_nombre', '')}"
                else:
                    subject = "Acceso al Portal de Tribunal - Recordatorio"
                
                # HTML email body with unified style and concurso data
                html_body = """
                <!DOCTYPE html>
                <html lang=\"es\">
                <head>
                    <meta charset=\"UTF-8\">
                    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
                    <title>Portal de Tribunal - Acceso</title>
                    <style>
                        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; max-width: 480px; margin: 0 auto; padding: 20px; background-color: #f5f5f5; }
                        .email-container { background-color: white; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); max-width: 480px; margin: 0 auto; }
                        .header { background: linear-gradient(135deg, #28a745 0%, #20c997 100%); color: white; padding: 30px 20px; text-align: center; }
                        .header h1 { margin: 0; font-size: 24px; font-weight: 600; }
                        .header p { margin: 8px 0 0 0; opacity: 0.9; font-size: 15px; }
                        .content { padding: 24px; }
                        .greeting { font-size: 18px; color: #2c3e50; margin-bottom: 18px; font-weight: 500; }
                        .concurso-info { background-color: #e8f5e8; border-left: 4px solid #28a745; padding: 16px; margin: 16px 0; border-radius: 0 4px 4px 0; }
                        .concurso-info h4 { color: #28a745; margin: 0 0 12px 0; font-size: 15px; font-weight: 600; }
                        .credentials { background-color: #f8f9fa; border: 2px solid #e9ecef; padding: 16px; border-radius: 6px; margin: 16px 0; }
                        .credentials h4 { color: #495057; margin: 0 0 12px 0; font-size: 15px; }
                        .button { display: inline-block; background: linear-gradient(135deg, #28a745 0%, #20c997 100%); color: white !important; padding: 12px 22px; text-decoration: none; border-radius: 6px; margin: 20px 0; font-weight: 600; font-size: 15px; transition: transform 0.2s; }
                        .button:hover { transform: translateY(-2px); }
                        .info-box { background-color: #d1ecf1; border: 1px solid #bee5eb; color: #0c5460; padding: 16px; border-radius: 6px; margin: 16px 0; }
                        .info-box strong { color: #0a4d55; }
                        .footer { background-color: #f8f9fa; padding: 16px; text-align: center; font-size: 13px; color: #6c757d; border-top: 1px solid #e9ecef; }
                        .footer strong { color: #495057; }
                        .url-break { word-break: break-all; font-size: 11px; color: #6c757d; margin-top: 8px; }
                        ul { padding-left: 16px; }
                        li { margin-bottom: 7px; }
                    </style>
                </head>
                <body>                    <div class=\"email-container\">
                        <div class="header">
                            <h1>Portal de Tribunal</h1>
                            <p>Selecciones Docentes CRUB UNCo</p>
                        </div>
                        
                        <div class="content">
                            <div class="greeting">Hola <<nombre>> <<apellido>>,</div>
                            
                            <p>Ha sido designado(a) como <strong>miembro del tribunal</strong> para el siguiente concurso docente. Su cuenta ya está configurada y puede acceder al Portal de Tribunal.</p>
                            
                            <!-- Concurso Information Section -->
                            <<concurso_section>>
                              <div class="credentials">
                                <h4>Sus credenciales de acceso:</h4>
                                <p><strong>Usuario/Email:</strong> <<correo>></p>
                                <p><strong>Contraseña:</strong> La que configuró anteriormente</p>
                            </div>
                            
                            <p>Haga clic en el siguiente enlace para acceder al portal:</p>
                              <div style="text-align: center;">
                                <a href="<<login_url>>" class="button">Acceder al Portal</a>
                            </div>
                              <div class="info-box">
                                <strong>Informacion importante:</strong>
                                <ul>
                                    <li>Use su correo electrónico y la contraseña que configuró previamente</li>
                                    <li>Si olvidó su contraseña, puede solicitar un restablecimiento desde la página de login</li>
                                    <li>El portal está disponible las 24 horas del día</li>
                                    <li>Podrá acceder a toda la información del concurso y realizar las evaluaciones correspondientes</li>
                                </ul>
                            </div>
                            
                            <p>Si tiene problemas para acceder, contacte al administrador del sistema.</p>
                        </div>
                        
                        <div class="footer">
                            <p><strong>Selecciones Docentes CRUB UNCo</strong></p>
                            <p>Este es un mensaje automático, por favor no responda a este correo.</p>
                            <div class="url-break">Si no puede hacer clic en el enlace, copie y pegue la siguiente URL en su navegador:<br><<login_url>></div>
                        </div>
                    </div>
                </body>
                </html>
                """                
                # Build concurso info section
                concurso_section = ""
                if concurso_id and concurso_placeholders:
                    concurso_section = f"""
                    <div class="concurso-info">
                        <h4>Informacion del Concurso</h4>
                        <p><strong>Departamento:</strong> {concurso_placeholders.get('departamento_nombre', 'N/A')}</p>
                        <p><strong>Area:</strong> {concurso_placeholders.get('area', 'N/A')}</p>
                        <p><strong>Orientacion:</strong> {concurso_placeholders.get('orientacion', 'N/A')}</p>
                        <p><strong>Cantidad de Cargos:</strong> {concurso_placeholders.get('cant_cargos_texto', 'N/A')}</p>
                    </div>
                    """
                
                # Placeholders for email content
                placeholders = {
                    'nombre': persona.nombre,
                    'apellido': persona.apellido,
                    'login_url': login_url,
                    'correo': persona.correo,
                    'concurso_section': concurso_section
                }
                
                # Add all concurso placeholders
                if concurso_placeholders:
                    placeholders.update(concurso_placeholders)
                
                # Send email via Google Drive API
                result = self.drive_api.send_email(
                    to_email=persona.correo,
                    subject=subject,
                    html_body=html_body,
                    sender_name="Selecciones Docentes CRUB UNCo",
                    placeholders=placeholders
                )
                
                current_app.logger.info(f"Login reminder email sent successfully to {persona.correo} via Google Drive")
                current_app.logger.info(f"Login URL: {login_url}")
                
                # Show success message in development
                if current_app.debug:
                    flash(f'Email de recordatorio enviado a {persona.correo}. Login URL: <a href="{login_url}" target="_blank">{login_url}</a>', 'info')
                
                return True
                
            except Exception as email_error:
                current_app.logger.error(f"Failed to send login reminder email via Google Drive: {email_error}")
                
                # Fallback: Log the URL for manual testing
                current_app.logger.info(f"EMAIL FALLBACK - Login reminder URL for {persona.correo}: {login_url}")
                
                # In development, show the link in the UI as fallback
                if current_app.debug:
                    flash(f'Error enviando email, pero enlace generado: <a href="{login_url}" target="_blank">Acceder al portal - {persona.correo}</a>', 'warning')
                
                return True  # Return True because link was generated successfully
            
        except Exception as e:            
            current_app.logger.error(f"Error generating login reminder email: {e}")
            return False

    def send_password_reset_email(self, persona: Persona, keycloak_user_id: str) -> bool:
        """Send a simple password reset email for users who need to reset their password."""
        try:
            # Generate reset token
            reset_token = self.generate_reset_token(keycloak_user_id)
            
            # Build reset URL pointing to our app
            reset_url = url_for('tribunal.reset_password', token=reset_token, _external=True)
            
            # Use Google Drive email system
            try:
                # Simple subject for password reset
                subject = "Restablecer Contraseña"
                
                # Simple HTML email body focused on password reset
                html_body = """
                <!DOCTYPE html>
                <html lang=\"es\">
                <head>
                    <meta charset=\"UTF-8\">
                    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
                    <title>Restablecer Contraseña</title>
                    <style>
                        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; max-width: 480px; margin: 0 auto; padding: 20px; background-color: #f5f5f5; }
                        .email-container { background-color: white; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); max-width: 480px; margin: 0 auto; }
                        .header { background: linear-gradient(135deg, #2563eb 0%, #3b82f6 100%); color: white; padding: 30px 20px; text-align: center; }
                        .header h1 { margin: 0; font-size: 24px; font-weight: 600; }
                        .header p { margin: 8px 0 0 0; opacity: 0.9; font-size: 15px; }
                        .content { padding: 24px; }
                        .greeting { font-size: 18px; color: #2c3e50; margin-bottom: 18px; font-weight: 500; }
                        .button { display: inline-block; background: linear-gradient(135deg, #2563eb 0%, #3b82f6 100%); color: white !important; padding: 12px 22px; text-decoration: none; border-radius: 6px; margin: 20px 0; font-weight: 600; font-size: 15px; transition: transform 0.2s; }
                        .button:hover { transform: translateY(-2px); }
                        .warning-box { background-color: #fff3cd; border: 1px solid #ffeaa7; color: #856404; padding: 16px; border-radius: 6px; margin: 16px 0; }
                        .warning-box strong { color: #7c4e00; }
                        .info-box { background-color: #d1ecf1; border: 1px solid #bee5eb; color: #0c5460; padding: 16px; border-radius: 6px; margin: 16px 0; }
                        .info-box strong { color: #0a4d55; }
                        .footer { background-color: #f8f9fa; padding: 16px; text-align: center; font-size: 13px; color: #6c757d; border-top: 1px solid #e9ecef; }
                        .footer strong { color: #495057; }
                        .url-break { word-break: break-all; font-size: 11px; color: #6c757d; margin-top: 8px; }
                        ul { padding-left: 16px; }
                        li { margin-bottom: 7px; }
                    </style>
                </head>
                <body>
                    <div class=\"email-container\">
                        <div class=\"header\">
                            <h1>Restablecer Contraseña</h1>
                            <p>Sistema de Selecciones Docentes CRUB</p>
                        </div>
                        <div class=\"content\">
                            <div class=\"greeting\">Hola <<nombre>> <<apellido>>,</div>
                            <p>Hemos recibido una solicitud para restablecer la contraseña de su cuenta.</p>
                            <p>Si usted solicitó restablecer su contraseña, haga clic en el siguiente enlace:</p>
                            <div style=\"text-align: center;\">
                                <a href=\"<<reset_url>>\" class=\"button\">Restablecer Contraseña</a>
                            </div>
                            <div class=\"warning-box\">
                                <strong>Importante:</strong>
                                <ul>
                                    <li>Este enlace es válido por <strong>24 horas</strong></li>
                                    <li>Solo puede ser usado <strong>una vez</strong></li>
                                    <li>Si no solicitó este restablecimiento, ignore este correo</li>
                                </ul>
                            </div>
                            <div class=\"info-box\">
                                <strong>Seguridad:</strong> Su contraseña actual permanece sin cambios hasta que complete el proceso de restablecimiento usando este enlace.
                            </div>
                            <p>Si no solicitó restablecer su contraseña o tiene alguna duda, puede ignorar este correo o contactar al administrador del sistema.</p>
                        </div>
                        <div class=\"footer\">
                            <p><strong>Sistema de Selecciones Docentes CRUB</strong></p>
                            <p>Este es un mensaje automático, por favor no responda a este correo.</p>
                            <div class=\"url-break\">Si no puede hacer clic en el enlace, copie y pegue la siguiente URL en su navegador:<br><<reset_url>></div>
                        </div>
                    </div>
                </body>
                </html>
                """
                # Placeholders for email content
                placeholders = {
                    'nombre': persona.nombre,
                    'apellido': persona.apellido,
                    'reset_url': reset_url,
                    'correo': persona.correo
                }
                
                # Send email via Google Drive API
                result = self.drive_api.send_email(
                    to_email=persona.correo,
                    subject=subject,
                    html_body=html_body,
                    sender_name="Selecciones Docentes CRUB UNCo",
                    placeholders=placeholders
                )
                
                current_app.logger.info(f"Password reset email sent successfully to {persona.correo} via Google Drive")
                current_app.logger.info(f"Reset URL: {reset_url}")
                
                # Show success message in development
                if current_app.debug:
                    flash(f'Email de restablecimiento enviado a {persona.correo}. Reset URL: <a href="{reset_url}" target="_blank">{reset_url}</a>', 'info')
                
                return True
                
            except Exception as email_error:
                current_app.logger.error(f"Failed to send password reset email via Google Drive: {email_error}")
                
                # Fallback: Log the URL for manual testing
                current_app.logger.info(f"EMAIL FALLBACK - Password reset URL for {persona.correo}: {reset_url}")
                current_app.logger.info(f"Reset token: {reset_token}")
                
                # In development, show the link in the UI as fallback
                if current_app.debug:
                    flash(f'Error enviando email, pero enlace generado: <a href="{reset_url}" target="_blank">Restablecer contraseña para {persona.correo}</a>', 'warning')
                
                return True  # Return True because token was generated successfully
            
        except Exception as e:
            current_app.logger.error(f"Error generating password reset email: {e}")
            return False

    def send_reset_email_internal(self, persona: Persona, keycloak_user_id: str, concurso_id: int = None) -> bool:
        """Send password reset email using Google Drive email system."""
        try:
            # Generate reset token
            reset_token = self.generate_reset_token(keycloak_user_id)
              # Build reset URL pointing to our app
            reset_url = url_for('tribunal.reset_password', token=reset_token, _external=True)
            
            # Get concurso placeholders if concurso_id is provided
            concurso_placeholders = {}
            if concurso_id:
                from app.services.placeholder_resolver import get_core_placeholders
                concurso_placeholders = get_core_placeholders(concurso_id, persona.id)
            
            # Use Google Drive email system
            try:
                # Email subject with concurso info
                if concurso_id and 'categoria_nombre' in concurso_placeholders:
                    subject = f"Portal de Tribunal - Configurar Acceso a Concurso {concurso_placeholders.get('categoria_nombre', '')}"
                else:
                    subject = "Configurar Contraseña - Portal de Tribunal"
                
                # HTML email body with unified style and concurso data
                html_body = """
                <!DOCTYPE html>
                <html lang=\"es\">
                <head>
                    <meta charset=\"UTF-8\">
                    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
                    <title>Portal de Tribunal - Configurar Acceso</title>
                    <style>
                        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; max-width: 480px; margin: 0 auto; padding: 20px; background-color: #f5f5f5; }
                        .email-container { background-color: white; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); max-width: 480px; margin: 0 auto; }
                        .header { background: linear-gradient(135deg, #2563eb 0%, #3b82f6 100%); color: white; padding: 30px 20px; text-align: center; }
                        .header h1 { margin: 0; font-size: 24px; font-weight: 600; }
                        .header p { margin: 8px 0 0 0; opacity: 0.9; font-size: 15px; }
                        .content { padding: 24px; }
                        .greeting { font-size: 18px; color: #2c3e50; margin-bottom: 18px; font-weight: 500; }
                        .concurso-info { background-color: #e7f1ff; border-left: 4px solid #2563eb; padding: 16px; margin: 16px 0; border-radius: 0 4px 4px 0; }
                        .concurso-info h4 { color: #2563eb; margin: 0 0 12px 0; font-size: 15px; font-weight: 600; }
                        .button { display: inline-block; background: linear-gradient(135deg, #2563eb 0%, #3b82f6 100%); color: white !important; padding: 12px 22px; text-decoration: none; border-radius: 6px; margin: 20px 0; font-weight: 600; font-size: 15px; transition: transform 0.2s; }
                        .button:hover { transform: translateY(-2px); }
                        .warning-box { background-color: #fff3cd; border: 1px solid #ffeaa7; color: #856404; padding: 16px; border-radius: 6px; margin: 16px 0; }
                        .warning-box strong { color: #7c4e00; }
                        .info-box { background-color: #d1ecf1; border: 1px solid #bee5eb; color: #0c5460; padding: 16px; border-radius: 6px; margin: 16px 0; }
                        .info-box strong { color: #0a4d55; }
                        .footer { background-color: #f8f9fa; padding: 16px; text-align: center; font-size: 13px; color: #6c757d; border-top: 1px solid #e9ecef; }
                        .footer strong { color: #495057; }
                        .url-break { word-break: break-all; font-size: 11px; color: #6c757d; margin-top: 8px; }
                        ul { padding-left: 16px; }
                        li { margin-bottom: 7px; }
                    </style>
                </head>
                <body>
                    <div class=\"email-container\">
                        <div class=\"header\">
                            <h1>Portal de Tribunal</h1>
                            <p>Selecciones Docentes CRUB UNCo</p>
                        </div>
                        <div class=\"content\">
                            <div class=\"greeting\">Hola <<nombre>> <<apellido>>,</div>
                            <p>Ha sido designado(a) como <strong>miembro del tribunal</strong> para el siguiente concurso docente. Para acceder al Portal de Tribunal, necesita configurar su contraseña de acceso.</p>
                            <!-- Concurso Information Section -->
                            <<concurso_section>>
                            <p>Haga clic en el siguiente enlace para configurar su contraseña:</p>
                            <div style=\"text-align: center;\">
                                <a href=\"<<reset_url>>\" class=\"button\">Configurar Contraseña</a>
                            </div>
                            <div class=\"warning-box\">
                                <strong>Importante - Configuración de Acceso:</strong>
                                <ul>
                                    <li>Este enlace es válido por <strong>24 horas</strong></li>
                                    <li>Solo puede ser usado <strong>una vez</strong></li>
                                    <li>No comparta este enlace con otras personas</li>
                                    <li>Una vez configurada su contraseña, podrá acceder con su correo electrónico</li>
                                </ul>
                            </div>
                            <div class=\"info-box\">
                                <strong>Después de configurar su contraseña:</strong>
                                <ul>
                                    <li>Podrá acceder al Portal de Tribunal las 24 horas</li>
                                    <li>Tendrá acceso a toda la información del concurso</li>
                                    <li>Podrá realizar las evaluaciones correspondientes a su rol</li>
                                    <li>Recibirá notificaciones sobre el progreso del concurso</li>
                                </ul>
                            </div>
                            <p>Si tiene problemas para acceder o no solicitó este acceso, contacte al administrador del sistema.</p>
                        </div>
                        <div class=\"footer\">
                            <p><strong>Selecciones Docentes CRUB UNCo</strong></p>
                            <p>Este es un mensaje automático, por favor no responda a este correo.</p>
                            <div class=\"url-break\">Si no puede hacer clic en el enlace, copie y pegue la siguiente URL en su navegador:<br><<reset_url>></div>
                        </div>
                    </div>
                </body>
                </html>
                """
                # Build concurso info section
                concurso_section = ""
                if concurso_id and concurso_placeholders:
                    concurso_section = f"""
                    <div class="concurso-info">
                        <h4>Informacion del Concurso</h4>
                        <p><strong>Departamento:</strong> {concurso_placeholders.get('departamento_nombre', 'N/A')}</p>
                        <p><strong>Area:</strong> {concurso_placeholders.get('area', 'N/A')}</p>
                        <p><strong>Orientacion:</strong> {concurso_placeholders.get('orientacion', 'N/A')}</p>
                        <p><strong>Cantidad de Cargos:</strong> {concurso_placeholders.get('cant_cargos_texto', 'N/A')}</p>
                    </div>
                    """
                
                # Placeholders for email content
                placeholders = {
                    'nombre': persona.nombre,
                    'apellido': persona.apellido,
                    'reset_url': reset_url,
                    'correo': persona.correo,
                    'concurso_section': concurso_section
                }
                
                # Add all concurso placeholders
                if concurso_placeholders:
                    placeholders.update(concurso_placeholders)
                
                # Send email via Google Drive API
                result = self.drive_api.send_email(
                    to_email=persona.correo,
                    subject=subject,
                    html_body=html_body,
                    sender_name="Selecciones Docentes CRUB UNCo",
                    placeholders=placeholders
                )
                
                current_app.logger.info(f"Password reset email sent successfully to {persona.correo} via Google Drive")
                current_app.logger.info(f"Reset URL: {reset_url}")
                
                # Show success message in development
                if current_app.debug:
                    flash(f'Email de configuración enviado a {persona.correo}. Reset URL: <a href="{reset_url}" target="_blank">{reset_url}</a>', 'info')
                
                return True
                
            except Exception as email_error:
                current_app.logger.error(f"Failed to send email via Google Drive: {email_error}")
                
                # Fallback: Log the URL for manual testing
                current_app.logger.info(f"EMAIL FALLBACK - Password reset URL for {persona.correo}: {reset_url}")
                current_app.logger.info(f"Reset token: {reset_token}")
                
                # In development, show the link in the UI as fallback
                if current_app.debug:
                    flash(f'Error enviando email, pero enlace generado: <a href="{reset_url}" target="_blank">Configurar contraseña para {persona.correo}</a>', 'warning')
                
                return True  # Return True because token was generated successfully
            
        except Exception as e:
            current_app.logger.error(f"Error generating reset email: {e}")
            return False

    def notify_tribunal_member_with_reset(self, persona: Persona, keycloak_admin: KeycloakAdminClient, concurso_id: int = None) -> Dict:
        """
        Notify a tribunal member with appropriate email based on their password status.
        - If user has password configured: sends login reminder email
        - If user needs password configuration: sends password reset email with token
        Returns dict with success status and message.
        """
        try:
            if not persona.correo:
                return {
                    'success': False,
                    'message': f'{persona.nombre} {persona.apellido} no tiene correo registrado'
                }
            
            # Find user in Keycloak by email
            keycloak_user = keycloak_admin.get_user_by_email(persona.correo)        
            if not keycloak_user:
                return {
                    'success': False,
                    'message': f'Usuario {persona.nombre} {persona.apellido} no encontrado en Keycloak.'
                }
            
            # Check password status to determine which email to send
            password_status = keycloak_admin.get_user_password_status(keycloak_user['id'])
            if password_status.get('has_password', False):
                # User already has password configured - send login reminder
                success = self.send_login_reminder_email(persona, concurso_id)
                
                if success:
                    return {
                        'success': True,
                        'message': f'Email de acceso enviado a {persona.nombre} {persona.apellido} (ya tiene contraseña configurada).',
                        'keycloak_user_id': keycloak_user['id'],
                        'email_type': 'login_reminder'
                    }
                else:
                    return {
                        'success': False,
                        'message': f'Error al enviar email de acceso a {persona.nombre} {persona.apellido}.'
                    }
            else:
                # User needs password configuration - send reset email with token
                success = self.send_reset_email_internal(persona, keycloak_user['id'], concurso_id)
                
                if success:
                    return {
                        'success': True,
                        'message': f'Email de configuración enviado a {persona.nombre} {persona.apellido} via Drive.',
                        'keycloak_user_id': keycloak_user['id'],
                        'email_type': 'password_reset'
                    }
                else:
                    return {
                        'success': False,
                        'message': f'Error al enviar email a {persona.nombre} {persona.apellido}.'
                    }
                
        except Exception as e:
            return {
                'success': False,
                'message': f'Error procesando {persona.nombre} {persona.apellido}: {str(e)}'
            }

    def send_simple_reset_fallback(self, persona: Persona, keycloak_user_id: str, concurso_id: int = None) -> bool:
        """Simple fallback method that generates token and logs it without Keycloak API calls."""
        try:
            # Generate reset token
            reset_token = self.generate_reset_token(keycloak_user_id)
            
            # Build reset URL
            reset_url = url_for('tribunal.reset_password', token=reset_token, _external=True)
            
            # Log the information for manual processing
            current_app.logger.info(f"Password reset requested for {persona.nombre} {persona.apellido}")
            current_app.logger.info(f"Email: {persona.correo}")
            current_app.logger.info(f"Reset URL: {reset_url}")
            current_app.logger.info(f"Token: {reset_token}")
            
            # In debug mode, show the link in the UI
            if current_app.debug:
                flash(f'Password reset link for {persona.nombre} {persona.apellido}: <a href="{reset_url}" target="_blank">Reset Password</a>', 'info')
            
            # You can implement actual email sending here without Keycloak
            # For example, using Flask-Mail or any other email service
            
            return True
            
        except Exception as e:
            current_app.logger.error(f"Error in fallback reset email: {e}")
            return False

    def notify_multiple_tribunal_members(self, personas_and_keycloak_ids: list, keycloak_admin: KeycloakAdminClient, concurso_id: int = None) -> Dict:
        """
        Notify multiple tribunal members with appropriate emails based on their password status.
        Args:
            personas_and_keycloak_ids: List of tuples (persona, keycloak_user_id)
            keycloak_admin: KeycloakAdminClient instance
        Returns:
            Dict with summary of results and detailed list of outcomes
        """
        results = {
            'total_processed': 0,
            'successful_login_reminders': 0,
            'successful_password_resets': 0,
            'failed': 0,
            'details': []
        }
        
        for persona, keycloak_user_id in personas_and_keycloak_ids:
            try:
                # Check password status to determine which email to send
                password_status = keycloak_admin.get_user_password_status(keycloak_user_id)
                if password_status.get('has_password', False):
                    # User already has password configured - send login reminder
                    success = self.send_login_reminder_email(persona, concurso_id)
                    
                    if success:
                        results['successful_login_reminders'] += 1
                        results['details'].append({
                            'persona': f"{persona.nombre} {persona.apellido}",
                            'email': persona.correo,
                            'status': 'success',
                            'email_type': 'login_reminder',
                            'message': 'Email de acceso enviado (ya tiene contraseña configurada)'
                        })
                    else:
                        results['failed'] += 1
                        results['details'].append({
                            'persona': f"{persona.nombre} {persona.apellido}",
                            'email': persona.correo,
                            'status': 'failed',
                            'email_type': 'login_reminder',
                            'message': 'Error al enviar email de acceso'
                        })                
                else:
                    # User needs password configuration - send reset email with token
                    success = self.send_reset_email_internal(persona, keycloak_user_id, concurso_id)
                    
                    if success:
                        results['successful_password_resets'] += 1
                        results['details'].append({
                            'persona': f"{persona.nombre} {persona.apellido}",
                            'email': persona.correo,
                            'status': 'success',
                            'email_type': 'password_reset',
                            'message': 'Email de configuración enviado'
                        })
                    else:
                        results['failed'] += 1
                        results['details'].append({
                            'persona': f"{persona.nombre} {persona.apellido}",
                            'email': persona.correo,
                            'status': 'failed',
                            'email_type': 'password_reset',
                            'message': 'Error al enviar email de configuración'
                        })
                
                results['total_processed'] += 1
                
            except Exception as e:
                results['failed'] += 1
                results['details'].append({
                    'persona': f"{persona.nombre} {persona.apellido}",
                    'email': persona.correo,
                    'status': 'failed',
                    'email_type': 'unknown',
                    'message': f'Error procesando: {str(e)}'
                })
                results['total_processed'] += 1
        
        return results


# Create a global instance to be used throughout the application
password_reset_service = PasswordResetService()
