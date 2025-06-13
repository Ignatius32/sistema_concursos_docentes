# Keycloak Client Configuration Guide

Based on your Keycloak server at `https://huayca.crub.uncoma.edu.ar/auth/`, here's the specific configuration needed for your `selecciones-docentes` client.

## Required Keycloak Client Settings

### 1. Create the Client
1. Go to your Keycloak Admin Console: `https://huayca.crub.uncoma.edu.ar/auth/admin/`
2. Select the `CRUB` realm
3. Go to **Clients** → **Create Client**

### 2. Client Basic Settings
```
Client ID: selecciones-docentes
Client Type: OpenID Connect
```

### 3. Client Authentication & Authorization
```
Client authentication: ON
Authorization: ON (optional, but recommended)
Authentication flow: 
  ✓ Standard flow
  ✓ Direct access grants
  ✓ Service accounts roles (IMPORTANT - needed for admin API)
```

### 4. Login Settings
```
Root URL: http://localhost:5000
Home URL: http://localhost:5000/
Valid redirect URIs: 
  - http://localhost:5000/*
  - http://your-production-domain.com/*
Valid post logout redirect URIs:
  - http://localhost:5000/
  - http://your-production-domain.com/
Web origins: 
  - http://localhost:5000
  - http://your-production-domain.com
```

### 5. Service Account Configuration (CRITICAL for Admin API)

After creating the client:

1. Go to **Clients** → **selecciones-docentes** → **Service account roles** tab
2. Assign these roles from **realm-management** client:
   - `realm-admin` (full admin access)
   - OR individually assign:
     - `manage-users`
     - `view-users` 
     - `manage-realm-roles`
     - `view-realm-roles`
     - `manage-clients`

### 6. Create Required Realm Roles

Go to **Realm settings** → **Roles** → **Create role**:

1. **app_admin**
   - Role name: `app_admin`
   - Description: `Administrator role for the application`

2. **tribunal_member** 
   - Role name: `tribunal_member`
   - Description: `Tribunal member role`

### 7. Client Secret

1. Go to **Clients** → **selecciones-docentes** → **Credentials** tab
2. Copy the **Client secret**
3. Use this in your environment variables

## Environment Variables Configuration

Create a `.env` file or set these environment variables:

```bash
# Keycloak Server Configuration
KEYCLOAK_SERVER_URL=https://huayca.crub.uncoma.edu.ar/auth
KEYCLOAK_REALM=CRUB

# OIDC Client Configuration (for user authentication)
KEYCLOAK_CLIENT_ID=selecciones-docentes
KEYCLOAK_CLIENT_SECRET=your-client-secret-here

# Admin API Configuration (same client, service account)
KEYCLOAK_ADMIN_CLIENT_ID=selecciones-docentes
KEYCLOAK_ADMIN_CLIENT_SECRET=your-client-secret-here

# Application URLs
KEYCLOAK_REDIRECT_URI=http://localhost:5000/oidc_callback
KEYCLOAK_POST_LOGOUT_REDIRECT_URI=http://localhost:5000/

# Role Names
KEYCLOAK_ADMIN_ROLE=app_admin
KEYCLOAK_TRIBUNAL_ROLE=tribunal_member
```

## Testing the Configuration

After setting up the client, test it:

```bash
# Run the diagnostic script
python diagnose_keycloak.py

# Run the personas test
python test_keycloak_personas.py
```

## Manual Verification Steps

### 1. Test OIDC Endpoints Manually

```bash
# Check if OIDC configuration is accessible
curl -k "https://huayca.crub.uncoma.edu.ar/auth/realms/CRUB/.well-known/openid_configuration"
```

### 2. Test Admin API Access

```bash
# Get service account token
curl -X POST "https://huayca.crub.uncoma.edu.ar/auth/realms/CRUB/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=selecciones-docentes" \
  -d "client_secret=YOUR_CLIENT_SECRET"
```

### 3. Test User Management

```bash
# Use the token to list users (replace TOKEN with actual token)
curl -X GET "https://huayca.crub.uncoma.edu.ar/auth/admin/realms/CRUB/users" \
  -H "Authorization: Bearer TOKEN"
```

## Common Issues & Solutions

### Issue 1: 404 Not Found on Admin API
**Solution**: Check that service account roles are properly assigned.

### Issue 2: 401 Unauthorized
**Solution**: Verify client secret and service account configuration.

### Issue 3: Role Assignment Fails
**Solution**: Ensure roles exist in the realm and service account has manage-users permission.

### Issue 4: OIDC Configuration Not Found
**Solution**: Check realm name and server URL. Some older Keycloak versions use different paths.

## Keycloak Version Compatibility

Your server appears to be running an older version of Keycloak. The configuration above is compatible with:
- Keycloak 8.x - 15.x (with `/auth` context path)
- May need adjustments for Keycloak 17+ (Quarkus distribution)

## Security Notes

1. **Use HTTPS in production**: Update URLs to use `https://` for production
2. **Restrict redirect URIs**: Only add domains you control
3. **Service account permissions**: Give minimal required permissions
4. **Client secret**: Keep it secure and don't commit to version control

## Next Steps

1. Configure the client in Keycloak as described above
2. Set the environment variables
3. Test with the diagnostic scripts
4. Try creating a persona through the admin interface
