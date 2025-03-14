from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timezone
from app.models.models import db, Concurso, Departamento, Area, Orientacion, Categoria, HistorialEstado, DocumentoConcurso, Sustanciacion
from app.integrations.google_drive import GoogleDriveAPI
from app.helpers.text_formatting import format_descripcion_cargo
from app.helpers.api_services import get_considerandos_data, get_departamento_heads_data
from app.document_generation.document_generator import generar_documento_desde_template
from app.document_generation.resolucion_templates import prepare_data_resolucion_llamado_tribunal
import json
import os
import requests

concursos = Blueprint('concursos', __name__, url_prefix='/concursos')
drive_api = GoogleDriveAPI()

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
            
            # Update concurso with all folder IDs
            concurso.drive_folder_id = folder_result['folderId']
            concurso.borradores_folder_id = folder_result['borradoresFolderId']
            concurso.postulantes_folder_id = folder_result['postulantesFolderId']
            concurso.documentos_firmados_folder_id = folder_result['documentosFirmadosFolderId']
            
            # Add initial state to history
            historial = HistorialEstado(
                concurso=concurso,
                estado="CREADO",
                observaciones="Creación inicial del concurso"
            )
            db.session.add(historial)
            
            # Create Sustanciacion record if any of the fields are filled
            constitucion_fecha_str = request.form.get('constitucion_fecha')
            constitucion_lugar = request.form.get('constitucion_lugar')
            constitucion_virtual_link = request.form.get('constitucion_virtual_link')
            constitucion_observaciones = request.form.get('constitucion_observaciones')
            
            # Check if any sustanciacion fields are filled
            if (constitucion_fecha_str or constitucion_lugar or 
                constitucion_virtual_link or constitucion_observaciones or
                request.form.get('sorteo_fecha') or request.form.get('sorteo_lugar') or
                request.form.get('sorteo_virtual_link') or request.form.get('sorteo_observaciones') or
                request.form.get('exposicion_fecha') or request.form.get('exposicion_lugar') or
                request.form.get('exposicion_virtual_link') or request.form.get('exposicion_observaciones')):
                
                # Parse datetime fields
                constitucion_fecha = datetime.strptime(constitucion_fecha_str, '%Y-%m-%dT%H:%M') if constitucion_fecha_str else None
                sorteo_fecha_str = request.form.get('sorteo_fecha')
                sorteo_fecha = datetime.strptime(sorteo_fecha_str, '%Y-%m-%dT%H:%M') if sorteo_fecha_str else None
                exposicion_fecha_str = request.form.get('exposicion_fecha')
                exposicion_fecha = datetime.strptime(exposicion_fecha_str, '%Y-%m-%dT%H:%M') if exposicion_fecha_str else None
                
                # Create Sustanciacion record
                sustanciacion = Sustanciacion(
                    concurso=concurso,
                    constitucion_fecha=constitucion_fecha,
                    constitucion_lugar=constitucion_lugar,
                    constitucion_virtual_link=constitucion_virtual_link,
                    constitucion_observaciones=constitucion_observaciones,
                    sorteo_fecha=sorteo_fecha,
                    sorteo_lugar=request.form.get('sorteo_lugar'),
                    sorteo_virtual_link=request.form.get('sorteo_virtual_link'),
                    sorteo_observaciones=request.form.get('sorteo_observaciones'),
                    exposicion_fecha=exposicion_fecha,
                    exposicion_lugar=request.form.get('exposicion_lugar'),
                    exposicion_virtual_link=request.form.get('exposicion_virtual_link'),
                    exposicion_observaciones=request.form.get('exposicion_observaciones')
                )
                db.session.add(sustanciacion)

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

@concursos.route('/<int:concurso_id>/generar-resolucion-llamado-tribunal', methods=['GET'])
@login_required
def generar_resolucion_llamado_tribunal(concurso_id):
    """Handle the request to generate a resolution document with tribunal information."""
    concurso = Concurso.query.get_or_404(concurso_id)
    # Redirect to the considerandos builder
    return redirect(url_for('concursos.considerandos_builder', 
                           concurso_id=concurso_id, 
                           document_type='RESOLUCION_LLAMADO_TRIBUNAL', 
                           template_name='resLlamadoTribunalInterino'))

