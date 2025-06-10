# Tribunal Notification System Refactoring

## Summary of Changes

The tribunal notification system has been simplified and improved to remove all sustanciación-related content and make it a simple credential notification system.

## Key Changes Made

### 1. **Removed "Notificar Sustanciación" Functionality**
- ✅ Deleted `/notificar-sustanciacion/<int:concurso_id>` route
- ✅ Deleted `notificar_sustanciacion.html` template
- ✅ Removed references to `notificado_sustanciacion` and `fecha_notificacion_sustanciacion` fields

### 2. **New "Notificar Todos" Functionality**
- ✅ Created `/concurso/<int:concurso_id>/notificar-todos` route
- ✅ Sends notifications to ALL tribunal members at once (excluding suplentes)
- ✅ Smart password handling:
  - **Users with existing passwords** → Get login page link
  - **Users without passwords** → Get password setup link

### 3. **Improved Individual Notification**
- ✅ Simplified `notificar_miembro` function
- ✅ Removed ALL sustanciación-related content
- ✅ Smart password detection using `persona.password_hash is not None`

### 4. **Enhanced Template**
- ✅ Added "Notificar Todos" button in tribunal index
- ✅ Improved status display to show password configuration status
- ✅ Added individual notification button for each member
- ✅ Fixed template variable references

## Smart Password Handling Logic

### For Users WITHOUT Password Set:
```
Subject: "Configuración de Credenciales - Portal de Tribunal"
Content: 
- Username (DNI)
- Reset token link to set password
- Portal access URL for future use
- Concurso information
```

### For Users WITH Password Already Set:
```
Subject: "Acceso al Portal de Tribunal"
Content:
- Username reminder (DNI)
- Direct link to tribunal login portal
- Concurso information
```

## How to Use

### Notify All Members at Once:
1. Go to tribunal index page
2. Click "Notificar Todos" button
3. System automatically:
   - Skips members without email
   - Sends appropriate message based on password status
   - Updates notification status
   - Shows results summary

### Notify Individual Member:
1. Click the envelope icon (📧) next to any member
2. System sends appropriate notification based on password status

## Benefits

1. **Simplified Logic**: No more complex sustanciación logic
2. **Smart Password Handling**: Different messages for users with/without passwords
3. **Better User Experience**: Clear status indicators and appropriate messages
4. **Bulk Operations**: Can notify all members at once
5. **Error Handling**: Proper error reporting and validation
6. **Status Tracking**: Clear visibility of who has been notified and password status

## Technical Details

### Password Detection:
```python
has_password = persona.password_hash is not None
```

### Status Display Priority:
1. 🟢 **Password Configured** (Green) - User has set their password
2. 🔵 **Credenciales Enviadas** (Blue) - Notification sent but password not set
3. 🟡 **No notificado** (Yellow) - No notification sent yet

### Email Subject Lines:
- **New Users**: "Configuración de Credenciales - Portal de Tribunal"
- **Existing Users**: "Acceso al Portal de Tribunal"

## Files Modified

1. `app/routes/tribunal.py`
   - Added `notificar_todos_miembros()` route
   - Simplified `notificar_miembro()` function
   - Added missing imports (string, random)

2. `app/templates/tribunal/index.html`
   - Added "Notificar Todos" button
   - Improved status display
   - Added individual notification buttons
   - Fixed template variable references

3. **Deleted Files**:
   - `app/templates/tribunal/notificar_sustanciacion.html`

## Next Steps

The system is now ready to use with the simplified notification logic. All sustanciación-related notification functionality has been removed, making the system cleaner and more focused on credential management.
