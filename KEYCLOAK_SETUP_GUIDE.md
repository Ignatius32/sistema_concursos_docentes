# Keycloak Setup Guide for Sistema Concursos Docentes

## 1. Keycloak Server Setup

### Option A: Using Docker (Recommended for development)
```bash
# Start Keycloak with Docker
docker run -p 8080:8080 -e KEYCLOAK_ADMIN=admin -e KEYCLOAK_ADMIN_PASSWORD=admin quay.io/keycloak/keycloak:latest start-dev
```

### Option B: Download and Install
1. Download Keycloak from: https://www.keycloak.org/downloads
2. Extract and run: `bin/kc.sh start-dev` (Linux/Mac) or `bin\kc.bat start-dev` (Windows)

## 2. Keycloak Configuration

### Step 1: Access Admin Console
- URL: http://localhost:8080
- Login with admin/admin (or your configured credentials)

### Step 2: Create Realm
1. Click "Create Realm"
2. Name: `my-app-realm`
3. Click "Create"

### Step 3: Create Client for Flask App
1. Go to "Clients" → "Create client"
2. **Client ID**: `flask-client`
3. **Client type**: OpenID Connect
4. Click "Next"
5. **Client authentication**: ON (Confidential)
6. **Authorization**: OFF
7. **Authentication flow**:
   - ✅ Standard flow
   - ✅ Direct access grants (for API access)
   - ❌ Implicit flow
   - ❌ Service accounts roles
8. Click "Next"
9. **Valid redirect URIs**: `http://localhost:5000/auth/oidc_callback`
10. **Web origins**: `http://localhost:5000`
11. Click "Save"
12. Go to "Credentials" tab and copy the **Client Secret**

### Step 4: Create Realm Roles
1. Go to "Realm roles" → "Create role"
2. Create these roles:
   - **Role name**: `app_admin`
   - **Description**: Application Administrator
   - Click "Save"
3. Repeat for:
   - **Role name**: `tribunal_member`
   - **Description**: Tribunal Member

### Step 5: Create Admin User
1. Go to "Users" → "Create new user"
2. **Username**: `admin`
3. **Email**: your-email@domain.com
4. **First name**: Admin
5. **Last name**: User
6. **Email verified**: ON
7. Click "Create"
8. Go to "Credentials" tab:
   - Set password
   - **Temporary**: OFF
9. Go to "Role mapping" tab:
   - Click "Assign role"
   - Select `app_admin`
   - Click "Assign"

## 3. Flask Application Configuration

### Step 1: Create .env file
```bash
cp .env.example .env
```

### Step 2: Update .env with your Keycloak settings
```bash
# Keycloak Server Configuration
KEYCLOAK_SERVER_URL=http://localhost:8080
KEYCLOAK_REALM=my-app-realm

# OIDC Client Configuration
KEYCLOAK_CLIENT_ID=flask-client
KEYCLOAK_CLIENT_SECRET=your-client-secret-from-step-3

# Keycloak Admin API Configuration
KEYCLOAK_ADMIN_USERNAME=admin
KEYCLOAK_ADMIN_PASSWORD=your-admin-password

# Application URLs
KEYCLOAK_REDIRECT_URI=http://localhost:5000/auth/oidc_callback
KEYCLOAK_POST_LOGOUT_REDIRECT_URI=http://localhost:5000/
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Initialize Database
```bash
# Remove old database (if you want a fresh start)
rm instance/concursos.db

# Start the application - it will create the database automatically
python run.py
```

## 4. Testing the Integration

### Step 1: Start the Application
```bash
python run.py
```

### Step 2: Test Login
1. Visit: http://localhost:5000/auth/login
2. Click "Iniciar Sesión con Keycloak"
3. Should redirect to Keycloak login page
4. Login with your admin credentials
5. Should redirect back to the application

### Step 3: Test Admin Functions
1. Go to: http://localhost:5000/admin/personas/
2. Create a new persona
3. Verify the user is created in Keycloak (check Users in Keycloak admin)
4. Check that an email would be sent (or see the temporary password in the flash message)

## 5. Troubleshooting

### Common Issues

#### 1. "Failed to initialize Keycloak OIDC"
- Check that Keycloak server is running on the configured URL
- Verify realm name and client configuration
- Check network connectivity

#### 2. "Invalid client credentials"
- Verify KEYCLOAK_CLIENT_SECRET in .env
- Check that client is configured as "Confidential" in Keycloak
- Ensure redirect URIs match exactly

#### 3. "Role not found" errors
- Verify realm roles are created in Keycloak
- Check role names match exactly (case-sensitive)
- Ensure admin user has proper roles assigned

#### 4. "User creation failed"
- Check admin credentials have permission to create users
- Verify email format is valid
- Check Keycloak logs for detailed error messages

### Debug Steps
1. **Check application logs** - Look for ERROR messages about Keycloak
2. **Check Keycloak logs** - Admin Console → Events
3. **Verify configuration** - Double-check all environment variables
4. **Test connectivity** - Try accessing http://localhost:8080/realms/my-app-realm/.well-known/openid_configuration

## 6. Production Considerations

### Security
- Use HTTPS for all Keycloak and application URLs
- Use strong, unique passwords and secrets
- Configure proper CORS settings
- Enable proper logging and monitoring

### Performance
- Configure appropriate session timeouts
- Set up Keycloak clustering if needed
- Use proper database backend for Keycloak (not H2)

### Backup
- Backup Keycloak configuration and user data
- Document all custom configurations
- Test disaster recovery procedures

## Next Steps

After successful setup, continue with:
1. **Tribunal member management refactoring** (`app/routes/tribunal.py`)
2. **Template updates** for tribunal access
3. **Email template updates** to remove password information
4. **Database migration** to finalize schema changes
5. **Production deployment** configuration

For more details, see `KEYCLOAK_IMPLEMENTATION_STATUS.md`
