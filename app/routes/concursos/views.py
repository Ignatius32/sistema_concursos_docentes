from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from datetime import datetime
from app.models.models import db, Concurso, Departamento, Area, Orientacion, Categoria, HistorialEstado, DocumentoConcurso, Sustanciacion, TribunalMiembro, Persona
from app.services.placeholder_resolver import get_core_placeholders
from app.helpers.api_services import get_considerandos_data, get_asignaturas_from_external_api
from . import concursos, drive_api

@concursos.route('/')
@login_required
def index():
    """Display list of all concursos."""
    # Simply load all concursos, can't use joinedload with dynamic relationship
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
            json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'roles_categorias.json')
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
                cierre_inscripcion=cierre_inscripcion,
                vencimiento=vencimiento,
                origen_vacante=request.form.get('origen_vacante'),
                docente_vacante=request.form.get('docente_vacante'),
                categoria_vacante=request.form.get('categoria_vacante'),
                dedicacion_vacante=request.form.get('dedicacion_vacante'),
                id_designacion_mocovi=request.form.get('id_designacion_mocovi')
            )
            db.session.add(concurso)
            db.session.commit()  # Commit to get concurso ID
              # Create Google Drive folder structure
            try:
                # Create concurso folder with subfolders
                folder_data = drive_api.create_concurso_folder(
                    concurso_id=concurso.id,
                    departamento=concurso.departamento_rel.nombre,
                    area=concurso.area,
                    orientacion=concurso.orientacion,
                    categoria=concurso.categoria,
                    dedicacion=concurso.dedicacion
                )
                
                # Update concurso with folder IDs
                concurso.drive_folder_id = folder_data.get('folderId')
                concurso.borradores_folder_id = folder_data.get('borradoresFolderId')
                concurso.documentos_firmados_folder_id = folder_data.get('documentosFirmadosFolderId')
                concurso.postulantes_folder_id = folder_data.get('postulantesFolderId')
                concurso.tribunal_folder_id = folder_data.get('tribunalFolderId')
                
                # Complete the database update
                db.session.commit()
                
            except Exception as e:
                flash(f'Error al crear carpetas en Google Drive: {str(e)}', 'warning')
                # Continue with the operation even if Drive folders couldn't be created
            
            # Create history entry
            historial = HistorialEstado(
                concurso=concurso,
                estado="CREADO",
                observaciones=f"Concurso creado por {current_user.username}"
            )
            db.session.add(historial)
            db.session.commit()
            
            flash('Concurso creado exitosamente.', 'success')
            return redirect(url_for('concursos.ver', concurso_id=concurso.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear el concurso: {str(e)}', 'danger')
    
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
    from app.models.models import DocumentTemplateConfig, NotificationCampaign, NotificationLog, TemaSetTribunal
    
    concurso = Concurso.query.get_or_404(concurso_id)
    
    # Get asignaturas from external API based on concurso criteria
    asignaturas_externas = []
    if concurso.departamento_rel:
        asignaturas_externas = get_asignaturas_from_external_api(
            departamento=concurso.departamento_rel.nombre,
            area=concurso.area,
            orientacion_concurso=concurso.orientacion
        )
    
    # Get available document types based on configurations in database
    available_documents = []
    # Get all active document template configurations
    template_configs = DocumentTemplateConfig.query.filter_by(is_active=True).all()
    
    # Create dictionary of template configs for easy access in template
    template_configs_dict = {config.document_type_key: config for config in template_configs}
    
    # Debug: print information about templates
    print(f"Found {len(template_configs)} active templates")
    for template in template_configs:
        print(f"Template: {template.document_type_key}, Visible for {template.concurso_visibility}, Current concurso tipo: {concurso.tipo}")
    
    # Check each template's visibility and uniqueness for this concurso
    for config in template_configs:
        # Check if this template is available for this concurso type
        if not config.is_visible_for_concurso_tipo(concurso.tipo):
            print(f"Template {config.document_type_key} not visible for concurso tipo {concurso.tipo}")
            continue
            
        # Check uniqueness constraint if applicable
        if config.is_unique_per_concurso:
            existing_document = DocumentoConcurso.query.filter_by(
                concurso_id=concurso_id,
                tipo=config.document_type_key
            ).first()
            
            if existing_document:
                # Skip this document type as one already exists
                continue
        
        # Add to available documents
        available_documents.append({
            'id': config.document_type_key,
            'name': config.display_name,
            'url': url_for('concursos.generar_documento', 
                         concurso_id=concurso_id, 
                         document_type_key=config.document_type_key)
        })
    
    # Get all global notification campaigns for the notification panel
    notification_campaigns = NotificationCampaign.query.order_by(NotificationCampaign.creado_en.desc()).all()
    
    # Get logs for this concurso grouped by campaign
    notification_logs = NotificationLog.query.filter_by(concurso_id=concurso_id).all()    
    notification_logs_by_campaign = {}
    for log in notification_logs:
        if log.campaign_id not in notification_logs_by_campaign:
            notification_logs_by_campaign[log.campaign_id] = []
        notification_logs_by_campaign[log.campaign_id].append(log)
        
    # Fetch tribunal member topic proposals if a sustanciacion exists
    temas_por_miembro = {}
    if concurso.sustanciacion and hasattr(concurso.sustanciacion, 'id'):
        # Get all topic proposals from tribunal members for this sustanciacion
        tema_proposals = TemaSetTribunal.query.filter_by(
            sustanciacion_id=concurso.sustanciacion.id
        ).all()
        
        # Organize by tribunal member for easy access in template
        for proposal in tema_proposals:
            temas_por_miembro[proposal.miembro_id] = {
                'temas': [tema.strip() for tema in proposal.temas_propuestos.split('|') if tema.strip()],
                'propuesta_cerrada': proposal.propuesta_cerrada,
                'fecha_propuesta': proposal.fecha_propuesta,
                'miembro': proposal.miembro  # Include the miembro relationship
            }
    
    # Debug: print what's being passed to the template
    print(f"Passing {len(available_documents)} available documents to template")
    for doc in available_documents:
        print(f"Document: {doc['name']} ({doc['id']}) URL: {doc['url']}")
        
    return render_template('concursos/ver.html', 
                      concurso=concurso,
                      available_documents=available_documents,
                      template_configs_dict=template_configs_dict,
                      notification_campaigns=notification_campaigns,
                      notification_logs_by_campaign=notification_logs_by_campaign,
                      asignaturas_externas=asignaturas_externas,
                      temas_por_miembro=temas_por_miembro)

@concursos.route('/<int:concurso_id>/editar', methods=['GET', 'POST'])
@login_required
def editar(concurso_id):
    """Edit an existing concurso."""
    concurso = Concurso.query.get_or_404(concurso_id)
    
    if request.method == 'POST':
        try:
            # Store original values to detect changes
            original_departamento_id = concurso.departamento_id
            original_categoria = concurso.categoria
            original_dedicacion = concurso.dedicacion
            original_area = concurso.area
            original_orientacion = concurso.orientacion
            
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
            
            # Extract new values
            new_departamento_id = int(request.form.get('departamento_id'))
            new_categoria = request.form.get('categoria')
            new_dedicacion = request.form.get('dedicacion')
            new_area = request.form.get('area')
            new_orientacion = request.form.get('orientacion')
            
            # Get categoria name from roles_categorias.json
            import json
            import os
            
            # Load roles_categorias.json data
            json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'roles_categorias.json')
            with open(json_path, 'r', encoding='utf-8') as f:
                roles_data = json.load(f)
            
            # Find categoria name by codigo
            categoria_nombre = None
            for rol in roles_data:
                for cat in rol['categorias']:
                    if cat['codigo'] == new_categoria:
                        categoria_nombre = cat['nombre']
                        break
                if categoria_nombre:
                    break
            
            # Update concurso
            concurso.tipo = tipo
            concurso.nro_res_llamado_interino = nro_res_llamado_interino
            concurso.nro_res_llamado_regular = nro_res_llamado_regular
            concurso.nro_res_tribunal_regular = nro_res_tribunal_regular
            concurso.cerrado_abierto = request.form.get('cerrado_abierto')
            concurso.cant_cargos = int(request.form.get('cant_cargos'))
            concurso.departamento_id = new_departamento_id
            concurso.area = new_area
            concurso.orientacion = new_orientacion
            concurso.categoria = new_categoria
            concurso.categoria_nombre = categoria_nombre
            concurso.dedicacion = new_dedicacion
            concurso.localizacion = request.form.get('localizacion')              
            concurso.asignaturas = request.form.get('asignaturas')            
            concurso.expediente = request.form.get('expediente')
              
            # Update vacancy data
            concurso.origen_vacante = request.form.get('origen_vacante')
            concurso.docente_vacante = request.form.get('docente_vacante')
            concurso.categoria_vacante = request.form.get('categoria_vacante')
            concurso.dedicacion_vacante = request.form.get('dedicacion_vacante')
            concurso.id_designacion_mocovi = request.form.get('id_designacion_mocovi')            # Handle cierre_inscripcion
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
            
            # Check if folder names need to be updated due to changes in key fields
            folder_fields_changed = (
                original_departamento_id != new_departamento_id or
                original_categoria != new_categoria or
                original_dedicacion != new_dedicacion or
                original_area != new_area or
                original_orientacion != new_orientacion
            )
            
            if folder_fields_changed and concurso.drive_folder_id:
                try:
                    # Get new department name for folder naming
                    new_departamento_nombre = concurso.departamento_rel.nombre
                    
                    # Update main concurso folder name
                    # Extract timestamp from current folder name or use current time
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    new_main_folder_name = f"{concurso.id}_{new_departamento_nombre}_{new_area}_{new_orientacion}_{new_categoria}_{new_dedicacion}_{timestamp}"
                    drive_api.update_folder_name(concurso.drive_folder_id, new_main_folder_name)
                    
                    # Update subfolder names if they exist
                    subfolders_to_update = {
                        'borradores_folder_id': f"borradores_{new_departamento_nombre}_{new_categoria}_{new_dedicacion}_{concurso.id}",
                        'postulantes_folder_id': f"postulantes_{new_departamento_nombre}_{new_categoria}_{new_dedicacion}_{concurso.id}",
                        'documentos_firmados_folder_id': f"documentos_firmados_{new_departamento_nombre}_{new_categoria}_{new_dedicacion}_{concurso.id}",
                        'tribunal_folder_id': f"tribunal_{new_departamento_nombre}_{new_categoria}_{new_dedicacion}_{concurso.id}"
                    }
                    
                    for folder_attr, new_name in subfolders_to_update.items():
                        folder_id = getattr(concurso, folder_attr)
                        if folder_id:
                            try:
                                drive_api.update_folder_name(folder_id, new_name)
                            except Exception as e:
                                flash(f'Warning: Could not update {folder_attr.replace("_", " ")}: {str(e)}', 'warning')
                    
                    # Update postulante folder names if categoria or dedicacion changed
                    if original_categoria != new_categoria or original_dedicacion != new_dedicacion:
                        from app.models.models import Postulante
                        postulantes = Postulante.query.filter_by(concurso_id=concurso.id).all()
                        
                        for postulante in postulantes:
                            if postulante.drive_folder_id:
                                try:
                                    new_postulante_folder_name = f"{postulante.apellido}_{postulante.nombre}_{postulante.dni}_{new_categoria}_{new_dedicacion}"
                                    drive_api.update_folder_name(postulante.drive_folder_id, new_postulante_folder_name)
                                except Exception as e:
                                    flash(f'Warning: Could not update folder for postulante {postulante.apellido}, {postulante.nombre}: {str(e)}', 'warning')
                    
                    flash('Folder names synchronized with updated concurso information.', 'info')
                    
                except Exception as e:
                    flash(f'Warning: Error synchronizing folder names: {str(e)}', 'warning')
                    # Continue with the operation even if folder sync fails
              # Create history entry for concurso edit
            historial = HistorialEstado(
                concurso_id=concurso.id,
                estado=concurso.estado_actual,
                subestado_snapshot=concurso.subestado,
                fecha=datetime.now(),
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
        concurso.asignaciones_tribunal.delete()
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
