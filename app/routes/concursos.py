from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timezone
from app.models.models import db, Concurso, Departamento, Area, Orientacion, Categoria, HistorialEstado, DocumentoConcurso, Sustanciacion
from app.integrations.google_drive import GoogleDriveAPI
from app.helpers.text_formatting import format_descripcion_cargo
from app.helpers.api_services import get_considerandos_data, get_departamento_heads_data
from app.document_generation.document_generator import generar_documento_desde_template
import json
import os
import requests
import io
from werkzeug.utils import secure_filename

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
            
            # Get resolution numbers based on tipo
            nro_res_llamado_interino = None
            nro_res_llamado_regular = None
            nro_res_tribunal_regular = None
            
            if tipo == 'Interino':
                nro_res_llamado_interino = request.form.get('nro_res_llamado_interino')
            elif tipo == 'Regular':
                nro_res_llamado_regular = request.form.get('nro_res_llamado_regular')
                nro_res_tribunal_regular = request.form.get('nro_res_tribunal_regular')
            
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
                nro_res_llamado_interino=nro_res_llamado_interino,
                nro_res_llamado_regular=nro_res_llamado_regular,
                nro_res_tribunal_regular=nro_res_tribunal_regular,
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
                categoria_vacante=request.form.get('categoria_vacante'),
                dedicacion_vacante=request.form.get('dedicacion_vacante'), 
                id_designacion_mocovi=request.form.get('id_designacion_mocovi'),
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
            concurso.tribunal_folder_id = folder_result['tribunalFolderId']
            
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
                request.form.get('temas_exposicion') or
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
                    temas_exposicion=request.form.get('temas_exposicion'),
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
    
    # Get available document types based on concurso type
    available_documents = []
    
    # Define all possible document types and their display names
    all_document_types = [
        {
            'id': 'RESOLUCION_LLAMADO_TRIBUNAL',
            'name': 'Resolución Llamado y Tribunal',
            'url_generator': lambda c_id: url_for('concursos.generar_resolucion_llamado_tribunal', concurso_id=c_id)
        },
        {
            'id': 'RESOLUCION_LLAMADO_REGULAR',
            'name': 'Resolución Llamado Regular', 
            'url_generator': lambda c_id: url_for('concursos.generar_resolucion_llamado_regular', concurso_id=c_id)
        },
        {
            'id': 'RESOLUCION_TRIBUNAL_REGULAR',
            'name': 'Resolución Tribunal Regular',
            'url_generator': lambda c_id: url_for('concursos.generar_resolucion_tribunal_regular', concurso_id=c_id)
        },
        {
            'id': 'ACTA_CONSTITUCION_TRIBUNAL_REGULAR',
            'name': 'Crear Borrador Acta Constitución de Tribunal Regular',
            'url_generator': lambda c_id: url_for('concursos.generar_acta_constitucion_tribunal_regular', concurso_id=c_id)
        }
    ]
    
    # Check each document type's visibility
    for doc_type in all_document_types:
        doc_data = get_considerandos_data(doc_type['id'], concurso.tipo)
        if doc_data:
            available_documents.append({
                'id': doc_type['id'],
                'name': doc_type['name'],
                'url': doc_type['url_generator'](concurso_id)
            })
    
    return render_template('concursos/ver.html', 
                          concurso=concurso,
                          available_documents=available_documents)

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

@concursos.route('/<int:concurso_id>/generar-resolucion-llamado-regular', methods=['GET'])
@login_required
def generar_resolucion_llamado_regular(concurso_id):
    """Handle the request to generate a regular resolution document."""
    concurso = Concurso.query.get_or_404(concurso_id)
    # Redirect to the considerandos builder
    return redirect(url_for('concursos.considerandos_builder', 
                           concurso_id=concurso_id, 
                           document_type='RESOLUCION_LLAMADO_REGULAR', 
                           template_name='resLlamadoRegular'))

@concursos.route('/<int:concurso_id>/generar-resolucion-tribunal-regular', methods=['GET'])
@login_required
def generar_resolucion_tribunal_regular(concurso_id):
    """Handle the request to generate a regular tribunal resolution document."""
    concurso = Concurso.query.get_or_404(concurso_id)
    # Redirect to the considerandos builder
    return redirect(url_for('concursos.considerandos_builder', 
                           concurso_id=concurso_id, 
                           document_type='RESOLUCION_TRIBUNAL_REGULAR', 
                           template_name='resTribunalRegular'))

