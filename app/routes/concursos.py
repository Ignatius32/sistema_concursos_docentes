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
            # Store old data for comparison
            old_departamento_id = concurso.departamento_id
            old_area = concurso.area
            old_orientacion = concurso.orientacion
            old_categoria = concurso.categoria
            old_dedicacion = concurso.dedicacion

            # Update concurso data from form
            tipo = request.form.get('tipo')
            concurso.tipo = tipo
            
            # Handle resolution numbers based on tipo
            if tipo == 'Interino':
                concurso.nro_res_llamado_interino = request.form.get('nro_res_llamado_interino')
                concurso.nro_res_llamado_regular = None
                concurso.nro_res_tribunal_regular = None
            elif tipo == 'Regular':
                concurso.nro_res_llamado_interino = None
                concurso.nro_res_llamado_regular = request.form.get('nro_res_llamado_regular')
                concurso.nro_res_tribunal_regular = request.form.get('nro_res_tribunal_regular')
            else:
                concurso.nro_res_llamado_interino = None
                concurso.nro_res_llamado_regular = None
                concurso.nro_res_tribunal_regular = None
            
            # Rest of the existing update code...
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
            
            # Update Google Drive folder names if relevant fields changed
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
                    
                    # Update main concurso folder
                    new_folder_name = f"{concurso.id}_{departamento.nombre}_{concurso.area}_{concurso.orientacion}_{concurso.categoria}_{concurso.dedicacion}_{timestamp}"
                    drive_api.update_folder_name(concurso.drive_folder_id, new_folder_name)
                    
                    # Update subfolder names
                    if old_categoria != concurso.categoria or old_dedicacion != concurso.dedicacion:
                        subfolders = {
                            'borradores': (concurso.borradores_folder_id, f"borradores_{departamento.nombre}_{concurso.categoria}_{concurso.dedicacion}_{concurso.id}"),
                            'postulantes': (concurso.postulantes_folder_id, f"postulantes_{departamento.nombre}_{concurso.categoria}_{concurso.dedicacion}_{concurso.id}"),
                            'documentos_firmados': (concurso.documentos_firmados_folder_id, f"documentos_firmados_{departamento.nombre}_{concurso.categoria}_{concurso.dedicacion}_{concurso.id}"),
                            'tribunal': (concurso.tribunal_folder_id, f"tribunal_{departamento.nombre}_{concurso.categoria}_{concurso.dedicacion}_{concurso.id}")
                        }

                        for folder_type, (folder_id, new_name) in subfolders.items():
                            if folder_id:
                                try:
                                    drive_api.update_folder_name(folder_id, new_name)
                                except Exception as e:
                                    flash(f'Error al renombrar la carpeta {folder_type}: {str(e)}', 'warning')
                        
                        # Update postulante folder names since they include categoria and dedicacion
                        for postulante in concurso.postulantes:
                            if postulante.drive_folder_id:
                                try:
                                    new_postulante_folder_name = f"{postulante.apellido}_{postulante.nombre}_{postulante.dni}_{concurso.categoria}_{concurso.dedicacion}"
                                    drive_api.update_folder_name(postulante.drive_folder_id, new_postulante_folder_name)
                                except Exception as e:
                                    flash(f'Error al renombrar la carpeta del postulante {postulante.apellido} {postulante.nombre}: {str(e)}', 'warning')

                except Exception as e:
                    flash(f'El concurso fue actualizado pero hubo un error al renombrar su carpeta en Drive: {str(e)}', 'warning')
            
            # Update or create Sustanciacion record
            constitucion_fecha_str = request.form.get('constitucion_fecha')
            sorteo_fecha_str = request.form.get('sorteo_fecha')
            exposicion_fecha_str = request.form.get('exposicion_fecha')
            temas_exposicion = request.form.get('temas_exposicion')

            # Check if a Sustanciacion record needs to be created
            if not concurso.sustanciacion:
                if (constitucion_fecha_str or request.form.get('constitucion_lugar') or 
                    request.form.get('constitucion_virtual_link') or request.form.get('constitucion_observaciones') or
                    sorteo_fecha_str or request.form.get('sorteo_lugar') or
                    request.form.get('sorteo_virtual_link') or request.form.get('sorteo_observaciones') or
                    temas_exposicion or  # Added this check
                    exposicion_fecha_str or request.form.get('exposicion_lugar') or
                    request.form.get('exposicion_virtual_link') or request.form.get('exposicion_observaciones')):
                    
                    concurso.sustanciacion = Sustanciacion(concurso=concurso)
                    db.session.add(concurso.sustanciacion)
            
            if concurso.sustanciacion:
                # Update dates if provided
                if constitucion_fecha_str:
                    concurso.sustanciacion.constitucion_fecha = datetime.strptime(constitucion_fecha_str, '%Y-%m-%dT%H:%M')
                if sorteo_fecha_str:
                    concurso.sustanciacion.sorteo_fecha = datetime.strptime(sorteo_fecha_str, '%Y-%m-%dT%H:%M')
                if exposicion_fecha_str:
                    concurso.sustanciacion.exposicion_fecha = datetime.strptime(exposicion_fecha_str, '%Y-%m-%dT%H:%M')
                
                # Add logging for debugging
                print(f"Saving temas_exposicion: {temas_exposicion}")
                
                # Update other fields
                concurso.sustanciacion.constitucion_lugar = request.form.get('constitucion_lugar')
                concurso.sustanciacion.constitucion_virtual_link = request.form.get('constitucion_virtual_link')
                concurso.sustanciacion.constitucion_observaciones = request.form.get('constitucion_observaciones')
                concurso.sustanciacion.sorteo_lugar = request.form.get('sorteo_lugar')
                concurso.sustanciacion.sorteo_virtual_link = request.form.get('sorteo_virtual_link')
                concurso.sustanciacion.sorteo_observaciones = request.form.get('sorteo_observaciones')
                concurso.sustanciacion.temas_exposicion = temas_exposicion
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
        
        # Get base filename from the original document
        original_url = documento.url
        original_file_id = original_url.split('/')[-2]  # Extract file ID from Google Drive URL
        
        # Create the new filename with _firmado suffix
        original_filename = documento.tipo.lower().replace('_', ' ') + f"_concurso_{concurso_id}"
        new_filename = f"{original_filename}_firmado.pdf"
        
        # Convert to PDF if it's not already and get file data
        file_data = file.read()
        
        # Upload to Google Drive in the documentos_firmados folder
        file_id, web_view_link = drive_api.upload_document(
            concurso.documentos_firmados_folder_id,
            new_filename,
            file_data
        )
        
        # Update document status to FIRMADO
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
        if documento.file_id:
            try:
                drive_api.delete_file(documento.file_id)
                documento.file_id = None  # Clear the file_id after successful deletion
                documento.url = None  # Clear the URL as well since the file no longer exists
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
            except Exception as e:
                flash(f'Advertencia: No se pudo eliminar el archivo de Google Drive: {str(e)}', 'warning')
        
        # Remove all signatures associated with this document
        for firma in documento.firmas:
            db.session.delete(firma)
        
        # Reset firma count
        documento.firma_count = 0
        
        # Reset document status to allow new upload
        documento.estado = 'BORRADOR'
        
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