#!/usr/bin/env python3
"""
Minimal OIDC test without admin API dependencies.
"""
import os
from flask import Flask, request, redirect, url_for, session, g
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_minimal_app():
    """Create a minimal Flask app for testing OIDC only."""
    app = Flask(__name__)
    app.secret_key = os.getenv('SECRET_KEY', 'test-secret-key')
    
    try:
        # Only test OIDC, no admin API
        from authlib.integrations.flask_client import OAuth
        from app.config.keycloak_config import KeycloakConfig
        
        # Validate only OIDC config
        config_errors = KeycloakConfig.validate_oidc_config()
        if config_errors:
            print(f"OIDC Config errors: {config_errors}")
            return None
        
        # Initialize OAuth
        oauth = OAuth(app)
        
        # Register Keycloak client with manual endpoints
        oidc_config = KeycloakConfig.get_oidc_config()
        keycloak = oauth.register(
            name='keycloak',
            client_id=KeycloakConfig.KEYCLOAK_CLIENT_ID,
            client_secret=KeycloakConfig.KEYCLOAK_CLIENT_SECRET,
            authorize_url=oidc_config['authorization_endpoint'],
            access_token_url=oidc_config['token_endpoint'],
            userinfo_endpoint=oidc_config['userinfo_endpoint'],
            client_kwargs={
                'scope': 'openid email profile'
            }
        )
        
        @app.route('/')
        def index():
            user_info = session.get('user_info')
            if user_info:
                return f'''
                <h1>Minimal OIDC Test - LOGGED IN</h1>
                <p><strong>User:</strong> {user_info.get('preferred_username', 'N/A')}</p>
                <p><strong>Email:</strong> {user_info.get('email', 'N/A')}</p>
                <p><strong>Name:</strong> {user_info.get('name', 'N/A')}</p>
                <p><a href="/logout">Logout</a></p>
                <hr>
                <details>
                    <summary>Full User Info</summary>
                    <pre>{user_info}</pre>
                </details>
                '''
            else:
                return '''
                <h1>Minimal OIDC Test - NOT LOGGED IN</h1>
                <p><a href="/login">Login with Keycloak</a></p>
                '''
        
        @app.route('/login')
        def login():
            redirect_uri = url_for('auth_callback', _external=True)
            return keycloak.authorize_redirect(redirect_uri)
        
        @app.route('/auth/callback')
        def auth_callback():
            try:
                token = keycloak.authorize_access_token()
                
                # Get user info from userinfo endpoint
                user_info = keycloak.parse_id_token(token)
                session['user_info'] = user_info
                session['token'] = token
                
                return redirect('/')
            except Exception as e:
                return f'Login failed: {str(e)}'
        
        @app.route('/logout')
        def logout():
            session.clear()
            logout_url = f"{oidc_config['end_session_endpoint']}?redirect_uri={url_for('index', _external=True)}"
            return redirect(logout_url)
        
        print("✓ Minimal OIDC app created successfully")
        return app
        
    except Exception as e:
        print(f"✗ Failed to create minimal app: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("Creating minimal OIDC test app...")
    
    app = create_minimal_app()
    if app:
        print("\n" + "=" * 60)
        print("MINIMAL OIDC TEST APP READY")
        print("=" * 60)
        print("Visit: http://127.0.0.1:5001")
        print("This tests ONLY the OIDC flow, no admin API")
        print("Fix the client secret in Keycloak first!")
        print("=" * 60)
        
        try:
            app.run(host='127.0.0.1', port=5001, debug=True)
        except KeyboardInterrupt:
            print("\nMinimal test app stopped.")
    else:
        print("Failed to create minimal app. Check the errors above.")
