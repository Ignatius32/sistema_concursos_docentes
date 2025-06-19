# Apache Deployment with Keycloak Integration

This document describes how to deploy the Sistema Concursos Docentes application on Apache with Keycloak authentication at a base URL.

## Prerequisites

1. Apache server with mod_wsgi enabled
2. Python 3.9+ with virtual environment
3. Keycloak server instance
4. SSL certificate (recommended for production)

## Deployment Steps

### 1. Application Setup

```bash
# Create application directory
sudo mkdir -p /var/www/concursos-docentes
cd /var/www/concursos-docentes

# Clone your application
sudo git clone <your-repo-url> .

# Create virtual environment
sudo python3 -m venv venv
sudo chown -R www-data:www-data venv

# Activate and install dependencies
sudo -u www-data venv/bin/pip install -r requirements.txt
```

### 2. Environment Configuration

Copy and configure the environment file:

```bash
sudo cp .env.production .env
sudo nano .env
```

Update the following variables:
- `PRODUCTION_HOST`: Your domain name
- `KEYCLOAK_CLIENT_SECRET`: From your Keycloak client configuration
- `SECRET_KEY`: Generate a secure random key
- Other database and service configurations as needed

### 3. Keycloak Client Configuration

In your Keycloak admin console, configure your client with:

**Valid Redirect URIs:**
- `https://your-domain.com/concursos-docentes/auth/callback`

**Valid Post Logout Redirect URIs:**
- `https://your-domain.com/concursos-docentes/`

**Web Origins:**
- `https://your-domain.com`

**Base URL:**
- `/concursos-docentes/`

### 4. Apache Configuration

The application includes an Apache configuration file (`apache_config.conf`). Add this to your Apache virtual host or include it:

```apache
# Include the configuration
Include /var/www/concursos-docentes/apache_config.conf
```

Or add directly to your virtual host:

```apache
<VirtualHost *:443>
    ServerName your-domain.com
    
    # SSL Configuration
    SSLEngine on
    SSLCertificateFile /path/to/your/certificate.crt
    SSLCertificateKeyFile /path/to/your/private.key
    
    # Include the concursos-docentes configuration
    Include /var/www/concursos-docentes/apache_config.conf
    
    # Your other configurations
</VirtualHost>
```

### 5. Permissions and Ownership

```bash
# Set proper ownership
sudo chown -R www-data:www-data /var/www/concursos-docentes

# Set proper permissions
sudo chmod -R 755 /var/www/concursos-docentes
sudo chmod -R 644 /var/www/concursos-docentes/app/static

# Protect sensitive files
sudo chmod 600 /var/www/concursos-docentes/.env
sudo chmod -R 700 /var/www/concursos-docentes/instance
```

### 6. Database Initialization

```bash
# Initialize the database
sudo -u www-data /var/www/concursos-docentes/venv/bin/python -c "
from app import create_app, init_app_data
app = create_app()
init_app_data(app)
"
```

### 7. Restart Apache

```bash
sudo systemctl restart apache2
```

## Testing the Deployment

1. **Test Application Access:**
   - Visit `https://your-domain.com/concursos-docentes/`
   - Should redirect to login page

2. **Test Keycloak Integration:**
   - Click login and verify Keycloak redirect works
   - Complete authentication flow
   - Verify redirect back to application

3. **Test Static Files:**
   - Check that CSS/JS files load properly
   - Visit `https://your-domain.com/concursos-docentes/static/css/`

## Troubleshooting

### Common Issues:

1. **404 on Base URL:**
   - Check Apache configuration is loaded
   - Verify APPLICATION_ROOT environment variable

2. **Keycloak Redirect Issues:**
   - Check redirect URIs in Keycloak client configuration
   - Verify KEYCLOAK_REDIRECT_URI in environment file

3. **Static Files Not Loading:**
   - Check Apache Alias configuration for static files
   - Verify file permissions

4. **Internal Server Error:**
   - Check Apache error logs: `sudo tail -f /var/log/apache2/error.log`
   - Check application logs
   - Verify Python virtual environment path in wsgi.py

### Logs to Check:

```bash
# Apache logs
sudo tail -f /var/log/apache2/error.log
sudo tail -f /var/log/apache2/access.log

# Application logs (if configured)
sudo tail -f /var/www/concursos-docentes/app.log
```

## Security Considerations

1. **SSL/TLS:** Always use HTTPS in production
2. **Firewall:** Restrict access to necessary ports only
3. **File Permissions:** Ensure sensitive files are not web-accessible
4. **Environment Variables:** Keep secrets secure and rotate regularly
5. **Database:** Use proper database security if not using SQLite

## Keycloak-Specific Notes

- The application automatically detects the base path and constructs proper redirect URIs
- If you change the base path, update both Apache configuration and Keycloak client settings
- The `APPLICATION_ROOT` environment variable should match your Apache WSGIScriptAlias path
- Dynamic URL generation handles both development and production environments

## Updates and Maintenance

To update the application:

```bash
cd /var/www/concursos-docentes
sudo -u www-data git pull
sudo -u www-data venv/bin/pip install -r requirements.txt
sudo systemctl restart apache2
```
