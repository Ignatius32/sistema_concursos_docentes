from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timezone
from app.models.models import db, Concurso, Departamento, Area, Orientacion, Categoria, HistorialEstado, DocumentoConcurso
from app.integrations.google_drive import GoogleDriveAPI
import json
import os

concursos = Blueprint('concursos', __name__, url_prefix='/concursos')
drive_api = GoogleDriveAPI()

def _format_cargos_text(cant_cargos, tipo):
    """Format the cargo count text with number in words and proper pluralization."""
    numeros_texto = {
        1: "un",
        2: "dos",
        3: "tres",
        4: "cuatro",
        5: "cinco",
        6: "seis",
        7: "siete",
        8: "ocho",
        9: "nueve",
        10: "diez"
    }
    
    numero = numeros_texto.get(cant_cargos, str(cant_cargos))
    cargo_text = "cargo" if cant_cargos == 1 else "cargos"
    tipo_text = "interino" if tipo == "Interino" else "regular"
    tipo_text = tipo_text if cant_cargos == 1 else tipo_text + ("es" if tipo == "Regular" else "s")
    
    return f"{numero} ({cant_cargos}) {cargo_text} {tipo_text}"

# Helper function to generate documents from templates
def generar_documento_desde_template(concurso_id, template_name, doc_tipo, prepare_data_func):
    """
    Generic function to generate a document from a template.
    
    Args:
        concurso_id (int): ID of the concurso
        template_name (str): Name of the template in Google Drive
        doc_tipo (str): Type of document for database record
        prepare_data_func (function): Function that prepares the data for the template
        
    Returns:
        tuple: (success, message, url) - Indicates success/failure, message, and URL if successful
    """
    try:
        concurso = Concurso.query.get_or_404(concurso_id)
        
        if not concurso.borradores_folder_id:
            return False, 'El concurso no tiene una carpeta de borradores asociada.', None
        
        # Get data for template from the specific function
        data, validation_message = prepare_data_func(concurso)
        
        # Check if data preparation succeeded
        if not data:
            return False, validation_message, None
            
        # Generate file name with timestamp
        file_name = f"{doc_tipo.replace('_', ' ').title()}_Concurso_{concurso.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
        
        # Use API to create document from template in borradores folder
        file_id, web_link = drive_api.create_document_from_template(
            template_name,
            data,
            concurso.borradores_folder_id,
            file_name
        )
        
        # Create document record
        documento = DocumentoConcurso(
            concurso=concurso,
            tipo=doc_tipo,
            url=web_link,
            estado='BORRADOR'
        )
        db.session.add(documento)
        
        # Add entry to history
        historial = HistorialEstado(
            concurso=concurso,
            estado="DOCUMENTO_GENERADO",
            observaciones=f"{doc_tipo.replace('_', ' ').title()} generado por {current_user.username}"
        )
        db.session.add(historial)
        db.session.commit()
        
        return True, f'Documento generado exitosamente.', web_link
        
    except Exception as e:
        db.session.rollback()
        return False, f'Error al generar el documento: {str(e)}', None

# Data preparation functions for different templates
def prepare_data_resolucion_llamado_tribunal(concurso):
    """Prepare data for the resolucion llamado tribunal template."""
    # Check if tribunal members are assigned
    tribunal_members = concurso.tribunal.all()
    if not tribunal_members:
        return None, 'No hay miembros del tribunal asignados para este concurso.'
    
    # Get related data
    departamento = Departamento.query.get(concurso.departamento_id)
    
    # Format dates for display
    current_year = datetime.now().year
    
    # Format tribunal members
    titulares = []
    suplentes = []
    
    for miembro in tribunal_members:
        member_info = f"{miembro.apellido}, {miembro.nombre} (DNI: {miembro.dni})"
        
        if miembro.rol == "Presidente":
            # Presidente always goes first in the titulares list
            titulares.insert(0, f"{member_info} - Presidente")
        elif miembro.rol == "Suplente":
            suplentes.append(member_info)
        else:  # Vocal
            titulares.append(member_info)
    
    # Join lists with line breaks for the document
    tribunal_titular_text = "\n".join(titulares)
    tribunal_suplentes_text = "\n".join(suplentes)
    
    # Get expediente number (this is an example, you might need to add this field to your model)
    #expediente = f"{expediente}"  # Replace with actual expediente field
    
    # Ensure we have the categoria_nombre
    categoria_nombre = concurso.categoria_nombre
    if not categoria_nombre:
        # Load roles_categorias.json data if needed
        json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'roles_categorias.json')
        with open(json_path, 'r', encoding='utf-8') as f:
            roles_data = json.load(f)
        
        # Find categoria name by codigo
        for rol in roles_data:
            for categoria in rol['categorias']:
                if categoria['codigo'] == concurso.categoria:
                    categoria_nombre = categoria['nombre']
                    break
            if categoria_nombre:
                break
    
    # Prepare data for template replacements
    data = {
        'cantCargos': _format_cargos_text(concurso.cant_cargos, concurso.tipo),
        'departamento': departamento.nombre,
        'area': concurso.area,
        'orientacion': concurso.orientacion,
        'tipo': concurso.tipo,
        'nombre': categoria_nombre or concurso.categoria,  # Use found name or fallback to codigo
        'codigo': concurso.categoria,
        'tribunal_titular': tribunal_titular_text,
        'tribunal_suplentes': tribunal_suplentes_text,
        'yyyy': str(current_year),
        'expediente': concurso.expediente
    }
    
    return data, None

