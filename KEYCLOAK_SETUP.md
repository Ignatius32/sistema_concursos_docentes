# Keycloak Integration Setup Guide

## Phase 1: Project Configuration & Dependencies

### Step 1: Install Dependencies

Install the new required Python packages:

```powershell
pip install -r requirements.txt
```

The following packages have been added for Keycloak integration:
- `authlib==1.3.0` - OAuth 2.0/OIDC client library
- `python-keycloak==3.7.0` - Keycloak Admin API client
- `cryptography==41.0.8` - Cryptographic support
- `PyJWT==2.8.0` - JWT token handling

### Step 2: Environment Configuration

1. Copy the `.env.template` file to `.env`:
   ```powershell
   Copy-Item .env.template .env
   ```

2. Update the `.env` file with your Keycloak configuration:

   ```env
   # Keycloak Configuration
   KEYCLOAK_SERVER_URL=http://localhost:8080
   KEYCLOAK_REALM=my-app-realm
   KEYCLOAK_CLIENT_ID=flask-client
   KEYCLOAK_CLIENT_SECRET=your-client-secret-here
   KEYCLOAK_ADMIN_CLIENT_ID=admin-cli
   KEYCLOAK_ADMIN_CLIENT_SECRET=your-admin-client-secret
   KEYCLOAK_REDIRECT_URI=http://localhost:5000/oidc_callback
   KEYCLOAK_POST_LOGOUT_REDIRECT_URI=http://localhost:5000/
   KEYCLOAK_ADMIN_ROLE=app_admin
   KEYCLOAK_TRIBUNAL_ROLE=tribunal_member
   ```

### Step 3: Keycloak Server Setup (Prerequisites)

Before running the Flask application, ensure your Keycloak server is properly configured:

#### 3.1 Keycloak Server Installation
1. Download and install Keycloak from https://www.keycloak.org/downloads
2. Start Keycloak server:
   ```bash
   # Development mode
   bin/kc.sh start-dev
   # or on Windows
   bin\kc.bat start-dev
   ```

#### 3.2 Realm Configuration
1. Access Keycloak Admin Console: http://localhost:8080/admin
2. Create a new realm called `my-app-realm` (or use the name from your .env)

#### 3.3 Client Configuration
Create a client for your Flask application:

1. Navigate to Clients → Create Client
2. Configure:
   - **Client ID**: `flask-client`
   - **Client Type**: OpenID Connect
   - **Client authentication**: On
3. In the client settings:
   - **Valid redirect URIs**: `http://localhost:5000/oidc_callback`
   - **Valid post logout redirect URIs**: `http://localhost:5000/`
   - **Standard Flow**: Enabled
   - **Implicit Flow**: Disabled
   - **Direct Access Grants**: Enabled (for testing)
4. Note the **Client Secret** from the Credentials tab

#### 3.4 Role Configuration
Create the following realm roles:
1. Navigate to Realm roles → Create role
2. Create roles:
   - `app_admin` - For application administrators
   - `tribunal_member` - For tribunal members

#### 3.5 Admin API Access
For user management, configure Admin API access:

**Option A: Service Account (Recommended)**
1. In your client settings, enable "Service accounts roles"
2. Go to Service Account Roles tab
3. Assign necessary realm-management roles:
   - `manage-users`
   - `manage-realm`
   - `view-users`
   - `view-realm`

**Option B: Admin User**
1. Create an admin user or use existing admin
2. Set credentials in .env:
   ```env
   KEYCLOAK_ADMIN_USERNAME=admin
   KEYCLOAK_ADMIN_PASSWORD=admin-password
   ```

### Step 4: Test Configuration

Run the Flask application to verify Keycloak integration:

```powershell
python run.py
```

Check the console output for:
- "Keycloak OIDC initialized successfully"
- No configuration errors

### Step 5: Files Created/Modified

The following files have been created or modified:

**New Files:**
- `app/config/keycloak_config.py` - Keycloak configuration management
- `app/integrations/keycloak_oidc.py` - OIDC client integration
- `app/utils/keycloak_auth.py` - Authorization decorators
- `.env.template` - Environment variables template
- `KEYCLOAK_SETUP.md` - This setup guide

**Modified Files:**
- `requirements.txt` - Added Keycloak dependencies
- `app/__init__.py` - Integrated Keycloak OIDC client

### Step 6: Verify Installation

1. Start your Flask application
2. Navigate to http://localhost:5000
3. The application should start without errors
4. Keycloak integration is ready for Phase 2 (Authentication Routes)

### Troubleshooting

**Common Issues:**

1. **Import errors for authlib**: Make sure you've installed the requirements
2. **Keycloak connection errors**: Verify KEYCLOAK_SERVER_URL is correct and server is running
3. **Client secret errors**: Ensure the client secret matches your Keycloak client configuration
4. **Role assignment errors**: Verify the service account has proper permissions in Keycloak

**Configuration Validation:**
The application will validate Keycloak configuration on startup and log any issues.

---

## Next Steps

Once this phase is complete, we'll proceed to **Phase 2: Authentication Routes** where we'll:
1. Modify the login/logout routes
2. Add OIDC callback handling
3. Update route protection decorators
4. Modify templates for Keycloak authentication

Ready to proceed to Phase 2?