@concursos.route('/<int:concurso_id>/generar-acta-constitucion-tribunal-regular', methods=['GET'])
@login_required
def generar_acta_constitucion_tribunal_regular(concurso_id):
    """Handle the request to generate a regular tribunal constitution document."""
    concurso = Concurso.query.get_or_404(concurso_id)

    # Check document visibility and uniqueness from API
    doc_data = get_considerandos_data('ACTA_CONSTITUCION_TRIBUNAL_REGULAR', concurso.tipo)
    if not doc_data:
        flash('Este documento no está disponible para este tipo de concurso.', 'warning')
        return redirect(url_for('concursos.ver', concurso_id=concurso_id))

    # Check if unique document already exists
    if doc_data.get('unique', 0) == 1:
        existing_document = DocumentoConcurso.query.filter_by(
            concurso_id=concurso_id,
            tipo='ACTA_CONSTITUCION_TRIBUNAL_REGULAR'
        ).first()
        if existing_document:
            flash('Ya existe un acta de constitución para este concurso. Por favor, elimine la existente antes de generar una nueva.', 'warning')
            return redirect(url_for('concursos.ver', concurso_id=concurso_id))

    # Generate the document directly using the consolidated function
    success, message, url = generar_documento_desde_template(
        concurso_id,
        'actaConstitucionTribunalRegular',
        'ACTA_CONSTITUCION_TRIBUNAL_REGULAR'
    )

    if success:
        flash(f'{message} <a href="{url}" target="_blank" class="alert-link">Abrir documento</a>', 'success')
    else:
        flash(message, 'danger')

    return redirect(url_for('concursos.ver', concurso_id=concurso_id))