@concursos.route('/')
@login_required
def index():
    """Display list of all concursos."""
    concursos_list = Concurso.query.order_by(Concurso.creado.desc()).all()
    return render_template('concursos/index.html', concursos=concursos_list)

@concursos.route('/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo():
    """Create a new concurso."""
    if request.method == 'POST':
        try:
            # Extract data from form
            tipo = request.form.get('tipo')
            cerrado_abierto = request.form.get('cerrado_abierto')
            cant_cargos = int(request.form.get('cant_cargos'))
            departamento_id = int(request.form.get('departamento_id'))
            area = request.form.get('area')
            orientacion = request.form.get('orientacion') 
            categoria = request.form.get('categoria')
            dedicacion = request.form.get('dedicacion')
            localizacion = request.form.get('localizacion')
            asignaturas = request.form.get('asignaturas')
            expediente = request.form.get('expediente')
            
            # Get categoria name from roles_categorias.json
            import json
            import os
            
            # Load roles_categorias.json data
            json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'roles_categorias.json')
            with open(json_path, 'r', encoding='utf-8') as f:
                roles_data = json.load(f)
            
            # Find categoria name by codigo
            categoria_nombre = None
            for rol in roles_data:
                for cat in rol['categorias']:
                    if cat['codigo'] == categoria:
                        categoria_nombre = cat['nombre']
                        break
                if categoria_nombre:
                    break
                    
            # Handle cierre_inscripcion (optional now)
            cierre_inscripcion_str = request.form.get('cierre_inscripcion')
            cierre_inscripcion = None
            if cierre_inscripcion_str:
                cierre_inscripcion = datetime.strptime(cierre_inscripcion_str, '%Y-%m-%d').date()
            
            # Handle vencimiento (optional)
            vencimiento_str = request.form.get('vencimiento')
            vencimiento = None
            if vencimiento_str:
                vencimiento = datetime.strptime(vencimiento_str, '%Y-%m-%d').date()
            
            # Create new concurso first to get its ID
            concurso = Concurso(
                tipo=tipo,
                cerrado_abierto=cerrado_abierto,
                cant_cargos=cant_cargos,
                departamento_id=departamento_id,
                area=area,
                orientacion=orientacion,
                categoria=categoria,
                categoria_nombre=categoria_nombre,  # Set the nombre from roles_categorias.json
                dedicacion=dedicacion,
                localizacion=localizacion,
                asignaturas=asignaturas,
                expediente=expediente,
                origen_vacante=request.form.get('origen_vacante'),
                docente_vacante=request.form.get('docente_vacante'),
                cierre_inscripcion=cierre_inscripcion,
                vencimiento=vencimiento,
                estado_actual="CREADO"
            )
            
            db.session.add(concurso)
            db.session.flush()  # This gets us the ID without committing
            
            # Create Google Drive folder using the new API class
            departamento = Departamento.query.get(departamento_id)
            folder_result = drive_api.create_concurso_folder(
                concurso.id,
                departamento.nombre,
                area,
                orientacion,
                categoria,
                dedicacion
            )
            
            # Update concurso with both folder IDs
            concurso.drive_folder_id = folder_result['folderId']
            concurso.borradores_folder_id = folder_result['borradoresFolderId']
            
            # Add initial state to history
            historial = HistorialEstado(
                concurso=concurso,
                estado="CREADO",
                observaciones="Creación inicial del concurso"
            )
            db.session.add(historial)
            
            db.session.commit()
            
            flash('Concurso creado exitosamente.', 'success')
            return redirect(url_for('concursos.ver', concurso_id=concurso.id))
        
        except Exception as e:
            flash(f'Error al crear el concurso: {str(e)}', 'danger')
            db.session.rollback()
    
    # Get data for form dropdowns
    departamentos = Departamento.query.all()
    categorias = Categoria.query.all()
    
    return render_template('concursos/nuevo.html', 
                           departamentos=departamentos,
                           categorias=categorias)

