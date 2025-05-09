from flask import Blueprint
from app.integrations.google_drive import GoogleDriveAPI

# Create blueprint
concursos = Blueprint('concursos', __name__, url_prefix='/concursos')

# Initialize shared services
drive_api = GoogleDriveAPI()

# Import route modules after the blueprint is defined to avoid circular imports
from . import views
from . import documents
from . import sustanciacion
from . import api
from . import uploads
