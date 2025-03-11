from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timezone
from app.models.models import db, Concurso, Departamento, Area, Orientacion, Categoria, HistorialEstado
from app.integrations.google_drive import GoogleDriveAPI

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
            categoria_nombre = request.form.get('categoria_nombre', '')
            dedicacion = request.form.get('dedicacion')
            localizacion = request.form.get('localizacion')
            
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
                categoria_nombre=categoria_nombre,
                dedicacion=dedicacion,
                localizacion=localizacion,
                cierre_inscripcion=cierre_inscripcion,
                vencimiento=vencimiento,
                estado_actual="CREADO"
            )
            
            db.session.add(concurso)
            db.session.flush()  # This gets us the ID without committing
            
            # Create Google Drive folder using the new API class
            departamento = Departamento.query.get(departamento_id)
            folder_id = drive_api.create_concurso_folder(
                concurso.id,
                departamento.nombre,
                area,
                orientacion,
                categoria,
                dedicacion
            )
            
            # Update concurso with the folder ID
            concurso.drive_folder_id = folder_id
            
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
            concurso.categoria_nombre = request.form.get('categoria_nombre', '')
            concurso.dedicacion = request.form.get('dedicacion')
            concurso.localizacion = request.form.get('localizacion')
            
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