@concursos.route('/<int:concurso_id>')
@login_required
def ver(concurso_id):
    """View details of a specific concurso."""
    concurso = Concurso.query.get_or_404(concurso_id)
    return render_template('concursos/ver.html', concurso=concurso)

@concursos.route('/<int:concurso_id>/generar-resolucion-llamado-tribunal', methods=['GET', 'POST'])
@login_required
def generar_resolucion_llamado_tribunal(concurso_id):
    """Generate a resolution document with tribunal information for a concurso."""
    success, message, url = generar_documento_desde_template(
        concurso_id,
        'resLlamadoTribunalInterino',  # template name
        'RESOLUCION_LLAMADO_TRIBUNAL',  # document type
        prepare_data_resolucion_llamado_tribunal  # function to prepare data
    )
    
    if success:
        flash(f'{message} <a href="{url}" target="_blank" class="alert-link">Abrir documento</a>', 'success')
    else:
        flash(message, 'danger')
        
    return redirect(url_for('concursos.ver', concurso_id=concurso_id))

@concursos.route('/<int:concurso_id>/editar', methods=['GET', 'POST'])
@login_required
def editar(concurso_id):
    """Edit an existing concurso."""
    concurso = Concurso.query.get_or_404(concurso_id)
    
    if request.method == 'POST':
        try:
            # Store old data for comparison
            old_departamento_id = concurso.departamento_id
            old_area = concurso.area
            old_orientacion = concurso.orientacion
            old_categoria = concurso.categoria
            old_dedicacion = concurso.dedicacion

            # Update concurso data from form
            concurso.tipo = request.form.get('tipo')
            concurso.cerrado_abierto = request.form.get('cerrado_abierto')
            concurso.cant_cargos = int(request.form.get('cant_cargos'))
            concurso.departamento_id = int(request.form.get('departamento_id'))
            concurso.area = request.form.get('area')
            concurso.orientacion = request.form.get('orientacion')
            concurso.categoria = request.form.get('categoria')
            concurso.dedicacion = request.form.get('dedicacion')
            concurso.localizacion = request.form.get('localizacion')
            concurso.asignaturas = request.form.get('asignaturas')
            concurso.expediente = request.form.get('expediente')
            concurso.origen_vacante = request.form.get('origen_vacante')
            concurso.docente_vacante = request.form.get('docente_vacante')
            
            # Get categoria name from roles_categorias.json
            import json
            import os
            
            # Load roles_categorias.json data
            json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'roles_categorias.json')
            with open(json_path, 'r', encoding='utf-8') as f:
                roles_data = json.load(f)
            
            # Find categoria name by codigo
            categoria_nombre = None
            for rol in roles_data:
                for cat in rol['categorias']:
                    if cat['codigo'] == concurso.categoria:
                        categoria_nombre = cat['nombre']
                        break
                if categoria_nombre:
                    break
                    
            # Set the categoria_nombre from roles_categorias.json
            concurso.categoria_nombre = categoria_nombre or concurso.categoria
            
            # Handle optional cierre_inscripcion
            cierre_inscripcion_str = request.form.get('cierre_inscripcion')
            if cierre_inscripcion_str:
                concurso.cierre_inscripcion = datetime.strptime(cierre_inscripcion_str, '%Y-%m-%d').date()
            else:
                concurso.cierre_inscripcion = None
            
            # Handle optional vencimiento
            vencimiento_str = request.form.get('vencimiento')
            if vencimiento_str:
                concurso.vencimiento = datetime.strptime(vencimiento_str, '%Y-%m-%d').date()
            else:
                concurso.vencimiento = None
            
            # Update Google Drive folder name if relevant fields changed and folder exists
            if concurso.drive_folder_id and (
                old_departamento_id != concurso.departamento_id or 
                old_area != concurso.area or 
                old_orientacion != concurso.orientacion or 
                old_categoria != concurso.categoria or 
                old_dedicacion != concurso.dedicacion
            ):
                try:
                    # Get the department name for the folder
                    departamento = Departamento.query.get(concurso.departamento_id)
                    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
                    new_folder_name = f"{concurso.id}_{departamento.nombre}_{concurso.area}_{concurso.orientacion}_{concurso.categoria}_{concurso.dedicacion}_{timestamp}"
                    drive_api.update_folder_name(concurso.drive_folder_id, new_folder_name)
                except Exception as e:
                    flash(f'El concurso fue actualizado pero hubo un error al renombrar su carpeta en Drive: {str(e)}', 'warning')
            
            # Add edit entry to history
            historial = HistorialEstado(
                concurso=concurso,
                estado="EDITADO",
                observaciones=f"Concurso editado por {current_user.username}"
            )
            db.session.add(historial)
            
            db.session.commit()
            
            flash('Concurso actualizado exitosamente.', 'success')
            return redirect(url_for('concursos.ver', concurso_id=concurso.id))
            
        except Exception as e:
            flash(f'Error al actualizar el concurso: {str(e)}', 'danger')
            db.session.rollback()
    
    # Get data for form dropdowns
    departamentos = Departamento.query.all()
    categorias = Categoria.query.all()
    
    return render_template('concursos/editar.html', 
                           concurso=concurso,
                           departamentos=departamentos,
                           categorias=categorias)

