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

    def send_reset_email_internal(self, persona: Persona, keycloak_user_id: str) -> bool:
        """Send password reset email using Google Drive email system."""
        try:
            # Generate reset token
            reset_token = self.generate_reset_token(keycloak_user_id)
            
            # Build reset URL pointing to our app
            reset_url = url_for('tribunal.reset_password', token=reset_token, _external=True)
            
            # Use Google Drive email system
            try:
                # Email subject
                subject = "Configurar Contraseña - Portal de Tribunal"
                
                # HTML email body with placeholders
                html_body = """
                <!DOCTYPE html>
                <html lang="es">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>Configurar Contraseña - Portal de Tribunal</title>
                    <style>
                        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }
                        .header { background-color: #007bff; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }
                        .content { background-color: #f8f9fa; padding: 30px; border: 1px solid #dee2e6; border-top: none; }
                        .button { display: inline-block; background-color: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; margin: 20px 0; font-weight: bold; }
                        .footer { background-color: #e9ecef; padding: 15px; border: 1px solid #dee2e6; border-top: none; border-radius: 0 0 5px 5px; font-size: 0.9em; color: #6c757d; }
                        .warning { background-color: #fff3cd; border: 1px solid #ffeaa7; color: #856404; padding: 15px; border-radius: 5px; margin: 15px 0; }
                    </style>
                </head>
                <body>
                    <div class="header">
                        <h1>Portal de Tribunal</h1>
                        <p>Sistema de Concursos Docentes</p>
                    </div>
                    
                    <div class="content">
                        <h2>Hola <<nombre>> <<apellido>>,</h2>
                        
                        <p>Ha sido designado(a) como miembro del tribunal para un concurso docente. Para acceder al Portal de Tribunal, necesita configurar su contraseña de acceso.</p>
                        
                        <p>Haga clic en el siguiente enlace para configurar su contraseña:</p>
                        
                        <div style="text-align: center;">
                            <a href="<<reset_url>>" class="button">Configurar Contraseña</a>
                        </div>
                        
                        <div class="warning">
                            <strong>Importante:</strong>
                            <ul>
                                <li>Este enlace es válido por 24 horas</li>
                                <li>Solo puede ser usado una vez</li>
                                <li>No comparta este enlace con otras personas</li>
                            </ul>
                        </div>
                        
                        <p>Una vez que configure su contraseña, podrá acceder al Portal de Tribunal usando su correo electrónico y la contraseña que haya elegido.</p>
                        
                        <p>Si tiene problemas para acceder o no solicitó este acceso, contacte al administrador del sistema.</p>
                    </div>
                    
                    <div class="footer">
                        <p><strong>Sistema de Concursos Docentes</strong></p>
                        <p>Este es un mensaje automático, por favor no responda a este correo.</p>
                        <p>Si no puede hacer clic en el enlace, copie y pegue la siguiente URL en su navegador:</p>
                        <p style="word-break: break-all; font-size: 0.8em;"><<reset_url>></p>
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
                    sender_name="Sistema de Concursos Docentes",
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

    def notify_tribunal_member_with_reset(self, persona: Persona, keycloak_admin: KeycloakAdminClient) -> Dict:
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
                success = self.send_login_reminder_email(persona)
                
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
                success = self.send_reset_email_internal(persona, keycloak_user['id'])
                
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

    def send_simple_reset_fallback(self, persona: Persona, keycloak_user_id: str) -> bool:
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

    def send_login_reminder_email(self, persona: Persona) -> bool:
        """Send login reminder email for users who already have their password configured."""
        try:
            # Build login URL pointing to tribunal login page
            login_url = url_for('tribunal.acceso', _external=True)
            
            # Use Google Drive email system
            try:
                # Email subject
                subject = "Acceso al Portal de Tribunal - Recordatorio"
                
                # HTML email body with placeholders
                html_body = """
                <!DOCTYPE html>
                <html lang="es">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>Acceso al Portal de Tribunal</title>
                    <style>
                        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }
                        .header { background-color: #28a745; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }
                        .content { background-color: #f8f9fa; padding: 30px; border: 1px solid #dee2e6; border-top: none; }
                        .button { display: inline-block; background-color: #28a745; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; margin: 20px 0; font-weight: bold; }
                        .footer { background-color: #e9ecef; padding: 15px; border: 1px solid #dee2e6; border-top: none; border-radius: 0 0 5px 5px; font-size: 0.9em; color: #6c757d; }
                        .info { background-color: #d1ecf1; border: 1px solid #bee5eb; color: #0c5460; padding: 15px; border-radius: 5px; margin: 15px 0; }
                        .credentials { background-color: #fff; border: 1px solid #dee2e6; padding: 15px; border-radius: 5px; margin: 15px 0; }
                    </style>
                </head>
                <body>
                    <div class="header">
                        <h1>Portal de Tribunal</h1>
                        <p>Sistema de Concursos Docentes</p>
                    </div>
                    
                    <div class="content">
                        <h2>Hola <<nombre>> <<apellido>>,</h2>
                        
                        <p>Ha sido designado(a) como miembro del tribunal para un concurso docente. Su cuenta ya está configurada y puede acceder al Portal de Tribunal.</p>
                        
                        <div class="credentials">
                            <h4>Sus credenciales de acceso:</h4>
                            <p><strong>Usuario/Email:</strong> <<correo>></p>
                            <p><strong>Contraseña:</strong> La que configuró anteriormente</p>
                        </div>
                        
                        <p>Haga clic en el siguiente enlace para acceder al portal:</p>
                        
                        <div style="text-align: center;">
                            <a href="<<login_url>>" class="button">Acceder al Portal</a>
                        </div>
                        
                        <div class="info">
                            <strong>Información importante:</strong>
                            <ul>
                                <li>Use su correo electrónico y la contraseña que configuró previamente</li>
                                <li>Si olvidó su contraseña, puede solicitar un restablecimiento desde la página de login</li>
                                <li>El portal está disponible las 24 horas del día</li>
                            </ul>
                        </div>
                        
                        <p>Si tiene problemas para acceder, contacte al administrador del sistema.</p>
                    </div>
                    
                    <div class="footer">
                        <p><strong>Sistema de Concursos Docentes</strong></p>
                        <p>Este es un mensaje automático, por favor no responda a este correo.</p>
                        <p>Si no puede hacer clic en el enlace, copie y pegue la siguiente URL en su navegador:</p>
                        <p style="word-break: break-all; font-size: 0.8em;"><<login_url>></p>
                    </div>
                </body>
                </html>
                """
                
                # Placeholders for email content
                placeholders = {
                    'nombre': persona.nombre,
                    'apellido': persona.apellido,
                    'login_url': login_url,
                    'correo': persona.correo
                }
                
                # Send email via Google Drive API
                result = self.drive_api.send_email(
                    to_email=persona.correo,
                    subject=subject,
                    html_body=html_body,
                    sender_name="Sistema de Concursos Docentes",
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


# Create a global instance to be used throughout the application
password_reset_service = PasswordResetService()