@concursos.route('/<int:concurso_id>/considerandos-builder', methods=['GET', 'POST'])
@login_required
def considerandos_builder(concurso_id):
    """
    Handle the considerandos builder interface.
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
    
    # Fetch considerandos options from the API, passing the concurso type for visibility filtering
    considerandos_data = get_considerandos_data(document_type, concurso.tipo)
    
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
    
    # Check if document is unique and already exists for this concurso
    is_unique = considerandos_data.get('unique', 0) == 1
    if is_unique:
        existing_document = DocumentoConcurso.query.filter_by(
            concurso_id=concurso_id, 
            tipo=document_type
        ).first()
        
        if existing_document:
            flash(f'Ya existe un documento de tipo {document_type} para este concurso. Por favor, elimine el existente antes de generar uno nuevo.', 'warning')
            return redirect(url_for('concursos.ver', concurso_id=concurso_id))
    
    # Extract just the considerandos part to use in the template
    considerandos_options = considerandos_data.get('considerandos', {})
    
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
            for considerando_key in considerandos_options.keys():
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
        
        # Proceed with document generation
        # Using the new simplified document generator that doesn't need a separate data preparation function
        success, message, url = generar_documento_desde_template(
            concurso_id,
            template_name,
            document_type,
            None,  # Using the default prepare_data_for_document function now
            considerandos_text
        )
        
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
        considerandos_data=considerandos_options,
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
            # Extract data from form
            tipo = request.form.get('tipo')
            
            # Get resolution numbers based on tipo
            nro_res_llamado_interino = None
            nro_res_llamado_regular = None
            nro_res_tribunal_regular = None
            
            if tipo == 'Interino':
                nro_res_llamado_interino = request.form.get('nro_res_llamado_interino')
            elif tipo == 'Regular':
                nro_res_llamado_regular = request.form.get('nro_res_llamado_regular')
                nro_res_tribunal_regular = request.form.get('nro_res_tribunal_regular')
            
            # Update concurso
            concurso.tipo = tipo
            concurso.nro_res_llamado_interino = nro_res_llamado_interino
            concurso.nro_res_llamado_regular = nro_res_llamado_regular
            concurso.nro_res_tribunal_regular = nro_res_tribunal_regular
            concurso.cerrado_abierto = request.form.get('cerrado_abierto')
            concurso.cant_cargos = int(request.form.get('cant_cargos'))
            concurso.departamento_id = int(request.form.get('departamento_id'))
            concurso.area = request.form.get('area')
            concurso.orientacion = request.form.get('orientacion')
            concurso.categoria = request.form.get('categoria')
            concurso.categoria_nombre = request.form.get('categoria_nombre')
            concurso.dedicacion = request.form.get('dedicacion')
            concurso.localizacion = request.form.get('localizacion')
            concurso.asignaturas = request.form.get('asignaturas')
            concurso.expediente = request.form.get('expediente')
            
            # Update vacancy data
            concurso.origen_vacante = request.form.get('origen_vacante')
            concurso.docente_vacante = request.form.get('docente_vacante')
            concurso.categoria_vacante = request.form.get('categoria_vacante')
            concurso.dedicacion_vacante = request.form.get('dedicacion_vacante')
            concurso.id_designacion_mocovi = request.form.get('id_designacion_mocovi')

            # Handle cierre_inscripcion
            cierre_inscripcion_str = request.form.get('cierre_inscripcion')
            if cierre_inscripcion_str:
                concurso.cierre_inscripcion = datetime.strptime(cierre_inscripcion_str, '%Y-%m-%d').date()
            else:
                concurso.cierre_inscripcion = None

            # Handle vencimiento
            vencimiento_str = request.form.get('vencimiento')
            if vencimiento_str:
                concurso.vencimiento = datetime.strptime(vencimiento_str, '%Y-%m-%d').date()
            else:
                concurso.vencimiento = None
            
            # Update sustanciacion
            constitucion_fecha_str = request.form.get('constitucion_fecha')
            sorteo_fecha_str = request.form.get('sorteo_fecha')
            exposicion_fecha_str = request.form.get('exposicion_fecha')
            
            # Parse datetime fields
            constitucion_fecha = datetime.strptime(constitucion_fecha_str, '%Y-%m-%dT%H:%M') if constitucion_fecha_str else None
            sorteo_fecha = datetime.strptime(sorteo_fecha_str, '%Y-%m-%dT%H:%M') if sorteo_fecha_str else None
            exposicion_fecha = datetime.strptime(exposicion_fecha_str, '%Y-%m-%dT%H:%M') if exposicion_fecha_str else None
            
            # Create or update sustanciacion
            if not concurso.sustanciacion:
                concurso.sustanciacion = Sustanciacion()
            
            concurso.sustanciacion.constitucion_fecha = constitucion_fecha
            concurso.sustanciacion.constitucion_lugar = request.form.get('constitucion_lugar')
            concurso.sustanciacion.constitucion_virtual_link = request.form.get('constitucion_virtual_link')
            concurso.sustanciacion.constitucion_observaciones = request.form.get('constitucion_observaciones')
            concurso.sustanciacion.sorteo_fecha = sorteo_fecha
            concurso.sustanciacion.sorteo_lugar = request.form.get('sorteo_lugar')
            concurso.sustanciacion.sorteo_virtual_link = request.form.get('sorteo_virtual_link')
            concurso.sustanciacion.sorteo_observaciones = request.form.get('sorteo_observaciones')
            concurso.sustanciacion.temas_exposicion = request.form.get('temas_exposicion')
            concurso.sustanciacion.exposicion_fecha = exposicion_fecha
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
            drive_api.delete_folder(concurso.drive_folder_id)
        
        # Delete all related data
        concurso.tribunal.delete()
        for postulante in concurso.postulantes:
            if postulante.drive_folder_id:
                drive_api.delete_folder(postulante.drive_folder_id)
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

@concursos.route('/<int:concurso_id>/documento/<int:documento_id>/subir-firmado', methods=['POST'])
@login_required
def subir_documento_firmado(concurso_id, documento_id):
    """Upload a signed version of a document."""
    concurso = Concurso.query.get_or_404(concurso_id)
    documento = DocumentoConcurso.query.get_or_404(documento_id)
    
    # Verify the document belongs to the concurso
    if documento.concurso_id != concurso_id:
        flash('El documento no pertenece a este concurso.', 'danger')
        return redirect(url_for('concursos.ver', concurso_id=concurso_id))
    
    if not concurso.documentos_firmados_folder_id:
        flash('El concurso no tiene una carpeta de documentos firmados asociada.', 'danger')
        return redirect(url_for('concursos.ver', concurso_id=concurso_id))
    
    try:
        file = request.files.get('documento_firmado')
        
        if not file:
            flash('No se seleccionó ningún archivo.', 'danger')
            return redirect(url_for('concursos.ver', concurso_id=concurso_id))
        
        # Create the filename with _firmado suffix
        original_filename = documento.tipo.lower().replace('_', ' ') + f"_concurso_{concurso.id}"
        new_filename = f"{original_filename}_firmado.pdf"
        
        # Upload to documentos_firmados folder
        file_data = file.read()
        file_id, web_view_link = drive_api.upload_document(
            concurso.documentos_firmados_folder_id,
            new_filename,
            file_data
        )
        
        # Update document record for the signed version
        documento.file_id = file_id  # Store the file ID of the signed version
        documento.url = web_view_link
        documento.estado = 'FIRMADO'
        
        # Add entry to history
        historial = HistorialEstado(
            concurso=concurso,
            estado="DOCUMENTO_FIRMADO",
            observaciones=f"Documento firmado {documento.tipo} subido por {current_user.username}"
        )
        db.session.add(historial)
        
        db.session.commit()
        flash(f'Documento firmado subido exitosamente. <a href="{web_view_link}" target="_blank" class="alert-link">Ver documento</a>', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al subir el documento firmado: {str(e)}', 'danger')
    
    return redirect(url_for('concursos.ver', concurso_id=concurso_id))

@concursos.route('/<int:concurso_id>/documentos/<int:documento_id>/enviar-firma', methods=['POST'])
@login_required
def enviar_firma(concurso_id, documento_id):
    """Send a document for signature via email."""
    try:
        concurso = Concurso.query.get_or_404(concurso_id)
        documento = DocumentoConcurso.query.get_or_404(documento_id)
        
        # Validate document state and type
        if (documento.estado not in ['BORRADOR', 'ENVIADO PARA FIRMAR']) or 'RESOLUCION' not in documento.tipo:
            flash('Solo se pueden enviar para firma resoluciones en estado borrador o enviado para firma.', 'error')
            return redirect(url_for('concursos.ver', concurso_id=concurso_id))
            
        # Get form data
        destinatario = request.form.get('destinatario')
        observaciones = request.form.get('observaciones', '')
        
        if not destinatario:
            flash('El correo del destinatario es requerido.', 'error')
            return redirect(url_for('concursos.ver', concurso_id=concurso_id))
            
        # Get the Google Drive API instance
        drive_api = GoogleDriveAPI()
        
        # Prepare email content
        doc_name = documento.tipo.replace('_', ' ').title()
        subject = f'Solicitud de firma: {doc_name} - Exp. {concurso.expediente or "S/N"}'
        html_body = f"""
        <p>Se solicita la firma del siguiente documento:</p>
        <p><strong>{doc_name}</strong></p>
        <p><strong>Detalles del concurso:</strong></p>
        <ul>
            <li>Departamento: {concurso.departamento_rel.nombre}</li>
            <li>Área: {concurso.area}</li>
            <li>Orientación: {concurso.orientacion}</li>
            <li>Categoría: {concurso.categoria_nombre} ({concurso.categoria})</li>
            <li>Dedicación: {concurso.dedicacion}</li>
        </ul>
        """
        
        if observaciones:
            html_body += f"<p><strong>Observaciones:</strong></p><p>{observaciones}</p>"
            
        # Send email with document as attachment
        drive_api.send_email(
            to_email=destinatario,
            subject=subject,
            html_body=html_body,
            sender_name='Sistema de Concursos Docentes',
            attachment_ids=[documento.file_id],
            placeholders={
                'expediente': concurso.expediente or 'S/N',
                'departamento': concurso.departamento_rel.nombre,
                'area': concurso.area,
                'orientacion': concurso.orientacion,
                'categoria': concurso.categoria_nombre,
                'dedicacion': concurso.dedicacion
            }
        )
        
        # Update document state
        documento.estado = 'ENVIADO PARA FIRMAR'
        db.session.commit()
        
        # Add entry to history
        historial = HistorialEstado(
            concurso=concurso,
            estado="DOCUMENTO_ENVIADO_FIRMA",
            observaciones=f"Documento {doc_name} enviado para firma a {destinatario}"
        )
        db.session.add(historial)
        db.session.commit()
        
        flash(f'El documento ha sido enviado a {destinatario} para su firma.', 'success')
        
    except Exception as e:
        flash(f'Error al enviar el documento: {str(e)}', 'error')
        
    return redirect(url_for('concursos.ver', concurso_id=concurso_id))

@concursos.route('/<int:concurso_id>/documento/<int:documento_id>/nueva-version', methods=['POST'])
@login_required
def nueva_version_documento(concurso_id, documento_id):
    """Create a new version of a document."""
    try:
        concurso = Concurso.query.get_or_404(concurso_id)
        documento = DocumentoConcurso.query.get_or_404(documento_id)
        
        # Verify the document belongs to the concurso
        if documento.concurso_id != concurso_id:
            flash('El documento no pertenece a este concurso.', 'danger')
            return redirect(url_for('concursos.ver_versiones', concurso_id=concurso_id, documento_id=documento_id))
        
        # Get form data
        observaciones = request.form.get('observaciones', '')
        file = request.files.get('documento')
        
        if not file:
            flash('No se seleccionó ningún archivo.', 'danger')
            return redirect(url_for('concursos.ver_versiones', concurso_id=concurso_id, documento_id=documento_id))
        
        # Get the latest version number
        latest_version = db.session.query(db.func.max(DocumentoVersion.version)).filter_by(documento_id=documento_id).scalar() or 0
        
        # Create a new filename with version
        file_name = f"{documento.tipo.lower().replace('_', ' ')}_{concurso.id}_v{latest_version + 1}.pdf"
        
        # Upload the new file to Google Drive
        file_data = file.read()
        file_id, web_view_link = drive_api.upload_document(
            concurso.borradores_folder_id,
            file_name,
            file_data
        )
        
        # Update the current document URL
        documento.url = web_view_link
        
        # Create a new version record
        version = DocumentoVersion(
            documento_id=documento_id,
            version=latest_version + 1,
            url=web_view_link,
            file_id=file_id,
            creado_por=current_user.username,
            observaciones=observaciones
        )
        db.session.add(version)
        
        # Add entry to history
        historial = HistorialEstado(
            concurso=concurso,
            estado="NUEVA_VERSION_DOCUMENTO",
            observaciones=f"Nueva versión del documento {documento.tipo} creada por {current_user.username}"
        )
        db.session.add(historial)
        
        db.session.commit()
        flash(f'Nueva versión del documento creada exitosamente.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al crear nueva versión: {str(e)}', 'danger')
    
    return redirect(url_for('concursos.ver_versiones', concurso_id=concurso_id, documento_id=documento_id))

@concursos.route('/<int:concurso_id>/documento/<int:documento_id>/eliminar-firmado', methods=['POST'])
@login_required
def eliminar_documento_firmado(concurso_id, documento_id):
    """Delete a signed version of a document."""
    concurso = Concurso.query.get_or_404(concurso_id)
    documento = DocumentoConcurso.query.get_or_404(documento_id)
    
    # Verify the document belongs to the concurso
    if documento.concurso_id != concurso_id:
        flash('El documento no pertenece a este concurso.', 'danger')
        return redirect(url_for('concursos.ver', concurso_id=concurso_id))
    
    try:
        # Update document status back to BORRADOR
        documento.estado = 'BORRADOR'
        
        # Add entry to history
        historial = HistorialEstado(
            concurso=concurso,
            estado="DOCUMENTO_FIRMADO_ELIMINADO",
            observaciones=f"Documento firmado {documento.tipo} eliminado por {current_user.username}"
        )
        db.session.add(historial)
        
        db.session.commit()
        flash('Documento firmado eliminado exitosamente. El documento volvió al estado borrador.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el documento firmado: {str(e)}', 'danger')
    
    return redirect(url_for('concursos.ver', concurso_id=concurso_id))

@concursos.route('/<int:concurso_id>/documento/<int:documento_id>/eliminar-pendiente-firma', methods=['POST'])
@login_required
def eliminar_documento_pendiente_firma(concurso_id, documento_id):
    """Delete a document that is pending signature, resetting it back to BORRADOR state."""
    concurso = Concurso.query.get_or_404(concurso_id)
    documento = DocumentoConcurso.query.get_or_404(documento_id)
    
    # Verify the document belongs to the concurso
    if documento.concurso_id != concurso_id:
        flash('El documento no pertenece a este concurso.', 'danger')
        return redirect(url_for('concursos.ver', concurso_id=concurso_id))
    
    try:
        # Check if document is in PENDIENTE DE FIRMA state
        if documento.estado != 'PENDIENTE DE FIRMA':
            flash('El documento no está pendiente de firma.', 'warning')
            return redirect(url_for('concursos.ver', concurso_id=concurso_id))
        
        # Delete the file from Google Drive if file_id exists
        if documento.file_id:
            try:
                drive_api.delete_file(documento.file_id)
                documento.file_id = None  # Clear the file_id after successful deletion
                documento.url = None      # Clear the URL as well
            except Exception as e:
                flash(f'Advertencia: No se pudo eliminar el archivo de Google Drive: {str(e)}', 'warning')
        
        # Remove all signatures associated with this document
        for firma in documento.firmas:
            db.session.delete(firma)
        
        # Reset firma count
        documento.firma_count = 0
        
        # Update document status back to BORRADOR
        documento.estado = 'BORRADOR'
        
        # Add entry to history
        historial = HistorialEstado(
            concurso=concurso,
            estado="DOCUMENTO_PENDIENTE_FIRMA_ELIMINADO",
            observaciones=f"Documento pendiente de firma {documento.tipo} eliminado por {current_user.username}"
        )
        db.session.add(historial)
        
        db.session.commit()
        flash('Documento pendiente de firma eliminado exitosamente. El documento volvió al estado borrador y puede ser subido nuevamente por el tribunal.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el documento pendiente de firma: {str(e)}', 'danger')
    
    return redirect(url_for('concursos.ver', concurso_id=concurso_id))

@concursos.route('/<int:concurso_id>/documento/<int:documento_id>/eliminar-borrador', methods=['POST'])
@login_required
def eliminar_borrador(concurso_id, documento_id):
    """Delete a draft document from the borradores folder."""
    concurso = Concurso.query.get_or_404(concurso_id)
    documento = DocumentoConcurso.query.get_or_404(documento_id)
    
    # Verify the document belongs to the concurso
    if documento.concurso_id != concurso_id:
        flash('El documento no pertenece a este concurso.', 'danger')
        return redirect(url_for('concursos.ver', concurso_id=concurso_id))
    
    try:
        # Delete the file from Google Drive borradores folder
        if documento.borrador_file_id:  # Use borrador_file_id instead of file_id
            try:
                drive_api.delete_file(documento.borrador_file_id)
                documento.borrador_file_id = None  # Clear the borrador_file_id after successful deletion
            except Exception as e:
                flash(f'Advertencia: No se pudo eliminar el archivo de Google Drive: {str(e)}', 'warning')
        
        # Add entry to history
        historial = HistorialEstado(
            concurso=concurso,
            estado="BORRADOR_ELIMINADO",
            observaciones=f"Borrador de {documento.tipo} eliminado por {current_user.username}"
        )
        db.session.add(historial)
        
        # If this is the only version (no signed document exists), delete the document record
        if documento.estado == 'BORRADOR':
            db.session.delete(documento)
        else:
            documento.estado = 'CREADO'  # Reset state if there's still a signed version
        
        db.session.commit()
        flash('Borrador eliminado exitosamente.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el borrador: {str(e)}', 'danger')
    
    return redirect(url_for('concursos.ver', concurso_id=concurso_id))

@concursos.route('/<int:concurso_id>/documento/<int:documento_id>/eliminar-subido', methods=['POST'])
@login_required
def eliminar_subido(concurso_id, documento_id):
    """Delete an uploaded/signed document from the firmados folder."""
    concurso = Concurso.query.get_or_404(concurso_id)
    documento = DocumentoConcurso.query.get_or_404(documento_id)
    
    # Verify the document belongs to the concurso
    if documento.concurso_id != concurso_id:
        flash('El documento no pertenece a este concurso.', 'danger')
        return redirect(url_for('concursos.ver', concurso_id=concurso_id))
    
    try:
        # Delete the file from Google Drive firmados folder
        if documento.file_id:
            try:
                drive_api.delete_file(documento.file_id)
                documento.file_id = None  # Only clear the firmado file_id
            except Exception as e:
                flash(f'Advertencia: No se pudo eliminar el archivo de Google Drive: {str(e)}', 'warning')
        
        # Remove all signatures associated with this document
        for firma in documento.firmas:
            db.session.delete(firma)
        
        # Reset firma count
        documento.firma_count = 0
        
        # Reset document status to BORRADOR if there's still a draft version
        if documento.borrador_file_id:
            documento.estado = 'BORRADOR'
            documento.url = None  # Clear the URL since it pointed to the firmado version
        else:
            documento.estado = 'CREADO'  # No versions exist
        
        # Add entry to history
        historial = HistorialEstado(
            concurso=concurso,
            estado="DOCUMENTO_SUBIDO_ELIMINADO",
            observaciones=f"Documento subido {documento.tipo} eliminado por {current_user.username}"
        )
        db.session.add(historial)
        
        db.session.commit()
        flash('Documento subido eliminado exitosamente. El tribunal puede subir un nuevo documento.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el documento subido: {str(e)}', 'danger')
    
    return redirect(url_for('concursos.ver', concurso_id=concurso_id))

@concursos.route('/<int:concurso_id>/reset-temas', methods=['POST'])
@login_required
def reset_temas(concurso_id):
    """Reset sorteo temas for a concurso. Only accessible by admin."""
    concurso = Concurso.query.get_or_404(concurso_id)
    
    if not concurso.sustanciacion:
        flash('El concurso no tiene información de sustanciación.', 'danger')
        return redirect(url_for('concursos.ver', concurso_id=concurso_id))
    
    try:
        concurso.sustanciacion.temas_exposicion = None
        
        # Add entry to history
        historial = HistorialEstado(
            concurso=concurso,
            estado="TEMAS_SORTEO_ELIMINADOS",
            observaciones=f"Temas de sorteo eliminados por administrador {current_user.username}"
        )
        db.session.add(historial)
        db.session.commit()
        
        flash('Temas de sorteo eliminados exitosamente.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar los temas: {str(e)}', 'danger')
    
    return redirect(url_for('concursos.ver', concurso_id=concurso_id))

@concursos.route('/<int:concurso_id>/realizar-sorteo', methods=['POST'])
@login_required
def realizar_sorteo(concurso_id):
    """Randomly select one tema from the list of temas_exposicion."""
    concurso = Concurso.query.get_or_404(concurso_id)
    
    if not concurso.sustanciacion or not concurso.sustanciacion.temas_exposicion:
        return jsonify({'error': 'No hay temas definidos para este concurso'}), 400
    
    try:
        # Split temas by the separator and filter out empty strings
        temas = [tema.strip() for tema in concurso.sustanciacion.temas_exposicion.split('|') if tema.strip()]
        
        if not temas:
            return jsonify({'error': 'No hay temas válidos definidos'}), 400
        
        # Randomly select one tema
        import random
        selected_tema = random.choice(temas)
        
        # Save the selected tema to the database
        concurso.sustanciacion.tema_sorteado = selected_tema
        
        # Add an entry to the history
        historial = HistorialEstado(
            concurso=concurso,
            estado="TEMA_SORTEADO",
            observaciones=f"Tema sorteado: {selected_tema}"
        )
        db.session.add(historial)
        db.session.commit()
        
        # Return the selected tema and all temas
        return jsonify({
            'success': True,
            'selectedTema': selected_tema,
            'allTemas': temas
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@concursos.route('/<int:concurso_id>/reset-tema-sorteado', methods=['POST'])
@login_required
def reset_tema_sorteado(concurso_id):
    """Reset only the tema_sorteado for a concurso, keeping temas_exposicion intact."""
    concurso = Concurso.query.get_or_404(concurso_id)
    
    if not concurso.sustanciacion or not concurso.sustanciacion.tema_sorteado:
        flash('No hay tema sorteado para este concurso.', 'warning')
        return redirect(url_for('concursos.ver', concurso_id=concurso_id))
    
    try:
        # Store the tema that was reset for the history
        tema_anterior = concurso.sustanciacion.tema_sorteado
        
        # Reset only the tema_sorteado field
        concurso.sustanciacion.tema_sorteado = None
        
        # Add entry to history
        historial = HistorialEstado(
            concurso=concurso,
            estado="TEMA_SORTEADO_ELIMINADO",
            observaciones=f"Tema sorteado eliminado por administrador {current_user.username}. Tema anterior: {tema_anterior}"
        )
        db.session.add(historial)
        db.session.commit()
        
        flash('Tema sorteado eliminado exitosamente. Puede realizar un nuevo sorteo.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el tema sorteado: {str(e)}', 'danger')
    
    return redirect(url_for('concursos.ver', concurso_id=concurso_id))