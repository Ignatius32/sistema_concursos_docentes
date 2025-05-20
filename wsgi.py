import sys
import os

# Add the application directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import app factory function and initialize app data
from app import create_app, init_app_data

# Create the application instance
application = create_app()
init_app_data(application)

# This is the WSGI application referenced by the Apache configuration
if __name__ == "__main__":
    application.run()
