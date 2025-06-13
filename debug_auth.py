#!/usr/bin/env python3
"""
Debug script to check Keycloak authentication status and roles
"""
from flask import Flask, g, session
from app import create_app
from app.utils.keycloak_auth import get_current_user_info, get_current_user_roles, is_admin

app = create_app()

@app.route('/debug/auth')
def debug_auth():
    """Debug route to check authentication status"""
    
    # Get authentication info
    user_info = get_current_user_info()
    user_roles = get_current_user_roles()
    is_authenticated = g.get('is_authenticated', False)
    admin_status = is_admin()
    
    debug_info = {
        'is_authenticated': is_authenticated,
        'user_info': user_info,
        'user_roles': user_roles,
        'is_admin': admin_status,
        'g_user_roles': g.get('user_roles', []),
        'g_is_authenticated': g.get('is_authenticated', False),
        'session_token_present': 'keycloak_token' in session
    }
    
    return f"""
    <h1>Keycloak Authentication Debug</h1>
    <pre>{debug_info}</pre>
    
    <h2>Template Context Variables:</h2>
    <p>keycloak_is_authenticated: {g.get('is_authenticated', False)}</p>
    <p>keycloak_is_admin: {admin_status}</p>
    <p>keycloak_user_roles: {user_roles}</p>
    
    <hr>
    <a href="/">Back to Home</a>
    """

if __name__ == '__main__':
    with app.app_context():
        print("Debug auth info:")
        print("Roles configured:")
        from app.config.keycloak_config import KeycloakConfig
        print(f"Admin role: {KeycloakConfig.KEYCLOAK_ADMIN_ROLE}")
        print(f"Tribunal role: {KeycloakConfig.KEYCLOAK_TRIBUNAL_ROLE}")
