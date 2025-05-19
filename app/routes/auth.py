from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
import os
from app.models.models import User, Persona, db # Import Persona
from datetime import datetime # Import datetime

auth = Blueprint('auth', __name__, url_prefix='/auth')

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('concursos.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        authenticated_user = None

        # 1. Try to find and authenticate with the User model
        user = User.query.filter_by(username=username).first()
        
        if user:
            if user.check_password(password) and user.is_active:
                authenticated_user = user
        elif not user and username == os.environ.get('ADMIN_USERNAME', 'admin'):
            # This handles the initial admin User creation if it doesn't exist
            # and the provided username matches the environment variable for the admin username.
            admin_default_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
            if password == admin_default_password:
                # Create the admin User as it wasn't found
                admin_user = User(
                    username=username,
                    role='admin',
                    is_active=True
                )
                admin_user.set_password(admin_default_password)
                db.session.add(admin_user)
                try:
                    db.session.commit()
                    authenticated_user = admin_user
                except Exception as e: # Catch potential race condition if user was created meanwhile
                    db.session.rollback()
                    flash(f"Error creating admin user: {e}", "danger")
                    # Try to fetch again in case it was created by another request
                    existing_admin_user = User.query.filter_by(username=username).first()
                    if existing_admin_user and existing_admin_user.check_password(password) and existing_admin_user.is_active:
                        authenticated_user = existing_admin_user


        # 2. If not authenticated via User model, try Persona model for admins
        if not authenticated_user:
            # Ensure username is not None or empty before querying Persona
            if username and username.strip():
                persona_admin = Persona.query.filter_by(username=username, is_admin=True).first()
                if persona_admin and persona_admin.password_hash and persona_admin.check_password(password):
                    # Persona model doesn't have an 'is_active' field by default in your provided code.
                    # Flask-Login's UserMixin provides a default is_active=True.
                    # If you add an 'is_active' field to Persona, check it here: and persona_admin.is_active
                    authenticated_user = persona_admin
        
        if authenticated_user:
            login_user(authenticated_user)
              # Update ultimo_acceso for Persona type users
            if isinstance(authenticated_user, Persona):
                authenticated_user.ultimo_acceso = datetime.utcnow()
                try:
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    flash(f"Error updating last access time: {e}", "warning")
                    
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('concursos.index'))
        
        flash('Usuario o contraseña incorrectos.')
    
    return render_template('auth/login.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))