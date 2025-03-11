import os
import json
from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

from app.models.models import db, User, init_db_from_json, init_categories_from_json

# Load environment variables
load_dotenv()

login_manager = LoginManager()
migrate = Migrate()

def init_app_data(app):
    """Initialize application data like admin user and reference data."""
    with app.app_context():
        db.create_all()
        
        # Check if admin user exists
        print(f"ADMIN_USERNAME: {os.environ.get('ADMIN_USERNAME')}")
        print(f"ADMIN_PASSWORD: {os.environ.get('ADMIN_PASSWORD')}")
        admin = User.query.filter_by(username=os.environ.get('ADMIN_USERNAME', 'admin')).first()
        if admin:
            print(f"Admin user exists: {admin.username}, {admin.password_hash}")
        if not admin:
            print("Creating admin user...")
            admin = User(
                username=os.environ.get('ADMIN_USERNAME', 'admin')
            )
            admin.set_password(os.environ.get('ADMIN_PASSWORD', 'admin123'))
            db.session.add(admin)
            db.session.commit()
            print(f"Admin user created: {admin.username}, {admin.password_hash}")
        
        # Initialize the database with departamentos, areas, orientaciones from JSON
        try:
            with open(os.path.join(app.root_path, '../deptos_area_orientacion.json'), 'r', encoding='utf-8') as f:
                json_data = json.load(f)
                # Check if we need to initialize the database (if there are no departamentos)
                from app.models.models import Departamento
                if Departamento.query.first() is None:
                    init_db_from_json(app, json_data)
        except Exception as e:
            print(f"Error loading departamentos: {e}")
        
        # Initialize the database with categorias from JSON
        try:
            with open(os.path.join(app.root_path, '../roles_categorias.json'), 'r', encoding='utf-8') as f:
                json_data = json.load(f)
                # Check if we need to initialize the database (if there are no categorias)
                from app.models.models import Categoria
                if Categoria.query.first() is None:
                    init_categories_from_json(app, json_data)
        except Exception as e:
            print(f"Error loading categorias: {e}")

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URI', 'sqlite:///concursos.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    migrate.init_app(app, db)
    
    # Register blueprints
    from app.routes.auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)
    
    from app.routes.concursos import concursos as concursos_blueprint
    app.register_blueprint(concursos_blueprint)
    
    from app.routes.postulantes import postulantes as postulantes_blueprint
    app.register_blueprint(postulantes_blueprint)
    
    from app.routes.tribunal import tribunal as tribunal_blueprint
    app.register_blueprint(tribunal_blueprint)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    return app