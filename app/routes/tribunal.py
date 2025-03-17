from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from app.models.models import db, Concurso, TribunalMiembro, Recusacion, DocumentoTribunal
from app.integrations.google_drive import GoogleDriveAPI
from datetime import datetime
import os
from werkzeug.utils import secure_filename

tribunal = Blueprint('tribunal', __name__, url_prefix='/tribunal')
drive_api = GoogleDriveAPI()

@tribunal.route('/concurso/<int:concurso_id>')
@login_required
def index(concurso_id):
    """Display tribunal members for a specific concurso."""
    concurso = Concurso.query.get_or_404(concurso_id)
    miembros = TribunalMiembro.query.filter_by(concurso_id=concurso_id).all()
    return render_template('tribunal/index.html', concurso=concurso, miembros=miembros)

@tribunal.route('/concurso/<int:concurso_id>/agregar', methods=['GET', 'POST'])
@login_required
def agregar(concurso_id):
    """Add a new member to the tribunal of a concurso."""
    concurso = Concurso.query.get_or_404(concurso_id)
    
    if request.method == 'POST':
        try:
            # Extract form data
            rol = request.form.get('rol')
            nombre = request.form.get('nombre')
            apellido = request.form.get('apellido')
            dni = request.form.get('dni')
            correo = request.form.get('correo')
            
            # Create Google Drive folder for tribunal member
            folder_name = f"{rol}_{apellido}_{nombre}_{dni}"
            folder_id = drive_api.create_tribunal_folder(
                parent_folder_id=concurso.tribunal_folder_id,
                nombre=nombre,
                apellido=apellido,
                dni=dni,
                rol=rol
            )
            
            # Create new tribunal member
            miembro = TribunalMiembro(
                concurso_id=concurso_id,
                rol=rol,
                nombre=nombre,
                apellido=apellido,
                dni=dni,
                correo=correo,
                drive_folder_id=folder_id
            )
            
            db.session.add(miembro)
            db.session.commit()
            
            flash('Miembro del tribunal agregado exitosamente.', 'success')
            return redirect(url_for('tribunal.index', concurso_id=concurso_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al agregar miembro del tribunal: {str(e)}', 'danger')
    
    return render_template('tribunal/agregar.html', concurso=concurso)

@tribunal.route('/<int:miembro_id>/editar', methods=['GET', 'POST'])
@login_required
def editar(miembro_id):
    """Edit an existing tribunal member."""
    miembro = TribunalMiembro.query.get_or_404(miembro_id)
    concurso = Concurso.query.get_or_404(miembro.concurso_id)
    
    if request.method == 'POST':
        try:
            # Update member data from form
            miembro.rol = request.form.get('rol')
            miembro.nombre = request.form.get('nombre')
            miembro.apellido = request.form.get('apellido')
            miembro.dni = request.form.get('dni')
            miembro.correo = request.form.get('correo')
            
            # Update Drive folder name if needed
            if miembro.drive_folder_id:
                new_folder_name = f"{miembro.rol}_{miembro.apellido}_{miembro.nombre}_{miembro.dni}"
                drive_api.update_folder_name(miembro.drive_folder_id, new_folder_name)
            
            db.session.commit()
            flash('Miembro del tribunal actualizado exitosamente.', 'success')
            return redirect(url_for('tribunal.index', concurso_id=miembro.concurso_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar miembro del tribunal: {str(e)}', 'danger')
    
    return render_template('tribunal/editar.html', miembro=miembro, concurso=concurso)

@tribunal.route('/<int:miembro_id>/eliminar', methods=['POST'])
@login_required
def eliminar(miembro_id):
    """Delete a tribunal member."""
    miembro = TribunalMiembro.query.get_or_404(miembro_id)
    concurso_id = miembro.concurso_id
    
    try:
        # Delete Drive folder if exists
        if miembro.drive_folder_id:
            drive_api.delete_folder(miembro.drive_folder_id)
        
        db.session.delete(miembro)
        db.session.commit()
        flash('Miembro del tribunal eliminado exitosamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar miembro del tribunal: {str(e)}', 'danger')
    
    return redirect(url_for('tribunal.index', concurso_id=concurso_id))

@tribunal.route('/<int:miembro_id>/recusar', methods=['GET', 'POST'])
@login_required
def recusar(miembro_id):
    """Submit a recusation against a tribunal member."""
    miembro = TribunalMiembro.query.get_or_404(miembro_id)
    concurso = Concurso.query.get_or_404(miembro.concurso_id)
    
    if request.method == 'POST':
        try:
            # Create recusation
            recusacion = Recusacion(
                concurso_id=miembro.concurso_id,
                miembro_id=miembro_id,
                motivo=request.form.get('motivo'),
                estado='PRESENTADA'
            )
            
            db.session.add(recusacion)
            db.session.commit()
            
            flash('Recusación presentada correctamente.', 'success')
            return redirect(url_for('tribunal.index', concurso_id=miembro.concurso_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al presentar recusación: {str(e)}', 'danger')
    
    return render_template('tribunal/recusar.html', miembro=miembro, concurso=concurso)

@tribunal.route('/<int:miembro_id>/subir-documento', methods=['POST'])
@login_required
def subir_documento(miembro_id):
    """Upload a document for a tribunal member."""
    miembro = TribunalMiembro.query.get_or_404(miembro_id)
    concurso = Concurso.query.get_or_404(miembro.concurso_id)
    
    try:
        # Get form data
        tipo = request.form.get('tipo')
        file = request.files.get('documento')
        
        if not file:
            flash('No se seleccionó ningún archivo.', 'danger')
            return redirect(url_for('tribunal.index', concurso_id=concurso.id))
        
        if not miembro.drive_folder_id:
            flash('El miembro del tribunal no tiene una carpeta asociada.', 'danger')
            return redirect(url_for('tribunal.index', concurso_id=concurso.id))
        
        # Create filename with proper suffix
        filename = secure_filename(f"{tipo}_{miembro.apellido}_{miembro.nombre}_{concurso.id}.pdf")
        
        # Read file data
        file_data = file.read()
        
        # Upload to Google Drive
        file_id, web_view_link = drive_api.upload_document(
            miembro.drive_folder_id,
            filename,
            file_data
        )
        
        # Create document record
        documento = DocumentoTribunal(
            miembro_id=miembro.id,
            tipo=tipo,
            url=web_view_link
        )
        
        db.session.add(documento)
        db.session.commit()
        
        flash(f'Documento subido exitosamente. <a href="{web_view_link}" target="_blank" class="alert-link">Ver documento</a>', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al subir documento: {str(e)}', 'danger')
    
    return redirect(url_for('tribunal.index', concurso_id=concurso.id))