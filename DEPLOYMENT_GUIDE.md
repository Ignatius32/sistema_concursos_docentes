# Deployment Guide for Concursos Docentes Application

This guide provides step-by-step instructions for deploying the "Concursos Docentes" application to the Apache server on https://huayca.crub.uncoma.edu.ar.

## Prerequisites
- Access to the server with sudo privileges
- Python 3.9+ installed
- Apache2 with mod_wsgi installed

## Deployment Steps

1. **Copy the Application to the Server**

   Create the directory and copy all application files to the server:
   ```
   sudo mkdir -p /var/www/concursos-docentes
   sudo cp -r /path/to/local/sistema_concursos_docentes/* /var/www/concursos-docentes/
   ```

2. **Set Proper Permissions**

   Ensure Apache can access the files:
   ```
   sudo chown -R www-data:www-data /var/www/concursos-docentes
   sudo chmod -R 755 /var/www/concursos-docentes
   ```

3. **Create Virtual Environment**

   Create and activate a Python virtual environment:
   ```
   cd /var/www/concursos-docentes
   sudo python3 -m venv venv
   sudo chmod -R 755 venv
   sudo -u www-data /var/www/concursos-docentes/venv/bin/pip install -r requirements.txt
   ```

4. **Set Up Environment Variables**

   Create a .env file with the necessary environment variables:
   ```
   sudo nano /var/www/concursos-docentes/.env
   ```

   Add these variables (adjust as needed):
   ```
   SECRET_KEY=your_secret_key_here
   ADMIN_USERNAME=admin
   ADMIN_PASSWORD=strong_password
   DATABASE_URI=sqlite:///concursos.db
   GOOGLE_DRIVE_CVS_FOLDER_ID=your_google_drive_folder_id
   ```

5. **Test the WSGI Application**

   Make sure the WSGI script works:
   ```
   cd /var/www/concursos-docentes
   sudo -u www-data venv/bin/python wsgi.py
   ```

6. **Update Apache Configuration**

   Add the configuration block from `apache_config.conf` to your Apache configuration file:
   ```
   sudo nano /etc/apache2/sites-available/huayca.crub.uncoma.edu.ar.conf
   ```

   Insert the configuration block from `apache_config.conf` before the closing `</VirtualHost>` tag.

7. **Test and Reload Apache**

   Check the Apache configuration and then reload:
   ```
   sudo apachectl configtest
   sudo systemctl reload apache2
   ```

8. **Access the Application**

   Your application should now be available at:
   https://huayca.crub.uncoma.edu.ar/concursos-docentes/

## Troubleshooting

1. **Check Apache Error Logs**:
   ```
   sudo tail -f /var/log/apache2/error.log
   ```

2. **Check Application Permissions**:
   Make sure the application directory and files are accessible by the www-data user.

3. **WSGI Issues**:
   Ensure that mod_wsgi is correctly installed and configured for your Python version:
   ```
   sudo apt-get install libapache2-mod-wsgi-py3
   ```

4. **Database Connection**:
   Verify the database file is created and has the right permissions:
   ```
   sudo chown www-data:www-data /var/www/concursos-docentes/instance/concursos.db
   sudo chmod 664 /var/www/concursos-docentes/instance/concursos.db
   ```