@concursos.route('/api/areas/<int:departamento_id>')
def get_areas(departamento_id):
    """API endpoint to fetch areas for a given department."""
    departamento = Departamento.query.get_or_404(departamento_id)
    areas = Area.query.filter_by(departamento_id=departamento_id).all()
    return jsonify([{'id': area.id, 'nombre': area.nombre} for area in areas])

@concursos.route('/api/orientaciones/<int:departamento_id>')
def get_orientaciones(departamento_id):
    """API endpoint to fetch orientaciones for a given area."""
    area_nombre = request.args.get('area')
    if not area_nombre:
        return jsonify([])
    
    area = Area.query.filter_by(departamento_id=departamento_id, nombre=area_nombre).first()
    if not area:
        return jsonify([])
        
    orientaciones = Orientacion.query.filter_by(area_id=area.id).all()
    return jsonify([{'id': o.id, 'nombre': o.nombre} for o in orientaciones])

@concursos.route('/<int:concurso_id>/eliminar', methods=['POST'])
@login_required
def eliminar(concurso_id):
    """Delete a concurso and all its related data."""
    concurso = Concurso.query.get_or_404(concurso_id)
    
    try:
        # Delete Google Drive folder if it exists
        if concurso.drive_folder_id:
            try:
                drive_api.delete_folder(concurso.drive_folder_id)
            except Exception as e:
                flash(f'Advertencia: No se pudo eliminar la carpeta de Google Drive: {str(e)}', 'warning')
        
        # Delete all related data
        concurso.tribunal.delete()
        for postulante in concurso.postulantes:
            # Delete postulante's Drive folder if it exists
            if postulante.drive_folder_id:
                try:
                    drive_api.delete_folder(postulante.drive_folder_id)
                except Exception as e:
                    flash(f'Advertencia: No se pudo eliminar la carpeta del postulante {postulante.apellido} {postulante.nombre} en Drive: {str(e)}', 'warning')
            postulante.documentos.delete()
        concurso.postulantes.delete()
        concurso.documentos.delete()
        concurso.historial_estados.delete()
        if concurso.sustanciacion:
            db.session.delete(concurso.sustanciacion)
        concurso.impugnaciones.delete()
        concurso.recusaciones.delete()
        
        # Delete the concurso
        db.session.delete(concurso)
        db.session.commit()
        
        flash('Concurso eliminado exitosamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el concurso: {str(e)}', 'danger')
    
    return redirect(url_for('concursos.index'))

@concursos.route('/<int:concurso_id>/documento/<int:documento_id>/eliminar', methods=['POST'])
@login_required
def eliminar_documento(concurso_id, documento_id):
    """Delete a document from a concurso."""
    concurso = Concurso.query.get_or_404(concurso_id)
    documento = DocumentoConcurso.query.get_or_404(documento_id)
    
    # Verify the document belongs to the concurso
    if documento.concurso_id != concurso_id:
        flash('El documento no pertenece a este concurso.', 'danger')
        return redirect(url_for('concursos.ver', concurso_id=concurso_id))
    
    try:
        # Get file ID from URL
        file_id = documento.url.split('/')[-2]  # Google Drive URLs have the file ID in the second-to-last segment
        
        # Try to delete from Drive
        try:
            drive_api.delete_file(file_id)
        except Exception as e:
            flash(f'Advertencia: No se pudo eliminar el archivo de Google Drive: {str(e)}', 'warning')
        
        # Delete from database
        db.session.delete(documento)
        
        # Add entry to history
        historial = HistorialEstado(
            concurso=concurso,
            estado="DOCUMENTO_ELIMINADO",
            observaciones=f"Documento {documento.tipo} eliminado por {current_user.username}"
        )
        db.session.add(historial)
        
        db.session.commit()
        flash('Documento eliminado exitosamente.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el documento: {str(e)}', 'danger')
    
    return redirect(url_for('concursos.ver', concurso_id=concurso_id))