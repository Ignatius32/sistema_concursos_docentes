#!/bin/bash
# Installation script for Sistema Concursos Docentes on Apache

echo "=== Sistema Concursos Docentes Installation Script ==="
echo "This script will help you deploy the application on Apache with Keycloak integration"
echo ""

# Step 1: Check if we're running as root or with sudo
if [ "$EUID" -ne 0 ]; then
    echo "Please run this script with sudo or as root"
    exit 1
fi

# Step 2: Update environment file
echo "Step 1: Updating environment configuration..."
cd /var/www/concursos-docentes

# Copy production environment template if .env doesn't exist
if [ ! -f ".env" ]; then
    if [ -f ".env.production" ]; then
        cp .env.production .env
        echo "Created .env from .env.production template"
    else
        echo "ERROR: .env.production template not found!"
        exit 1
    fi
fi

# Step 3: Install Python dependencies
echo "Step 2: Installing Python dependencies..."
if [ -d "venv" ]; then
    echo "Virtual environment already exists"
else
    python3 -m venv venv
    echo "Created virtual environment"
fi

# Activate virtual environment and install dependencies
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Step 4: Set proper permissions
echo "Step 3: Setting proper permissions..."
chown -R www-data:www-data /var/www/concursos-docentes
chmod -R 755 /var/www/concursos-docentes
chmod -R 644 /var/www/concursos-docentes/app/static
chmod 600 /var/www/concursos-docentes/.env
chmod -R 700 /var/www/concursos-docentes/instance

# Step 5: Initialize database
echo "Step 4: Initializing database..."
sudo -u www-data /var/www/concursos-docentes/venv/bin/python -c "
import sys
sys.path.insert(0, '/var/www/concursos-docentes')
from app import create_app, init_app_data
app = create_app()
init_app_data(app)
print('Database initialized successfully')
"

# Step 6: Test configuration
echo "Step 5: Testing configuration..."
sudo -u www-data /var/www/concursos-docentes/venv/bin/python /var/www/concursos-docentes/debug_keycloak.py

# Step 7: Restart Apache
echo "Step 6: Restarting Apache..."
systemctl restart apache2

# Step 8: Check Apache status
echo "Step 7: Checking Apache status..."
systemctl status apache2 --no-pager -l

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Next steps:"
echo "1. Check the application at: https://your-domain.com/concursos-docentes/"
echo "2. Monitor logs: sudo tail -f /var/log/apache2/error.log"
echo "3. Check application logs: sudo tail -f /var/www/concursos-docentes/app.log"
echo ""
echo "If you see errors, run the debug script:"
echo "sudo -u www-data /var/www/concursos-docentes/venv/bin/python /var/www/concursos-docentes/debug_keycloak.py"
echo ""
echo "Common issues:"
echo "- Make sure your Keycloak client is configured with the correct redirect URIs"
echo "- Verify that the KEYCLOAK_CLIENT_SECRET in .env matches your Keycloak client"
echo "- Check that the APPLICATION_ROOT matches your Apache WSGIScriptAlias path"
