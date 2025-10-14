"""
Keycloak-Persona Synchronization Service

This service handles bidirectional synchronization between:
- Local Persona records in the database
- Keycloak users with the tribunal_member role

Features:
- Sync personas to Keycloak (create users, assign roles)
- Sync Keycloak users to personas (create local records)
- Update existing records in both directions
- Handle role assignments and removals
- Maintain data consistency between systems
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from flask import current_app
from sqlalchemy.exc import IntegrityError

from app.models.models import db, Persona  
from app.integrations.keycloak_admin_client import get_keycloak_admin
from app.config.keycloak_config import KeycloakConfig

logger = logging.getLogger(__name__)


class KeycloakPersonaSyncService:
    """Service for synchronizing personas with Keycloak users."""
    
    def __init__(self):
        self.keycloak_admin = get_keycloak_admin()
        self.tribunal_role = KeycloakConfig.KEYCLOAK_TRIBUNAL_ROLE
        self.admin_role = KeycloakConfig.KEYCLOAK_ADMIN_ROLE
        
    def sync_all(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Perform full bidirectional synchronization.
        
        Args:
            dry_run: If True, only report what would be done without making changes
            
        Returns:
            Dictionary with sync results and statistics
        """
        if not self.keycloak_admin:
            return {
                'success': False,
                'error': 'Keycloak admin client not available'
            }
            
        logger.info(f"Starting full sync (dry_run={dry_run})")
        
        results = {
            'success': True,
            'dry_run': dry_run,
            'timestamp': datetime.utcnow().isoformat(),
            'personas_to_keycloak': {},
            'keycloak_to_personas': {},
            'updates': {},
            'errors': []
        }
               
        try:
            # Step 1: Sync personas to Keycloak
            logger.info("Step 1: Syncing personas to Keycloak")
            personas_sync = self.sync_personas_to_keycloak(dry_run=dry_run)
            results['personas_to_keycloak'] = personas_sync
            
            # Step 2: Sync Keycloak users to personas
            logger.info("Step 2: Syncing Keycloak users to personas")
            keycloak_sync = self.sync_keycloak_to_personas(dry_run=dry_run)
            results['keycloak_to_personas'] = keycloak_sync
            
            # Step 3: Update existing records
            logger.info("Step 3: Updating existing records")
            updates_sync = self.sync_updates(dry_run=dry_run)
            results['updates'] = updates_sync
            
            # Calculate totals
            results['summary'] = {
                'personas_created_in_keycloak': len(personas_sync.get('created', [])),
                'personas_updated_in_keycloak': len(personas_sync.get('updated', [])),
                'personas_created_locally': len(keycloak_sync.get('created', [])),
                'personas_updated_locally': len(keycloak_sync.get('updated', [])),
                'records_synchronized': len(updates_sync.get('synchronized', [])),
                'total_errors': len(results['errors'])
            }
            
            logger.info(f"Sync completed successfully: {results['summary']}")
            
        except Exception as e:
            logger.error(f"Sync failed with error: {e}")
            results['success'] = False
            results['errors'].append(f"Sync failed: {str(e)}")
            
        return results
    
    def sync_personas_to_keycloak(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Sync local personas to Keycloak users.
        Creates Keycloak users for personas that don't have keycloak_user_id.
        """
        results = {
            'created': [],
            'updated': [],
            'skipped': [],
            'errors': []
        }
        
        # Get all personas without keycloak_user_id
        personas_without_keycloak = Persona.query.filter(
            Persona.keycloak_user_id.is_(None)
        ).all()
        
        logger.info(f"Found {len(personas_without_keycloak)} personas without Keycloak users")
        
        for persona in personas_without_keycloak:
            try:
                # Check if user already exists in Keycloak by email or username
                existing_user = None
                if persona.correo:
                    existing_user = self.keycloak_admin.get_user_by_email(persona.correo)
                
                if not existing_user and persona.username:
                    existing_user = self.keycloak_admin.get_user_by_username(persona.username)
                
                if not existing_user and persona.dni:
                    existing_user = self.keycloak_admin.get_user_by_username(persona.dni)
                
                if existing_user:
                    # User exists, just link them
                    if not dry_run:
                        persona.keycloak_user_id = existing_user['id']
                        
                        # Ensure tribunal_member role is assigned
                        if not self.keycloak_admin.assign_client_role(existing_user['id'], self.tribunal_role):
                            logger.warning(f"Failed to assign tribunal_member role to existing user {existing_user['id']}")
                        
                        # Assign admin role if persona is admin
                        if persona.is_admin:
                            if not self.keycloak_admin.assign_client_role(existing_user['id'], self.admin_role):
                                logger.warning(f"Failed to assign admin role to existing user {existing_user['id']}")
                        
                        db.session.commit()
                    
                    results['updated'].append({
                        'persona_id': persona.id,
                        'persona_name': f"{persona.apellido}, {persona.nombre}",
                        'keycloak_user_id': existing_user['id'],
                        'action': 'linked_existing_user'
                    })
                    logger.info(f"Linked persona {persona.id} to existing Keycloak user {existing_user['id']}")
                    
                else:
                    # Create new user in Keycloak
                    if not persona.correo:
                        results['errors'].append({
                            'persona_id': persona.id,
                            'error': 'Cannot create Keycloak user without email'
                        })
                        continue
                    
                    username = persona.username or persona.dni or persona.correo
                    
                    user_data = {
                        'username': username,
                        'email': persona.correo,
                        'firstName': persona.nombre,
                        'lastName': persona.apellido,
                        'attributes': {
                            'dni': persona.dni or '',
                            'telefono': persona.telefono or '',
                            'cargo': persona.cargo or ''
                        }
                    }
                    
                    if not dry_run:
                        keycloak_user_id = self.keycloak_admin.create_user(user_data)
                        
                        if keycloak_user_id:
                            # Link the user
                            persona.keycloak_user_id = keycloak_user_id
                            
                            # Assign tribunal_member role
                            if not self.keycloak_admin.assign_client_role(keycloak_user_id, self.tribunal_role):
                                logger.warning(f"Failed to assign tribunal_member role to new user {keycloak_user_id}")
                              # Assign admin role if needed
                            if persona.is_admin:
                                if not self.keycloak_admin.assign_client_role(keycloak_user_id, self.admin_role):
                                    logger.warning(f"Failed to assign admin role to new user {keycloak_user_id}")
                            
                            # User created successfully (no email sent)
                            db.session.commit()
                            
                            results['created'].append({
                                'persona_id': persona.id,
                                'persona_name': f"{persona.apellido}, {persona.nombre}",
                                'keycloak_user_id': keycloak_user_id,
                                'action': 'created_new_user'
                            })
                            logger.info(f"Created Keycloak user {keycloak_user_id} for persona {persona.id}")
                        else:
                            results['errors'].append({
                                'persona_id': persona.id,
                                'error': 'Failed to create Keycloak user'
                            })
                    else:
                        results['created'].append({
                            'persona_id': persona.id,
                            'persona_name': f"{persona.apellido}, {persona.nombre}",
                            'action': 'would_create_new_user',
                            'user_data': user_data
                        })
                        
            except Exception as e:
                logger.error(f"Error syncing persona {persona.id} to Keycloak: {e}")
                results['errors'].append({
                    'persona_id': persona.id,
                    'error': str(e)
                })
        
        return results
    
    def sync_keycloak_to_personas(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Sync Keycloak users with tribunal_member and/or admin role to local personas.
        Creates or links local personas for Keycloak users that don't have corresponding personas.
        """
        results = {
            'created': [],
            'updated': [],
            'skipped': [],
            'errors': []
        }
        
        try:
            # Get all users with tribunal_member role and admin role, then union
            tribunal_users = self._get_users_with_role(self.tribunal_role)
            admin_users = self._get_users_with_role(self.admin_role)
            logger.info(f"Found {len(tribunal_users)} users with {self.tribunal_role} role and {len(admin_users)} users with {self.admin_role} role in Keycloak")

            users_map: Dict[str, Dict[str, Any]] = {u['id']: u for u in tribunal_users}
            for u in admin_users:
                users_map.setdefault(u['id'], u)

            users = list(users_map.values())

            for user in users:
                try:
                    # Fetch roles once for this user
                    user_roles = self.keycloak_admin.get_user_client_roles(user['id']) if self.keycloak_admin else []
                    has_admin_role = self.admin_role in user_roles
                    has_tribunal_role = self.tribunal_role in user_roles

                    # Check if persona already exists
                    existing_persona = Persona.query.filter_by(keycloak_user_id=user['id']).first()
                    
                    if existing_persona:
                        # Keep local admin flag in sync with Keycloak admin role
                        admin_changed = False
                        if existing_persona.is_admin != has_admin_role:
                            if not dry_run:
                                existing_persona.is_admin = has_admin_role
                                if not has_admin_role:
                                    # If removing admin locally, also clear cargo
                                    existing_persona.cargo = None
                                db.session.commit()
                            admin_changed = True
                        
                        results['skipped'].append({
                            'keycloak_user_id': user['id'],
                            'persona_id': existing_persona.id,
                            'reason': 'persona_already_exists',
                            'admin_role_synced': admin_changed
                        })
                        continue
                    
                    # Check if persona exists by email or username
                    email = user.get('email')
                    username = user.get('username')
                    
                    existing_persona = None
                    if email:
                        existing_persona = Persona.query.filter_by(correo=email).first()
                    
                    if not existing_persona and username:
                        existing_persona = Persona.query.filter(
                            (Persona.username == username) | (Persona.dni == username)
                        ).first()
                    
                    if existing_persona:
                        # Link existing persona to Keycloak user
                        if not dry_run:
                            existing_persona.keycloak_user_id = user['id']
                            # Sync admin flag from Keycloak
                            existing_persona.is_admin = has_admin_role
                            if not has_admin_role:
                                existing_persona.cargo = None
                            db.session.commit()
                        
                        results['updated'].append({
                            'keycloak_user_id': user['id'],
                            'persona_id': existing_persona.id,
                            'action': 'linked_existing_persona',
                            'is_admin': has_admin_role
                        })
                        logger.info(f"Linked existing persona {existing_persona.id} to Keycloak user {user['id']}")
                        
                    else:
                        # Create new persona
                        # We need either email or username to create a persona
                        if not email and not username:
                            results['errors'].append({
                                'keycloak_user_id': user['id'],
                                'error': 'Cannot create persona without email or username'
                            })
                            continue
                        
                        # Extract attributes
                        attributes = user.get('attributes', {})
                        dni = attributes.get('dni', [None])[0] if 'dni' in attributes else username
                        telefono = attributes.get('telefono', [None])[0] if 'telefono' in attributes else None
                        cargo = attributes.get('cargo', [None])[0] if 'cargo' in attributes else None                        
                        # Use the real email from Keycloak (can be None if user has no email)
                        correo = email  # Use actual Keycloak email, don't create placeholder
                        
                        # Use real first name and last name from Keycloak
                        nombre = user.get('firstName', '').strip()
                        apellido = user.get('lastName', '').strip()
                        
                        # Validate for duplicates before creating
                        validation_errors = []
                        
                        # Check for duplicate DNI
                        if dni:
                            existing_dni = Persona.query.filter_by(dni=dni).first()
                            if existing_dni:
                                validation_errors.append(f"DNI {dni} already exists")
                        
                        # Check for duplicate correo (only if it's a real email, not placeholder)
                        if correo and not correo.endswith('@noemail.local'):
                            existing_email = Persona.query.filter_by(correo=correo).first()
                            if existing_email:
                                validation_errors.append(f"Email {correo} already exists")
                        
                        # Check for duplicate username
                        if username:
                            existing_username = Persona.query.filter_by(username=username).first()
                            if existing_username:
                                validation_errors.append(f"Username {username} already exists")
                        
                        # If validation errors, skip creation
                        if validation_errors:
                            results['errors'].append({
                                'keycloak_user_id': user['id'],
                                'error': f'Duplicate validation failed: {"; ".join(validation_errors)}'
                            })
                            continue
                        
                        # Note: When syncing from Keycloak to personas, now we also include admin-only users
                        # and we set local is_admin flag according to Keycloak admin role.

                        if not dry_run:
                            new_persona = Persona(
                                nombre=nombre,
                                apellido=apellido,
                                dni=dni,
                                correo=correo,
                                telefono=telefono,
                                username=username,
                                keycloak_user_id=user['id'],
                                is_admin=has_admin_role,
                                cargo=cargo if has_admin_role else None
                            )
                            
                            try:
                                db.session.add(new_persona)
                                db.session.commit()
                                
                                results['created'].append({
                                    'keycloak_user_id': user['id'],
                                    'persona_id': new_persona.id,
                                    'persona_name': f"{new_persona.apellido}, {new_persona.nombre}",
                                    'action': 'created_new_persona',
                                    'is_admin': has_admin_role
                                })                                
                                logger.info(f"Created persona {new_persona.id} for Keycloak user {user['id']}")
                                
                            except IntegrityError as e:
                                db.session.rollback()
                                results['errors'].append({
                                    'keycloak_user_id': user['id'],
                                    'error': f'Database integrity error: {str(e)}'
                                })
                                
                        else:
                            results['created'].append({
                                'keycloak_user_id': user['id'],
                                'action': 'would_create_new_persona',
                                'persona_data': {
                                    'nombre': nombre,
                                    'apellido': apellido,
                                    'dni': dni,
                                    'correo': correo,
                                    'telefono': telefono,
                                    'username': username,
                                    'is_admin': has_admin_role,
                                    'cargo': cargo if has_admin_role else None
                                }
                            })
                            
                except Exception as e:
                    logger.error(f"Error syncing Keycloak user {user['id']} to persona: {e}")
                    results['errors'].append({
                        'keycloak_user_id': user['id'],
                        'error': str(e)
                    })
                    
        except Exception as e:
            logger.error(f"Error getting users from Keycloak: {e}")
            results['errors'].append({
                'error': f'Failed to get users: {str(e)}'
            })
        return results
    
    def sync_updates(self, dry_run: bool = False, sync_user_data: bool = False) -> Dict[str, Any]:
        """
        Synchronize updates between existing linked personas and Keycloak users.
        
        Args:
            dry_run: If True, only report what would be done without making changes
            sync_user_data: If True, sync user data (name, email, etc.). If False, only sync roles.
        """
        results = {
            'synchronized': [],
            'role_updates': [],
            'errors': []
        }
        
        # Get all personas with linked Keycloak users
        linked_personas = Persona.query.filter(
            Persona.keycloak_user_id.isnot(None)
        ).all()
        
        logger.info(f"Found {len(linked_personas)} linked personas to synchronize")
        
        for persona in linked_personas:
            try:
                # Get Keycloak user
                keycloak_user = self.keycloak_admin.get_user_by_id(persona.keycloak_user_id)
                if not keycloak_user:
                    results['errors'].append({
                        'persona_id': persona.id,
                        'keycloak_user_id': persona.keycloak_user_id,
                        'error': 'Keycloak user not found'
                    })
                    continue
                
                # Only sync user data if explicitly requested
                if sync_user_data:
                    # Check if user information needs updating
                    updates_needed = {}
                    
                    # Only update email if persona has a valid email (don't overwrite with empty values)
                    if persona.correo and keycloak_user.get('email') != persona.correo:
                        updates_needed['email'] = persona.correo
                    elif not persona.correo and keycloak_user.get('email'):
                        # If persona has no email but Keycloak user does, keep the Keycloak email
                        # This prevents deleting emails from Keycloak when persona email is empty
                        logger.info(f"Persona {persona.id} has no email, keeping Keycloak email: {keycloak_user.get('email')}")
                    
                    if keycloak_user.get('firstName') != persona.nombre:
                        updates_needed['firstName'] = persona.nombre
                    if keycloak_user.get('lastName') != persona.apellido:
                        updates_needed['lastName'] = persona.apellido
                    
                    # Check attributes
                    attributes = keycloak_user.get('attributes', {})
                    current_dni = attributes.get('dni', [None])[0] if 'dni' in attributes else None
                    current_telefono = attributes.get('telefono', [None])[0] if 'telefono' in attributes else None
                    current_cargo = attributes.get('cargo', [None])[0] if 'cargo' in attributes else None
                    
                    if current_dni != persona.dni:
                        if 'attributes' not in updates_needed:
                            updates_needed['attributes'] = {}
                        updates_needed['attributes']['dni'] = persona.dni or ''
                    
                    if current_telefono != persona.telefono:
                        if 'attributes' not in updates_needed:
                            updates_needed['attributes'] = {}
                        updates_needed['attributes']['telefono'] = persona.telefono or ''
                    
                    if current_cargo != persona.cargo:
                        if 'attributes' not in updates_needed:
                            updates_needed['attributes'] = {}
                        updates_needed['attributes']['cargo'] = persona.cargo or ''
                    
                    # Update user information if needed
                    if updates_needed:
                        if not dry_run:
                            if self.keycloak_admin.update_user(persona.keycloak_user_id, updates_needed):
                                logger.info(f"Updated Keycloak user {persona.keycloak_user_id} for persona {persona.id}")
                            else:
                                results['errors'].append({
                                    'persona_id': persona.id,
                                    'keycloak_user_id': persona.keycloak_user_id,
                                    'error': 'Failed to update Keycloak user'
                                })
                                continue
                        
                        results['synchronized'].append({
                            'persona_id': persona.id,
                            'keycloak_user_id': persona.keycloak_user_id,
                            'updates': updates_needed
                        })
                else:
                    logger.info(f"Skipping user data sync for persona {persona.id} (sync_user_data=False)")
                    results['skipped'].append({
                        'persona_id': persona.id,
                        'keycloak_user_id': persona.keycloak_user_id,
                        'reason': 'sync_user_data=False'
                    })
                
                # Check role assignments
                user_roles = self.keycloak_admin.get_user_client_roles(persona.keycloak_user_id)
                has_admin_role = self.admin_role in user_roles
                has_tribunal_role = self.tribunal_role in user_roles
                
                role_changes = []
                
                # Ensure tribunal_member role is always assigned
                if not has_tribunal_role:
                    if not dry_run:
                        if self.keycloak_admin.assign_client_role(persona.keycloak_user_id, self.tribunal_role):
                            role_changes.append(f"assigned {self.tribunal_role}")
                        else:
                            results['errors'].append({
                                'persona_id': persona.id,
                                'keycloak_user_id': persona.keycloak_user_id,
                                'error': f'Failed to assign {self.tribunal_role} role'
                            })
                    else:
                        role_changes.append(f"would assign {self.tribunal_role}")
                
                # Handle admin role based on persona.is_admin
                if persona.is_admin and not has_admin_role:
                    if not dry_run:
                        if self.keycloak_admin.assign_client_role(persona.keycloak_user_id, self.admin_role):
                            role_changes.append(f"assigned {self.admin_role}")
                        else:
                            results['errors'].append({
                                'persona_id': persona.id,
                                'keycloak_user_id': persona.keycloak_user_id,
                                'error': f'Failed to assign {self.admin_role} role'
                            })
                    else:
                        role_changes.append(f"would assign {self.admin_role}")
                        
                elif not persona.is_admin and has_admin_role:
                    if not dry_run:
                        if self.keycloak_admin.remove_client_role(persona.keycloak_user_id, self.admin_role):
                            role_changes.append(f"removed {self.admin_role}")
                        else:
                            results['errors'].append({
                                'persona_id': persona.id,
                                'keycloak_user_id': persona.keycloak_user_id,
                                'error': f'Failed to remove {self.admin_role} role'
                            })
                    else:
                        role_changes.append(f"would remove {self.admin_role}")
                
                if role_changes:
                    results['role_updates'].append({
                        'persona_id': persona.id,
                        'keycloak_user_id': persona.keycloak_user_id,
                        'changes': role_changes
                    })
                    
            except Exception as e:
                logger.error(f"Error synchronizing persona {persona.id}: {e}")
                results['errors'].append({
                    'persona_id': persona.id,
                    'keycloak_user_id': persona.keycloak_user_id,
                    'error': str(e)
                })
        
        return results
    
    def _get_users_with_role(self, role_name: str) -> List[Dict[str, Any]]:
        """Get all users with a specific client role."""
        try:
            # Get all users
            all_users = self.keycloak_admin.search_users({})
            
            # Filter users with the specified role
            users_with_role = []
            for user in all_users:
                user_roles = self.keycloak_admin.get_user_client_roles(user['id'])
                if role_name in user_roles:
                    users_with_role.append(user)
            
            return users_with_role
            
        except Exception as e:
            logger.error(f"Error getting users with role {role_name}: {e}")
            return []
    
    def remove_orphaned_personas(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Remove personas whose corresponding Keycloak users no longer have tribunal_member role
        and are not app admins. Admin-only users are preserved.
        WARNING: This is a destructive operation.
        """
        results = {
            'removed': [],
            'errors': []
        }
        
        # Get all personas with Keycloak user IDs
        linked_personas = Persona.query.filter(
            Persona.keycloak_user_id.isnot(None)
        ).all()
        
        for persona in linked_personas:
            try:
                # Check if user still exists and has tribunal_member role
                keycloak_user = self.keycloak_admin.get_user_by_id(persona.keycloak_user_id)
                
                if not keycloak_user:
                    # User no longer exists in Keycloak
                    if not dry_run:
                        # Check if persona has any tribunal assignments
                        if persona.asignaciones.count() > 0:
                            results['errors'].append({
                                'persona_id': persona.id,
                                'error': 'Cannot remove persona with tribunal assignments'
                            })
                            continue
                        
                        db.session.delete(persona)
                        db.session.commit()
                    
                    results['removed'].append({
                        'persona_id': persona.id,
                        'persona_name': f"{persona.apellido}, {persona.nombre}",
                        'reason': 'keycloak_user_not_found'
                    })
                    continue
                
                # Check roles: only remove if lacks tribunal role AND lacks admin role
                user_roles = self.keycloak_admin.get_user_client_roles(persona.keycloak_user_id)
                if (self.tribunal_role not in user_roles) and (self.admin_role not in user_roles):
                    if not dry_run:
                        # Check if persona has any tribunal assignments
                        if persona.asignaciones.count() > 0:
                            results['errors'].append({
                                'persona_id': persona.id,
                                'error': 'Cannot remove persona with tribunal assignments'
                            })
                            continue
                        
                        db.session.delete(persona)
                        db.session.commit()
                    
                    results['removed'].append({
                        'persona_id': persona.id,
                        'persona_name': f"{persona.apellido}, {persona.nombre}",
                        'reason': 'no_longer_has_required_roles'
                    })
                else:
                    # Preserve user as they still have admin or tribunal role
                    results['errors'].append({
                        'persona_id': persona.id,
                        'info': 'Persona retained due to admin or tribunal role present'
                    })
                    
            except Exception as e:
                logger.error(f"Error checking persona {persona.id} for removal: {e}")
                results['errors'].append({
                    'persona_id': persona.id,
                    'error': str(e)
                })
        
        return results


# Global instance
_sync_service = None

def get_sync_service() -> KeycloakPersonaSyncService:
    """Get the global sync service instance (lazy loaded)."""
    global _sync_service
    if _sync_service is None:
        _sync_service = KeycloakPersonaSyncService()
    return _sync_service