@concursos.route('/<int:concurso_id>/considerandos-builder', methods=['GET', 'POST'])
@login_required
def considerandos_builder(concurso_id):
    """
    Handle the considerandos builder interface.
    
    This route displays a form to select considerandos options and then generates
    the document with those options.
    """
    concurso = Concurso.query.get_or_404(concurso_id)
    
    # Get the departamento object
    departamento = Departamento.query.get(concurso.departamento_id) if concurso.departamento_id else None
    
    # Get document type and template name from query parameters
    document_type = request.args.get('document_type')
    template_name = request.args.get('template_name')
    
    # Generate cargo description - FIX: Correct order of parameters
    descripcion_cargo = format_descripcion_cargo(
        concurso.cant_cargos,
        concurso.tipo,
        concurso.categoria,
        concurso.categoria_nombre or concurso.categoria,
        concurso.dedicacion
    )
    
    if not document_type or not template_name:
        flash('Tipo de documento o plantilla no especificados', 'danger')
        return redirect(url_for('concursos.ver', concurso_id=concurso_id))
    
    # Fetch considerandos options from the API
    considerandos_data = get_considerandos_data(document_type)
    
    # Fetch departamento heads data
    departamento_heads = get_departamento_heads_data()
    
    if considerandos_data is None:
        error_message = 'No se pudieron cargar los considerandos. Por favor, inténtelo de nuevo más tarde.'
        return render_template(
            'concursos/considerandos_builder.html', 
            concurso=concurso,
            departamento=departamento,
            document_type=document_type,
            considerandos_data={},
            departamento_heads=departamento_heads,
            descripcion_cargo=descripcion_cargo,
            error_message=error_message
        )
    
    if request.method == 'POST':
        # Save committee and council information
        try:
            # Process committee date
            fecha_comision_str = request.form.get('fecha_comision_academica')
            if fecha_comision_str:
                concurso.fecha_comision_academica = datetime.strptime(fecha_comision_str, '%Y-%m-%d').date()
            else:
                concurso.fecha_comision_academica = None
            
            # Process council date
            fecha_consejo_str = request.form.get('fecha_consejo_directivo')
            if fecha_consejo_str:
                concurso.fecha_consejo_directivo = datetime.strptime(fecha_consejo_str, '%Y-%m-%d').date()
            else:
                concurso.fecha_consejo_directivo = None
            
            # Process text fields
            concurso.despacho_comision_academica = request.form.get('despacho_comision_academica', '')
            concurso.sesion_consejo_directivo = request.form.get('sesion_consejo_directivo', '')
            concurso.despacho_consejo_directivo = request.form.get('despacho_consejo_directivo', '')
            
            # Save to database
            db.session.commit()
        except Exception as e:
            flash(f'Error al guardar información de comisión y consejo: {str(e)}', 'warning')
            db.session.rollback()
        
        # Collect selected considerandos in the specified order
        selected_considerandos = []
        
        # Process considerandos order from the hidden input
        considerandos_order_json = request.form.get('considerandos_order', '[]')
        try:
            considerandos_order = json.loads(considerandos_order_json)
            
            # Extract considerando values in the specified order
            for item in considerandos_order:
                value = item.get('value', '')
                if value and value.strip():
                    selected_considerandos.append(value.strip())
        except json.JSONDecodeError:
            # Fallback to the old way if the JSON is invalid
            # This ensures backward compatibility
            for considerando_key in considerandos_data.keys():
                selected_value = request.form.get(considerando_key)
                if selected_value:
                    selected_considerandos.append(selected_value)
            
            # Add custom considerandos if provided
            custom_considerandos = request.form.getlist('custom_considerandos[]')
            for custom_text in custom_considerandos:
                if custom_text and custom_text.strip():
                    selected_considerandos.append(custom_text.strip())
        
        # Compile considerandos text with single line breaks
        considerandos_text = "\n".join(selected_considerandos)
        
        # Proceed with document generation based on document type
        if document_type == 'RESOLUCION_LLAMADO_TRIBUNAL':
            success, message, url = generar_documento_desde_template(
                concurso_id,
                template_name,
                document_type,
                prepare_data_resolucion_llamado_tribunal,
                considerandos_text
            )
        else:
            flash('Tipo de documento no soportado', 'danger')
            return redirect(url_for('concursos.ver', concurso_id=concurso_id))
        
        if success:
            flash(f'{message} <a href="{url}" target="_blank" class="alert-link">Abrir documento</a>', 'success')
        else:
            flash(message, 'danger')
            
        return redirect(url_for('concursos.ver', concurso_id=concurso_id))
    
    # Display the considerandos form
    return render_template(
        'concursos/considerandos_builder.html',
        concurso=concurso,
        departamento=departamento,
        document_type=document_type,
        considerandos_data=considerandos_data,
        departamento_heads=departamento_heads,
        descripcion_cargo=descripcion_cargo
    )

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
            
            # Update or create Sustanciacion record
            constitucion_fecha_str = request.form.get('constitucion_fecha')
            sorteo_fecha_str = request.form.get('sorteo_fecha')
            exposicion_fecha_str = request.form.get('exposicion_fecha')

            if not concurso.sustanciacion:
                if (constitucion_fecha_str or request.form.get('constitucion_lugar') or 
                    request.form.get('constitucion_virtual_link') or request.form.get('constitucion_observaciones') or
                    sorteo_fecha_str or request.form.get('sorteo_lugar') or
                    request.form.get('sorteo_virtual_link') or request.form.get('sorteo_observaciones') or
                    exposicion_fecha_str or request.form.get('exposicion_lugar') or
                    request.form.get('exposicion_virtual_link') or request.form.get('exposicion_observaciones')):
                    
                    concurso.sustanciacion = Sustanciacion(concurso=concurso)
            
            if concurso.sustanciacion:
                # Update dates if provided
                if constitucion_fecha_str:
                    concurso.sustanciacion.constitucion_fecha = datetime.strptime(constitucion_fecha_str, '%Y-%m-%dT%H:%M')
                if sorteo_fecha_str:
                    concurso.sustanciacion.sorteo_fecha = datetime.strptime(sorteo_fecha_str, '%Y-%m-%dT%H:%M')
                if exposicion_fecha_str:
                    concurso.sustanciacion.exposicion_fecha = datetime.strptime(exposicion_fecha_str, '%Y-%m-%dT%H:%M')
                
                # Update other fields
                concurso.sustanciacion.constitucion_lugar = request.form.get('constitucion_lugar')
                concurso.sustanciacion.constitucion_virtual_link = request.form.get('constitucion_virtual_link')
                concurso.sustanciacion.constitucion_observaciones = request.form.get('constitucion_observaciones')
                concurso.sustanciacion.sorteo_lugar = request.form.get('sorteo_lugar')
                concurso.sustanciacion.sorteo_virtual_link = request.form.get('sorteo_virtual_link')
                concurso.sustanciacion.sorteo_observaciones = request.form.get('sorteo_observaciones')
                concurso.sustanciacion.exposicion_lugar = request.form.get('exposicion_lugar')
                concurso.sustanciacion.exposicion_virtual_link = request.form.get('exposicion_virtual_link')
                concurso.sustanciacion.exposicion_observaciones = request.form.get('exposicion_observaciones')
            
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