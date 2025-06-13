#!/usr/bin/env python3
"""
Test Flask OIDC integration with minimal setup.
"""
import os
from flask import Flask, request, redirect, url_for
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_test_app():
    """Create a minimal Flask app for testing OIDC."""
    app = Flask(__name__)
    app.secret_key = os.getenv('SECRET_KEY', 'test-secret-key')
    
    # Import and initialize Keycloak OIDC
    try:
        from app.integrations.keycloak_oidc import KeycloakOIDCClient
        from app.config.keycloak_config import KeycloakConfig
        
        # Initialize OIDC client
        oidc_client = KeycloakOIDCClient()
        oidc_client.init_app(app)
        
        @app.route('/')
        def index():
            return '''
            <h1>Keycloak OIDC Test</h1>
            <p><a href="/login">Login with Keycloak</a></p>
            <p><a href="/logout">Logout</a></p>
            <p><a href="/protected">Protected Route</a></p>
            '''
        
        @app.route('/login')
        def login():
            try:
                return oidc_client.login()
            except Exception as e:
                return f'Login error: {str(e)}'
        
        @app.route('/auth/callback')
        def callback():
            try:
                success = oidc_client.callback()
                if success:
                    return redirect('/')
                else:
                    return 'Login failed'
            except Exception as e:
                return f'Callback error: {str(e)}'
        
        @app.route('/logout')
        def logout():
            try:
                return oidc_client.logout()
            except Exception as e:
                return f'Logout error: {str(e)}'
        
        @app.route('/protected')
        def protected():
            if oidc_client.is_authenticated():
                user_info = oidc_client.get_user_info()
                return f'''
                <h1>Protected Route</h1>
                <p>You are authenticated!</p>
                <p>User info: {user_info}</p>
                <p><a href="/logout">Logout</a></p>
                '''
            else:
                return redirect(url_for('login'))
        
        @app.before_request
        def load_user():
            """Load user information before each request."""
            oidc_client.before_request()
        
        print("✓ Test app created successfully")
        return app
        
    except Exception as e:
        print(f"✗ Failed to create test app: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("Creating test Flask app for Keycloak OIDC...")
    
    app = create_test_app()
    if app:
        print("\n" + "=" * 60)
        print("TEST APP READY")
        print("=" * 60)
        print("Visit: http://127.0.0.1:5000")
        print("Try the login flow to test Keycloak integration")
        print("Press Ctrl+C to stop")
        print("=" * 60)
        
        try:
            app.run(host='127.0.0.1', port=5000, debug=True)
        except KeyboardInterrupt:
            print("\nTest app stopped.")
    else:
        print("Failed to create test app. Check the errors above.")
