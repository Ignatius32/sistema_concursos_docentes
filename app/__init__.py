import os
import json
from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash
from pathlib import Path

from app.models.models import db, User, init_db_from_json, init_categories_from_json

login_manager = LoginManager()
migrate = Migrate()

def init_app_data(app):
    """Initialize application data like admin user and reference data."""
    with app.app_context():
        # Create the instance directory if it doesn't exist
        os.makedirs(app.instance_path, exist_ok=True)
        
        db.create_all()
        
        # Check if admin user exists
        admin = User.query.filter_by(username=os.environ.get('ADMIN_USERNAME', 'admin')).first()
        if not admin:
            print("Creating admin user...")
            admin = User(
                username=os.environ.get('ADMIN_USERNAME', 'admin')
            )
            admin.set_password(os.environ.get('ADMIN_PASSWORD', 'admin123'))
            db.session.add(admin)
            db.session.commit()
        
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
    # Load environment variables from the root directory
    env_path = Path(__file__).resolve().parent.parent / '.env'
    print(f"Loading .env from: {env_path}")
    load_dotenv(env_path)
    
    app = Flask(__name__, instance_relative_config=True)
    
    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
    
    # Set up database URI with absolute path in instance folder
    if os.environ.get('DATABASE_URI'):
        db_uri = os.environ.get('DATABASE_URI')
        if db_uri.startswith('sqlite:///'):
            # Convert relative SQLite path to absolute path in instance folder
            db_path = os.path.join(app.instance_path, db_uri.replace('sqlite:///', ''))
            app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
        else:
            app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    else:
        db_path = os.path.join(app.instance_path, 'concursos.db')
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    
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