from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
import os
from app.models.models import User, db

auth = Blueprint('auth', __name__, url_prefix='/auth')

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('concursos.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Find user by username
        user = User.query.filter_by(username=username).first()
        
        # If user doesn't exist and it's the admin username, create it
        if not user and username == os.environ.get('ADMIN_USERNAME', 'admin'):
            user = User(
                username=username,
                role='admin',
                is_active=True
            )
            user.set_password(os.environ.get('ADMIN_PASSWORD', 'admin123'))
            db.session.add(user)
            db.session.commit()
        
        # Verify password
        if user and user.check_password(password):
            login_user(user)
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