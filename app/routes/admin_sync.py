"""
Admin routes for Keycloak-Persona synchronization management.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.services.keycloak_persona_sync import get_sync_service
from app.utils.keycloak_auth import keycloak_login_required, admin_required
import logging

logger = logging.getLogger(__name__)
admin_sync_bp = Blueprint('admin_sync', __name__, url_prefix='/admin/sync')

@admin_sync_bp.route('/', methods=['GET'])
@keycloak_login_required
@admin_required
def sync_dashboard():
    """Display the synchronization dashboard."""
    return render_template('admin/sync/dashboard.html')

@admin_sync_bp.route('/status', methods=['GET'])
@keycloak_login_required
@admin_required
def sync_status():
    """Get current sync status and statistics."""
    try:
        sync_service = get_sync_service()
        
        # Get dry run results to show what would be synced
        results = sync_service.sync_all(dry_run=True)
        
        return jsonify({
            'success': True,
            'status': results
        })
    except Exception as e:
        logger.error(f"Error getting sync status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_sync_bp.route('/run', methods=['POST'])
@keycloak_login_required
@admin_required
def run_sync():
    """Execute full synchronization."""
    try:
        sync_service = get_sync_service()
        
        # Get options from request
        dry_run = request.json.get('dry_run', False) if request.is_json else request.form.get('dry_run') == 'true'
        
        # Run synchronization
        results = sync_service.sync_all(dry_run=dry_run)
        
        if request.is_json:
            return jsonify(results)
        else:
            # Handle form submission
            if results['success']:
                summary = results['summary']
                message = f"Sincronización completada. "
                message += f"Creados en Keycloak: {summary['personas_created_in_keycloak']}, "
                message += f"Creados localmente: {summary['personas_created_locally']}, "
                message += f"Actualizados: {summary['records_synchronized']}"
                
                if summary['total_errors'] > 0:
                    message += f". Errores: {summary['total_errors']}"
                    flash(message, 'warning')
                else:
                    flash(message, 'success')
            else:
                flash(f"Error en la sincronización: {', '.join(results['errors'])}", 'danger')
            
            return redirect(url_for('admin_sync.sync_dashboard'))
            
    except Exception as e:
        logger.error(f"Error running sync: {e}")
        error_msg = f"Error ejecutando sincronización: {str(e)}"
        
        if request.is_json:
            return jsonify({
                'success': False,
                'error': error_msg
            }), 500
        else:
            flash(error_msg, 'danger')
            return redirect(url_for('admin_sync.sync_dashboard'))

@admin_sync_bp.route('/personas-to-keycloak', methods=['POST'])
@keycloak_login_required
@admin_required
def sync_personas_to_keycloak():
    """Sync personas to Keycloak only."""
    try:
        sync_service = get_sync_service()
        dry_run = request.json.get('dry_run', False) if request.is_json else request.form.get('dry_run') == 'true'
        
        results = sync_service.sync_personas_to_keycloak(dry_run=dry_run)
        
        if request.is_json:
            return jsonify({
                'success': True,
                'results': results
            })
        else:
            created_count = len(results['created'])
            updated_count = len(results['updated'])
            error_count = len(results['errors'])
            
            message = f"Sincronización personas → Keycloak: {created_count} creados, {updated_count} actualizados"
            if error_count > 0:
                message += f", {error_count} errores"
                flash(message, 'warning')
            else:
                flash(message, 'success')
            
            return redirect(url_for('admin_sync.sync_dashboard'))
            
    except Exception as e:
        logger.error(f"Error syncing personas to Keycloak: {e}")
        error_msg = f"Error sincronizando personas a Keycloak: {str(e)}"
        
        if request.is_json:
            return jsonify({
                'success': False,
                'error': error_msg
            }), 500
        else:
            flash(error_msg, 'danger')
            return redirect(url_for('admin_sync.sync_dashboard'))

@admin_sync_bp.route('/keycloak-to-personas', methods=['POST'])
@keycloak_login_required
@admin_required
def sync_keycloak_to_personas():
    """Sync Keycloak users to personas only."""
    try:
        sync_service = get_sync_service()
        dry_run = request.json.get('dry_run', False) if request.is_json else request.form.get('dry_run') == 'true'
        
        results = sync_service.sync_keycloak_to_personas(dry_run=dry_run)
        
        if request.is_json:
            return jsonify({
                'success': True,
                'results': results
            })
        else:
            created_count = len(results['created'])
            updated_count = len(results['updated'])
            error_count = len(results['errors'])
            
            message = f"Sincronización Keycloak → personas: {created_count} creados, {updated_count} actualizados"
            if error_count > 0:
                message += f", {error_count} errores"
                flash(message, 'warning')
            else:
                flash(message, 'success')
            
            return redirect(url_for('admin_sync.sync_dashboard'))
            
    except Exception as e:
        logger.error(f"Error syncing Keycloak to personas: {e}")
        error_msg = f"Error sincronizando Keycloak a personas: {str(e)}"
        
        if request.is_json:
            return jsonify({
                'success': False,
                'error': error_msg
            }), 500
        else:
            flash(error_msg, 'danger')
            return redirect(url_for('admin_sync.sync_dashboard'))

@admin_sync_bp.route('/remove-orphaned', methods=['POST'])
@keycloak_login_required
@admin_required
def remove_orphaned_personas():
    """Remove personas that no longer have corresponding Keycloak users with tribunal_member role."""
    try:
        sync_service = get_sync_service()
        dry_run = request.json.get('dry_run', False) if request.is_json else request.form.get('dry_run') == 'true'
        
        # This is a destructive operation, require explicit confirmation
        if not dry_run:
            confirm = request.json.get('confirm', False) if request.is_json else request.form.get('confirm') == 'true'
            if not confirm:
                error_msg = "Esta operación requiere confirmación explícita"
                if request.is_json:
                    return jsonify({
                        'success': False,
                        'error': error_msg
                    }), 400
                else:
                    flash(error_msg, 'danger')
                    return redirect(url_for('admin_sync.sync_dashboard'))
        
        results = sync_service.remove_orphaned_personas(dry_run=dry_run)
        
        if request.is_json:
            return jsonify({
                'success': True,
                'results': results
            })
        else:
            removed_count = len(results['removed'])
            error_count = len(results['errors'])
            
            if dry_run:
                message = f"Se eliminarían {removed_count} personas huérfanas"
            else:
                message = f"Eliminadas {removed_count} personas huérfanas"
            
            if error_count > 0:
                message += f", {error_count} errores"
                flash(message, 'warning')
            else:
                flash(message, 'info' if dry_run else 'success')
            
            return redirect(url_for('admin_sync.sync_dashboard'))
            
    except Exception as e:
        logger.error(f"Error removing orphaned personas: {e}")
        error_msg = f"Error eliminando personas huérfanas: {str(e)}"
        
        if request.is_json:
            return jsonify({
                'success': False,
                'error': error_msg
            }), 500
        else:
            flash(error_msg, 'danger')
            return redirect(url_for('admin_sync.sync_dashboard'))
