from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify
from app.utils.keycloak_auth import keycloak_login_required, admin_required
from app.models.models import db, Concurso, Postulante, DocumentoPostulante, Impugnacion, Categoria
from app.integrations.google_drive import GoogleDriveAPI
import os
import json
from datetime import datetime
import uuid
from werkzeug.utils import secure_filename
from PIL import Image
import io
from PyPDF2 import PdfMerger, PdfReader, PdfWriter
import tempfile

postulantes = Blueprint('postulantes', __name__, url_prefix='/postulantes')
drive_api = GoogleDriveAPI()

def convert_to_pdf(file_stream, original_filename):
    """Convert a file to PDF if it's an image, or return the PDF as-is."""
    content_type = file_stream.content_type
    file_data = file_stream.read()
    
    if (content_type.startswith('image/')):
        # Convert image to PDF
        image = Image.open(io.BytesIO(file_data))
        if image.mode == 'RGBA':
            image = image.convert('RGB')
        pdf_bytes = io.BytesIO()
        image.save(pdf_bytes, format='PDF')
        return pdf_bytes.getvalue()
    elif content_type == 'application/pdf':
        return file_data
    else:
        raise ValueError(f"Unsupported file type: {content_type}")

def generate_document_filename(tipo, postulante, concurso):
    """Generate a standardized filename for the document."""
    apellido = secure_filename(postulante.apellido.lower())
    nombre = secure_filename(postulante.nombre.lower())
    return f"{tipo}_{apellido}_{nombre}_{postulante.dni}_{concurso.categoria}_{concurso.dedicacion}_{concurso.id}.pdf"

@postulantes.route('/concurso/<int:concurso_id>')
@keycloak_login_required
@admin_required
def index(concurso_id):
    """Display applicants for a specific concurso."""
    concurso = Concurso.query.get_or_404(concurso_id)
    postulantes_list = Postulante.query.filter_by(concurso_id=concurso_id).all()
    return render_template('postulantes/index.html', concurso=concurso, postulantes=postulantes_list)

