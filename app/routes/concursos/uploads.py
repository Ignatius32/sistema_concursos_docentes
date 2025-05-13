from flask import redirect, url_for, flash, request
from flask_login import login_required, current_user
from datetime import datetime
from app.models.models import db, Concurso, HistorialEstado
from . import concursos, drive_api

@concursos.route('/<int:concurso_id>/cargar-tkd', methods=['POST'])
@login_required
def cargar_tkd(concurso_id):
    """Upload or update TKD number and file for a concurso."""
    concurso = Concurso.query.get_or_404(concurso_id)
    
    try:
        # Get TKD number from form
        tkd_number = request.form.get('tkd_number', '').strip()
        if not tkd_number:
            flash('Debe ingresar un número de TKD', 'warning')
            return redirect(url_for('concursos.ver', concurso_id=concurso_id))
        
        # Get TKD file from form
        tkd_file = request.files.get('tkd_file')
        
        # If no file and no existing file, require file 
        # (although frontend validation should prevent this case)
        if (not tkd_file or not tkd_file.filename) and not concurso.tkd_file_id:
            flash('Debe subir un archivo PDF para el TKD', 'warning')
            return redirect(url_for('concursos.ver', concurso_id=concurso_id))
          # Update TKD number
        old_tkd = concurso.tkd
        concurso.tkd = tkd_number
        concurso.id_designacion_mocovi = tkd_number  # Update MOCOVI ID as well to ensure placeholder works
        
        # Create history record for TKD number update
        if old_tkd != tkd_number:
            historial = HistorialEstado(
                concurso=concurso,
                estado="TKD ACTUALIZADO",
                observaciones=f"Número de TKD actualizado de '{old_tkd or 'vacío'}' a '{tkd_number}'"
            )
            db.session.add(historial)
        
        # Handle file upload if provided
        if tkd_file and tkd_file.filename:
            # Check if documentos_firmados_folder_id exists
            if not concurso.documentos_firmados_folder_id:
                flash('El concurso no tiene una carpeta de documentos firmados configurada', 'danger')
                return redirect(url_for('concursos.ver', concurso_id=concurso_id))
            
            # Generate filename with date and timestamp to avoid duplicates
            now = datetime.now()
            date_str = now.strftime("%Y%m%d")
            timestamp = int(now.timestamp())
            filename = f"TKD_{tkd_number}_{concurso_id}_{date_str}_{timestamp}.pdf"
            
            # Delete old file if exists
            if concurso.tkd_file_id:
                try:
                    drive_api.delete_file(concurso.tkd_file_id)
                except Exception as e:
                    # Log error but continue with upload
                    print(f"Error deleting old TKD file: {str(e)}")
            
            # Upload new file
            file_data = tkd_file.read()
            file_id, file_url = drive_api.upload_document(
                concurso.documentos_firmados_folder_id, 
                filename, 
                file_data
            )
            
            # Update concurso with new file ID
            old_file_id = concurso.tkd_file_id
            concurso.tkd_file_id = file_id
            
            # Create history record for file upload
            action = "cargado" if not old_file_id else "actualizado"
            historial = HistorialEstado(
                concurso=concurso,
                estado="ARCHIVO TKD CARGADO",
                observaciones=f"Archivo TKD {action} para el número {tkd_number}"
            )
            db.session.add(historial)
        
        # Commit all changes
        db.session.commit()
        flash(f'TKD actualizado correctamente', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al actualizar el TKD: {str(e)}', 'danger')
    
    return redirect(url_for('concursos.ver', concurso_id=concurso_id))

@concursos.route('/<int:concurso_id>/borrar-tkd', methods=['POST'])
@login_required
def borrar_tkd(concurso_id):
    """Delete TKD number and file for a concurso."""
    concurso = Concurso.query.get_or_404(concurso_id)
    
    try:
        # Track what was deleted for history
        deleted_items = []
        
        # Delete TKD file if it exists
        if concurso.tkd_file_id:
            try:
                # Use existing delete_file function from GoogleDriveAPI
                drive_api.delete_file(concurso.tkd_file_id)
                deleted_items.append("archivo PDF")
            except Exception as e:
                # Log error but continue with the rest of the deletion
                print(f"Error deleting TKD file: {str(e)}")
            
            # Clear file ID regardless of whether deletion succeeded
            concurso.tkd_file_id = None
        
        # Store the old TKD value for history
        old_tkd = concurso.tkd
          # Delete TKD number if it exists
        if concurso.tkd:
            concurso.tkd = None
            concurso.id_designacion_mocovi = None  # Also clear MOCOVI ID for consistency
            deleted_items.append("número TKD")
        
        # If anything was deleted, create a history record
        if deleted_items:
            historial = HistorialEstado(
                concurso=concurso,
                estado="TKD ELIMINADO",
                observaciones=f"Se eliminó el respaldo TKD: {', '.join(deleted_items)} (valor anterior: '{old_tkd or 'vacío'}')"
            )
            db.session.add(historial)
        
        # Commit changes
        db.session.commit()
        flash(f'TKD respaldo eliminado correctamente', 'success')
    
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el TKD respaldo: {str(e)}', 'danger')
    
    return redirect(url_for('concursos.ver', concurso_id=concurso_id))

@concursos.route('/<int:concurso_id>/gestionar-notas-adicionales', methods=['POST'])
@login_required
def gestionar_notas_adicionales(concurso_id):
    """Upload or update multiple note types for a concurso."""
    concurso = Concurso.query.get_or_404(concurso_id)
    files_processed = 0
    
    # Define configuration for each note type
    note_types = [
        {
            'file_input_name': 'nota_solicitud_sac_file',
            'model_field': 'nota_solicitud_sac_file_id',
            'base_filename': 'Nota Solicitud SAC',
            'estado': 'NOTA SOLICITUD SAC',
            'descripcion': 'Nota Solicitud SAC'
        },
        {
            'file_input_name': 'nota_centro_estudiantes_file',
            'model_field': 'nota_centro_estudiantes_file_id',
            'base_filename': 'Nota Centro Estudiantes',
            'estado': 'NOTA CENTRO ESTUDIANTES',
            'descripcion': 'Nota Centro Estudiantes'
        },
        {
            'file_input_name': 'nota_consulta_depto_file',
            'model_field': 'nota_consulta_depto_file_id',
            'base_filename': 'Nota Consulta Depto Academico',
            'estado': 'NOTA CONSULTA DEPTO',
            'descripcion': 'Nota Consulta a Depto. Académico'
        }
    ]
    
    try:
        # Check if documentos_firmados_folder_id exists
        if not concurso.documentos_firmados_folder_id:
            flash('El concurso no tiene una carpeta de documentos firmados configurada', 'danger')
            return redirect(url_for('concursos.ver', concurso_id=concurso_id))
        
        # Process each note type where a file was uploaded
        for note_type in note_types:
            note_file = request.files.get(note_type['file_input_name'])
            
            # Skip if no file is provided for this note type
            if not note_file or not note_file.filename:
                continue
                
            # Generate filename with date and timestamp to avoid duplicates
            now = datetime.now()
            date_str = now.strftime("%Y%m%d")
            timestamp = int(now.timestamp())
            filename = f"{note_type['base_filename']}_{concurso_id}_{date_str}_{timestamp}.pdf"
            
            # Get current file ID from the model field
            old_file_id = getattr(concurso, note_type['model_field'])
            
            # Delete old file if exists
            if old_file_id:
                try:
                    drive_api.delete_file(old_file_id)
                except Exception as e:
                    # Log error but continue with upload
                    print(f"Error deleting old {note_type['descripcion']} file: {str(e)}")
            
            # Upload new file
            file_data = note_file.read()
            file_id, file_url = drive_api.upload_document(
                concurso.documentos_firmados_folder_id, 
                filename, 
                file_data
            )
            
            # Update concurso with new file ID
            setattr(concurso, note_type['model_field'], file_id)
            
            # Create history record for file upload
            action = "cargada" if not old_file_id else "actualizada"
            action_estado = "CARGADA" if not old_file_id else "ACTUALIZADA"
            historial = HistorialEstado(
                concurso=concurso,
                estado=f"{note_type['estado']} {action_estado}",
                observaciones=f"{note_type['descripcion']} {action} por {current_user.username}"
            )
            db.session.add(historial)
            
            # Increment counter and add success message
            files_processed += 1
            flash(f'{note_type["descripcion"]} {action} correctamente', 'success')
        
        # If no files were processed, show a message
        if files_processed == 0:
            flash('No se seleccionó ningún archivo para cargar o actualizar', 'info')
            return redirect(url_for('concursos.ver', concurso_id=concurso_id))
        
        # Commit all changes
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al gestionar las notas adicionales: {str(e)}', 'danger')
    
    return redirect(url_for('concursos.ver', concurso_id=concurso_id))
