import os
import json
from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash
from pathlib import Path

from app.models.models import db, User, init_db_from_json, init_categories_from_json
from app.integrations.keycloak_oidc import keycloak_oidc
from app.integrations.keycloak_admin_client import get_keycloak_admin
from app.config.keycloak_config import KeycloakConfig

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
            
        # Initialize sorteo configuration with default values
        try:
            from app.routes.admin_sorteo_config import init_sorteo_config
            init_sorteo_config()
        except Exception as e:
            print(f"Error initializing sorteo config: {e}")

def create_app():
    # Load environment variables from the root directory
    env_path = Path(__file__).resolve().parent.parent / '.env'
    print(f"Loading .env from: {env_path}")
    load_dotenv(env_path)
    
    app = Flask(__name__, instance_relative_config=True)
    
    # Configure APPLICATION_ROOT for deployment with base path
    app.config['APPLICATION_ROOT'] = os.environ.get('APPLICATION_ROOT', '/selecciones-docentes')
    
    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
    
    # Google Drive Configuration
    app.config['GOOGLE_DRIVE_CVS_FOLDER_ID'] = os.environ.get('GOOGLE_DRIVE_CVS_FOLDER_ID')
    
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
    migrate.init_app(app, db)      # Initialize Keycloak OIDC
    try:
        keycloak_oidc.init_app(app)
        app.logger.info("Keycloak OIDC initialized successfully")
    except Exception as e:
        app.logger.error(f"Failed to initialize Keycloak OIDC: {e}")
        # You can choose to raise the exception to prevent app startup
        # or continue without Keycloak (for development/testing)
        # raise e
    
    # Initialize sync scheduler
    try:
        from app.services.sync_scheduler import init_scheduler
        init_scheduler(app)
        app.logger.info("Keycloak sync scheduler initialized")
    except Exception as e:
        app.logger.error(f"Failed to initialize sync scheduler: {e}")# Initialize Keycloak Admin Client - temporarily disabled
    # TODO: Re-enable after configuring service account in Keycloak
    # try:
    #     # Test if we can get a keycloak admin client
    #     keycloak_admin = get_keycloak_admin()
    #     app.keycloak_admin = keycloak_admin
    #     app.logger.info("Keycloak Admin Client initialized successfully")
    # except Exception as e:
    #     app.logger.error(f"Failed to initialize Keycloak Admin Client: {e}")
    #     # Continue without admin client for now
    app.keycloak_admin = None
    app.logger.info("Keycloak Admin Client disabled - enable after configuring service account")
      
        # Register blueprints
    from app.routes.auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)
    from app.routes.concursos import concursos as concursos_blueprint
    app.register_blueprint(concursos_blueprint)
    from app.routes.admin_templates import admin_templates_bp
    app.register_blueprint(admin_templates_bp)
    
    from app.routes.admin_sorteo_config import admin_sorteo_config_bp, init_sorteo_config
    app.register_blueprint(admin_sorteo_config_bp)
    
    from app.routes.postulantes import postulantes as postulantes_blueprint
    app.register_blueprint(postulantes_blueprint)
    
    from app.routes.tribunal import tribunal as tribunal_blueprint
    app.register_blueprint(tribunal_blueprint)      # Register admin personas blueprint
    from app.routes.admin_personas import admin_personas_bp
    app.register_blueprint(admin_personas_bp)
    
    # Register admin sync blueprint
    from app.routes.admin_sync import admin_sync_bp
    app.register_blueprint(admin_sync_bp)
      
    # Register admin API data blueprint
    from app.routes.admin_api_data import admin_api_data_bp
    app.register_blueprint(admin_api_data_bp)
    
    # Register notifications blueprint
    from app.routes.notifications import notifications_bp
    app.register_blueprint(notifications_bp)
    
    # Register API blueprint
    from app.routes.api import api_bp
    app.register_blueprint(api_bp)
    
    # Register public blueprint
    from app.routes.public import public as public_blueprint
    app.register_blueprint(public_blueprint)

    # Register admin instructivos blueprint (new editable instructivos feature)
    from app.routes.admin_instructivos import bp as admin_instructivos_bp
    app.register_blueprint(admin_instructivos_bp)

    # Register admin required docs blueprint
    from app.routes.admin_required_docs import bp as admin_required_docs_bp
    app.register_blueprint(admin_required_docs_bp)

    # Add context processor for template functions
    from flask import g
    # Keycloak helper accessors (avoid direct import of non-existent functions)
    def get_current_user_info():
        kc = getattr(app, 'keycloak_oidc', None)
        if kc:
            return kc.get_user_info()
        return {}

    def get_current_user_roles():
        kc = getattr(app, 'keycloak_oidc', None)
        if kc:
            return kc.get_user_roles()
        return []

    def is_admin():
        """Return True if user has the configured admin role.

        Uses KeycloakConfig.KEYCLOAK_ADMIN_ROLE and keeps backward compatibility
        with legacy 'admin'/'ADMIN' role names if present in tokens.
        """
        roles = set(get_current_user_roles() or [])
        configured_admin = KeycloakConfig.KEYCLOAK_ADMIN_ROLE
        legacy_aliases = {'admin', 'ADMIN'}
        return (configured_admin in roles) or bool(roles.intersection(legacy_aliases))

    def is_tribunal_member():
        """Return True if user has tribunal role or is admin (admins inherit)."""
        roles = set(get_current_user_roles() or [])
        configured_tribunal = KeycloakConfig.KEYCLOAK_TRIBUNAL_ROLE
        legacy_aliases = {'tribunal', 'TRIBUNAL'}
        return (configured_tribunal in roles) or bool(roles.intersection(legacy_aliases)) or is_admin()
    from app.helpers.api_services import get_programa_download_url
    
    @app.context_processor
    def utility_processor():
        try:
            user_info = get_current_user_info()
            user_roles = get_current_user_roles()
            is_authenticated = g.get('is_authenticated', False)
            admin_status = is_admin()
            tribunal_status = is_tribunal_member()
            
            return {
                'get_programa_download_url': get_programa_download_url,
                'keycloak_user_info': user_info,
                'keycloak_user_roles': user_roles,
                'keycloak_is_admin': admin_status,
                'keycloak_is_tribunal': tribunal_status,
                'keycloak_is_authenticated': is_authenticated,
                'debug_g_authenticated': g.get('is_authenticated', 'NOT_SET'),
                'debug_g_roles': g.get('user_roles', 'NOT_SET')
            }
        except Exception as e:
            # Fallback in case of errors
            return {
                'get_programa_download_url': get_programa_download_url,
                'keycloak_user_info': {},
                'keycloak_user_roles': [],
                'keycloak_is_admin': False,
                'keycloak_is_tribunal': False,
                'keycloak_is_authenticated': False,
                'debug_error': str(e)
            }
    
    # Add custom filters for templates
    @app.template_filter('format_datetime')
    def format_datetime(value, format='%d/%m/%Y %H:%M'):
        """Format a datetime object for display in templates"""
        if value is None:
            return ""
        return value.strftime(format)

    @app.template_filter('trim')
    def trim_filter(value):
        """Trim whitespace from string"""
        if value is None:
            return ""
        return value.strip()

    @app.template_filter('fromjson')
    def fromjson_filter(value):
        """Parse a JSON string into a Python object"""
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return value

    @app.template_filter('format_date_spanish')
    def format_date_spanish(value, format='%d de %B de %Y'):
        """Format a date object with Spanish month names"""
        if value is None:
            return ""
        
        # Spanish month names
        months_spanish = {
            'January': 'enero', 'February': 'febrero', 'March': 'marzo',
            'April': 'abril', 'May': 'mayo', 'June': 'junio',
            'July': 'julio', 'August': 'agosto', 'September': 'septiembre',
            'October': 'octubre', 'November': 'noviembre', 'December': 'diciembre'
        }
        
        # Format with English month names first
        formatted_date = value.strftime(format)
        
        # Replace English month names with Spanish ones
        for english, spanish in months_spanish.items():
            formatted_date = formatted_date.replace(english, spanish)
        
        return formatted_date

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    return app