@postulantes.route('/concurso/<int:concurso_id>/agregar', methods=['GET', 'POST'])
@keycloak_login_required
@admin_required
def agregar(concurso_id):
    """Add a new applicant to a concurso."""
    concurso = Concurso.query.get_or_404(concurso_id)
    
    if request.method == 'POST':
        try:            # Extract form data
            dni = request.form.get('dni')
            nombre = request.form.get('nombre')
            apellido = request.form.get('apellido')
            correo = request.form.get('correo')
            telefono = request.form.get('telefono')
            domicilio = request.form.get('domicilio')
            
            # Check if postulante already exists in this concurso
            existing = Postulante.query.filter_by(concurso_id=concurso_id, dni=dni).first()
            if existing:
                flash('Ya existe un postulante con ese DNI en este concurso.', 'warning')
                return redirect(url_for('postulantes.agregar', concurso_id=concurso_id))
              # Create new postulante
            postulante = Postulante(
                concurso_id=concurso_id,
                dni=dni,
                nombre=nombre,
                apellido=apellido,
                correo=correo,
                telefono=telefono,
                domicilio=domicilio
                # estado will be 'activo' by default
            )
            
            db.session.add(postulante)
            db.session.flush()  # To get the postulante ID
            
            # Create Google Drive folder for the postulante
            if concurso.postulantes_folder_id:
                try:
                    folder_id = drive_api.create_postulante_folder(
                        concurso.postulantes_folder_id,
                        postulante.dni,
                        postulante.apellido,
                        postulante.nombre,
                        concurso.categoria,
                        concurso.dedicacion
                    )
                    postulante.drive_folder_id = folder_id
                except Exception as e:
                    print(f"Error creating Drive folder: {e}")
                    flash('El postulante fue creado pero hubo un error al crear su carpeta en Drive.', 'warning')
            
            db.session.commit()
            
            flash('Postulante agregado exitosamente.', 'success')
            return redirect(url_for('postulantes.ver', postulante_id=postulante.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al agregar postulante: {str(e)}', 'danger')
    
    return render_template('postulantes/agregar.html', concurso=concurso)

@postulantes.route('/<int:postulante_id>')
@keycloak_login_required
@admin_required
def ver(postulante_id):
    """View details of a specific applicant."""
    postulante = Postulante.query.get_or_404(postulante_id)
    concurso = Concurso.query.get_or_404(postulante.concurso_id)
    documentos = DocumentoPostulante.query.filter_by(postulante_id=postulante_id).all()
    
    # Get the documentation requirements for this concurso based on the categoria and dedicacion
    # Load roles_categorias.json to determine required documents
    try:
        with open(os.path.join(current_app.root_path, '../roles_categorias.json'), 'r', encoding='utf-8') as f:
            categorias_data = json.load(f)
            
        required_docs = []
        for rol in categorias_data:
            for cat in rol['categorias']:
                if cat['codigo'] == concurso.categoria:
                    # Add base documents
                    required_docs.extend(cat['documentacionRequerida']['base'])
                    
                    # Add documents by dedicacion if available
                    if 'porDedicacion' in cat['documentacionRequerida'] and concurso.dedicacion in cat['documentacionRequerida']['porDedicacion']:
                        required_docs.extend(cat['documentacionRequerida']['porDedicacion'][concurso.dedicacion])
                    break
    except Exception as e:
        print(f"Error loading required documents: {e}")
        required_docs = []
    
    # Create a dictionary to check which documents have been uploaded
    uploaded_docs = {doc.tipo: doc for doc in documentos}
    
    return render_template(
        'postulantes/ver.html', 
        postulante=postulante, 
        concurso=concurso, 
        documentos=documentos,
        required_docs=required_docs,
        uploaded_docs=uploaded_docs
    )

@postulantes.route('/<int:postulante_id>/editar', methods=['GET', 'POST'])
@keycloak_login_required
@admin_required
def editar(postulante_id):
    """Edit an existing applicant."""
    postulante = Postulante.query.get_or_404(postulante_id)
    concurso = Concurso.query.get_or_404(postulante.concurso_id)
    
    if request.method == 'POST':
        try:
            # Store old data for comparison
            old_apellido = postulante.apellido
            old_nombre = postulante.nombre
            old_dni = postulante.dni            # Update postulante data from form
            postulante.dni = request.form.get('dni')
            postulante.nombre = request.form.get('nombre')
            postulante.apellido = request.form.get('apellido')
            postulante.correo = request.form.get('correo')
            postulante.telefono = request.form.get('telefono')
            postulante.domicilio = request.form.get('domicilio')
            postulante.estado = request.form.get('estado', 'activo') # Default to 'activo' if not provided
            
            # Update Google Drive folder name if relevant fields changed and folder exists
            if postulante.drive_folder_id and (
                old_apellido != postulante.apellido or 
                old_nombre != postulante.nombre or 
                old_dni != postulante.dni
            ):
                try:
                    new_folder_name = f"{postulante.apellido}_{postulante.nombre}_{postulante.dni}_{concurso.categoria}_{concurso.dedicacion}"
                    drive_api.update_folder_name(postulante.drive_folder_id, new_folder_name)
                except Exception as e:
                    flash(f'El postulante fue actualizado pero hubo un error al renombrar su carpeta en Drive: {str(e)}', 'warning')
            
            db.session.commit()
            flash('Postulante actualizado exitosamente.', 'success')
            return redirect(url_for('postulantes.ver', postulante_id=postulante.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar postulante: {str(e)}', 'danger')
    
    return render_template('postulantes/editar.html', postulante=postulante, concurso=concurso)

@postulantes.route('/<int:postulante_id>/eliminar', methods=['POST'])
@keycloak_login_required
@admin_required
def eliminar(postulante_id):
    """Delete an applicant."""
    postulante = Postulante.query.get_or_404(postulante_id)
    concurso_id = postulante.concurso_id
    
    try:
        # Delete Google Drive folder if it exists
        if postulante.drive_folder_id:
            try:
                drive_api.delete_folder(postulante.drive_folder_id)
            except Exception as e:
                flash(f'Advertencia: No se pudo eliminar la carpeta de Google Drive: {str(e)}', 'warning')
        
        # First delete all documents associated with this applicant
        DocumentoPostulante.query.filter_by(postulante_id=postulante_id).delete()
        
        # Then delete the applicant
        db.session.delete(postulante)
        db.session.commit()
        
        flash('Postulante y sus documentos eliminados exitosamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar postulante: {str(e)}', 'danger')
    
    return redirect(url_for('postulantes.index', concurso_id=concurso_id))

@postulantes.route('/<int:postulante_id>/documentos/agregar', methods=['GET', 'POST'])
@keycloak_login_required
@admin_required
def agregar_documento(postulante_id):
    """Add a document for an applicant."""
    postulante = Postulante.query.get_or_404(postulante_id)
    concurso = Concurso.query.get_or_404(postulante.concurso_id)
    
    if request.method == 'POST':
        try:
            tipo = request.form.get('tipo')
            file = request.files.get('documento')
            
            if not file:
                flash('No se seleccionó ningún archivo.', 'danger')
                return redirect(request.url)
            
            # Convert to PDF if needed and get the file data
            try:
                pdf_data = convert_to_pdf(file, file.filename)
            except Exception as e:
                flash(f'Error al procesar el archivo: {str(e)}', 'danger')
                return redirect(request.url)
            
            # Generate standardized filename
            filename = generate_document_filename(tipo, postulante, concurso)
            
            # Check if document already exists
            existing = DocumentoPostulante.query.filter_by(
                postulante_id=postulante_id,
                tipo=tipo
            ).first()
            
            try:
                if existing:
                    # Get the existing file ID from the URL
                    existing_file_id = existing.url.split('/')[-2]
                    
                    # Overwrite existing file
                    file_id, web_view_link = drive_api.overwrite_file(
                        existing_file_id,
                        pdf_data
                    )
                    
                    # Update existing document
                    existing.url = web_view_link
                    existing.creado = datetime.utcnow()
                    flash(f'Documento "{tipo}" actualizado exitosamente.', 'success')
                else:
                    # Upload new file
                    file_id, web_view_link = drive_api.upload_document(
                        postulante.drive_folder_id,
                        filename,
                        pdf_data
                    )
                    
                    # Create new document
                    documento = DocumentoPostulante(
                        postulante_id=postulante_id,
                        tipo=tipo,
                        url=web_view_link
                    )
                    db.session.add(documento)
                    flash(f'Documento "{tipo}" agregado exitosamente.', 'success')
                
                db.session.commit()
                return redirect(url_for('postulantes.ver', postulante_id=postulante_id))
                
            except Exception as e:
                flash(f'Error al subir el documento: {str(e)}', 'danger')
                return redirect(request.url)
            
        except Exception as e:
            flash(f'Error al agregar documento: {str(e)}', 'danger')
    
    # Get the documentation requirements for this concurso
    try:
        with open(os.path.join(current_app.root_path, '../roles_categorias.json'), 'r', encoding='utf-8') as f:
            categorias_data = json.load(f)
            
        required_docs = []
        for rol in categorias_data:
            for cat in rol['categorias']:
                if cat['codigo'] == concurso.categoria:
                    # Add base documents
                    required_docs.extend(cat['documentacionRequerida']['base'])
                    
                    # Add documents by dedicacion if available
                    if 'porDedicacion' in cat['documentacionRequerida'] and concurso.dedicacion in cat['documentacionRequerida']['porDedicacion']:
                        required_docs.extend(cat['documentacionRequerida']['porDedicacion'][concurso.dedicacion])
                    break
    except Exception as e:
        print(f"Error loading required documents: {e}")
        required_docs = []
    
    # Get all currently uploaded document types
    uploaded_doc_types = [doc.tipo for doc in DocumentoPostulante.query.filter_by(postulante_id=postulante_id).all()]
    
    # Filter out documents that are already uploaded
    available_docs = [doc for doc in required_docs if doc not in uploaded_doc_types]
    
    return render_template(
        'postulantes/agregar_documento.html',
        postulante=postulante,
        concurso=concurso,
        available_docs=available_docs
    )

@postulantes.route('/documentos/<int:documento_id>/eliminar', methods=['POST'])
@keycloak_login_required
@admin_required
def eliminar_documento(documento_id):
    """Delete a document."""
    documento = DocumentoPostulante.query.get_or_404(documento_id)
    postulante = Postulante.query.get_or_404(documento.postulante_id)
    postulante_id = documento.postulante_id
    
    try:
        # Extract file ID from the Google Drive URL
        file_id = documento.url.split('/')[-2]  # Google Drive URLs end in /view
        
        # Delete file from Google Drive
        try:
            drive_api.delete_file(file_id)
        except Exception as e:
            flash(f'Advertencia: No se pudo eliminar el archivo de Google Drive: {str(e)}', 'warning')
        
        # Delete document record from database
        db.session.delete(documento)
        db.session.commit()
        flash('Documento eliminado exitosamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar documento: {str(e)}', 'danger')
    
    return redirect(url_for('postulantes.ver', postulante_id=postulante_id))

@postulantes.route('/<int:postulante_id>/impugnar', methods=['GET', 'POST'])
@keycloak_login_required
@admin_required
def impugnar(postulante_id):
    """Submit an impugnation against an applicant."""
    postulante = Postulante.query.get_or_404(postulante_id)
    concurso = Concurso.query.get_or_404(postulante.concurso_id)
    
    if request.method == 'POST':
        try:
            # Create impugnation
            impugnacion = Impugnacion(
                concurso_id=postulante.concurso_id,
                postulante_id=postulante_id,
                motivo=request.form.get('motivo'),
                estado='PRESENTADA'
            )
            
            db.session.add(impugnacion)
            db.session.commit()
            
            flash('Impugnación presentada correctamente.', 'success')
            return redirect(url_for('postulantes.ver', postulante_id=postulante_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al presentar impugnación: {str(e)}', 'danger')
