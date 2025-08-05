import sys
import os
import site
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).resolve().parent / '.env'
load_dotenv(env_path)
logging.info(f"Loading .env from: {env_path}")

# Configure logging for production
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('/var/www/concursos-docentes/app.log'),
        logging.StreamHandler()
    ]
)

# Add the site-packages of the virtualenv
site.addsitedir('/var/www/concursos-docentes/venv/lib/python3.9/site-packages')

# Add the application directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set environment variables for production deployment
os.environ.setdefault('APPLICATION_ROOT', '/selecciones-docentes')

# Import app factory function and initialize app data
from app import create_app, init_app_data

try:
    # Create the application instance
    application = create_app()
    
    # Initialize app data (create admin user, load reference data, etc.)
    init_app_data(application)
    
    logging.info("Sistema Concursos Docentes application started successfully")
    
except Exception as e:
    logging.error(f"Failed to start application: {e}")
    raise

# This is the WSGI application referenced by the Apache configuration
if __name__ == "__main__":
    application.run()
