# Keycloak Integration for Personas - Implementation Summary

## Overview

This document summarizes the improvements made to the Keycloak integration for managing personas in the `admin_personas` module. The integration now properly handles user creation, role assignment, and synchronization between the local database and Keycloak.

## Key Improvements Made

### 1. Enhanced KeycloakAdminClient (`app/integrations/keycloak_admin_client.py`)

**New Features:**
- **Duplicate User Detection**: The `create_user` method now checks for existing users by email and username before creating new ones
- **Role Validation**: Added `role_exists()` and `get_all_realm_roles()` methods for better role management
- **Improved Error Handling**: Better logging and error reporting for all operations

**Key Methods:**
```python
# Check if user exists before creating
existing_user = keycloak_admin.get_user_by_email(email)
existing_user = keycloak_admin.get_user_by_username(username)

# Validate roles before assignment
if keycloak_admin.role_exists(role_name):
    keycloak_admin.assign_realm_role(user_id, role_name)
```

### 2. Improved Admin Personas Route (`app/routes/admin_personas.py`)

**Enhanced User Creation Process:**
1. **Local Validation**: Check if persona exists in local database
2. **Keycloak User Check**: Check if user already exists in Keycloak by email/username
3. **User Creation**: Create user only if it doesn't exist
4. **Role Assignment**: Assign appropriate roles with validation
5. **Local Record**: Create local Persona record with Keycloak user ID

**Role Management:**
- Always assigns `tribunal_member` role to all personas
- Assigns `app_admin` role if `is_admin` is checked
- Uses configuration-based role names from `KeycloakConfig`
- Validates role existence before assignment
- Provides detailed feedback on role assignment success/failure

### 3. Configuration Integration

**Role Configuration:**
```python
# In KeycloakConfig
KEYCLOAK_ADMIN_ROLE = os.environ.get('KEYCLOAK_ADMIN_ROLE', 'app_admin')
KEYCLOAK_TRIBUNAL_ROLE = os.environ.get('KEYCLOAK_TRIBUNAL_ROLE', 'tribunal_member')
```

## Required Keycloak Setup

### 1. Client Configuration

Your Keycloak client `selecciones-docentes` needs:

**Client Settings:**
- Client ID: `selecciones-docentes` (or as configured in `KEYCLOAK_CLIENT_ID`)
- Client Protocol: `openid-connect`
- Access Type: `confidential`
- Service Accounts Enabled: `ON` (for admin operations)
- Authorization Enabled: `ON` (optional)

**Valid Redirect URIs:**
- `http://localhost:5000/oidc_callback` (adjust for your domain)
- `http://your-domain.com/oidc_callback`

### 2. Required Realm Roles

Create these roles in your Keycloak realm:
- `app_admin` - For administrative users
- `tribunal_member` - For tribunal members (assigned to all personas)

### 3. Service Account Configuration

For the admin client to work:
1. Go to your client's **Service Account Roles** tab
2. Assign these roles to the service account:
   - `realm-admin` (from realm-management client)
   - `manage-users` (from realm-management client)
   - `view-users` (from realm-management client)

### 4. Environment Variables

Set these environment variables:
```bash
# Basic OIDC Configuration
KEYCLOAK_SERVER_URL=http://localhost:8080
KEYCLOAK_REALM=my-app-realm
KEYCLOAK_CLIENT_ID=selecciones-docentes
KEYCLOAK_CLIENT_SECRET=your-client-secret

# Admin API Configuration  
KEYCLOAK_ADMIN_CLIENT_ID=selecciones-docentes
KEYCLOAK_ADMIN_CLIENT_SECRET=your-client-secret

# Application URLs
KEYCLOAK_REDIRECT_URI=http://localhost:5000/oidc_callback
KEYCLOAK_POST_LOGOUT_REDIRECT_URI=http://localhost:5000/

# Role Names (optional - defaults provided)
KEYCLOAK_ADMIN_ROLE=app_admin
KEYCLOAK_TRIBUNAL_ROLE=tribunal_member
```

## Testing the Integration

Run the test script to verify the setup:

```bash
cd /path/to/sistema_concursos_docentes
python test_keycloak_personas.py
```

This will:
- Test connection to Keycloak
- Verify role existence
- List available roles
- Show current configuration

## User Creation Flow

When creating a new persona through the admin interface:

1. **Form Validation**: Required fields (nombre, apellido, dni, correo) are validated
2. **Local Duplicate Check**: Checks if persona exists in local DB by DNI or email
3. **Keycloak User Check**: Checks if user exists in Keycloak by email or username (DNI)
4. **User Creation**: Creates user in Keycloak if it doesn't exist
5. **Role Assignment**: Assigns `tribunal_member` role (always) and `app_admin` role (if selected)
6. **Local Record**: Creates persona record with link to Keycloak user ID
7. **Password Setup**: Sends password setup email or provides temporary password

## Error Handling

The integration includes comprehensive error handling:
- **Connection Issues**: Graceful degradation if Keycloak is unavailable
- **Role Validation**: Checks if roles exist before assignment
- **Duplicate Users**: Handles existing users gracefully
- **Detailed Feedback**: Flash messages inform users of success/failure status

## Troubleshooting

### Common Issues:

1. **Role Assignment Fails**
   - Verify roles exist in Keycloak realm
   - Check service account has proper permissions
   - Run test script to validate role existence

2. **User Creation Fails**
   - Check admin client credentials
   - Verify service account permissions
   - Check server URL and realm name

3. **Connection Issues**
   - Verify Keycloak server is running
   - Check firewall/network connectivity
   - Validate environment variables

### Debug Information

Enable debug logging in your Flask app:
```python
import logging
logging.getLogger('app.integrations.keycloak_admin_client').setLevel(logging.DEBUG)
```

## Files Modified

- `app/integrations/keycloak_admin_client.py` - Enhanced admin client with duplicate detection and role validation
- `app/routes/admin_personas.py` - Improved user creation and role assignment logic
- `test_keycloak_personas.py` - New test script for validation

## Next Steps

1. **Test the Integration**: Run the test script and create a test persona
2. **Environment Setup**: Configure your environment variables
3. **Role Creation**: Create required roles in Keycloak
4. **Service Account**: Configure service account permissions
5. **Production Testing**: Test with your actual Keycloak instance
