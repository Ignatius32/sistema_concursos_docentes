"""
Admin routes for managing considerandos and departamento heads data.
Provides CRUD operations for data that was previously fetched from external APIs.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.models.models import db, Considerandos, DepartamentoHead
from app.utils.keycloak_auth import admin_required
from app.services.placeholder_resolver import get_core_placeholders
import json

# Create a blueprint for admin API data management routes
admin_api_data_bp = Blueprint('admin_api_data', __name__, url_prefix='/admin/api-data')

@admin_api_data_bp.route('/considerandos')
@admin_required
def considerandos_list():
    """List all considerandos."""
    considerandos = Considerandos.query.filter_by(is_active=True).order_by(Considerandos.document_type).all()
    return render_template('admin/api_data/considerandos_list.html', considerandos=considerandos)

@admin_api_data_bp.route('/considerandos/new', methods=['GET', 'POST'])
@admin_required
def considerandos_new():
    """Create new considerando."""
    if request.method == 'POST':
        try:            # Get form data
            document_type = request.form.get('document_type', '').strip()
            visibility = request.form.get('visibility', '').strip()
            considerandos_json = request.form.get('considerandos_data', '').strip()
            
            # Validate required fields
            if not document_type or not visibility:
                flash('Document type and visibility are required.', 'error')
                return render_template('admin/api_data/considerandos_form.html', 
                                     data={'document_type': document_type, 'visibility': visibility, 
                                           'considerandos_data': considerandos_json})
              # Check if document_type already exists
            existing = Considerandos.query.filter_by(document_type=document_type).first()
            if existing:
                flash(f'Considerando with document type "{document_type}" already exists.', 'error')
                return render_template('admin/api_data/considerandos_form.html', 
                                     data={'document_type': document_type, 'visibility': visibility, 
                                           'considerandos_data': considerandos_json})
            
            # Parse JSON data
            try:
                considerandos_data = json.loads(considerandos_json) if considerandos_json else {}
            except json.JSONDecodeError as e:
                flash(f'Invalid JSON format in considerandos data: {str(e)}', 'error')
                return render_template('admin/api_data/considerandos_form.html', 
                                     data={'document_type': document_type, 'visibility': visibility, 
                                           'considerandos_data': considerandos_json})
            
            # Create new considerando
            considerando = Considerandos(
                document_type=document_type,
                visibility=visibility,
                considerandos_data=considerandos_data
            )            
            db.session.add(considerando)
            db.session.commit()
            
            flash(f'Considerando "{document_type}" created successfully.', 'success')
            return redirect(url_for('admin_api_data.considerandos_list'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating considerando: {str(e)}', 'error')
            return render_template('admin/api_data/considerandos_form.html', 
                                 data={'document_type': document_type, 'visibility': visibility, 
                                       'considerandos_data': considerandos_json})
    
    return render_template('admin/api_data/considerandos_form.html')

@admin_api_data_bp.route('/considerandos/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def considerandos_edit(id):
    """Edit existing considerando."""
    considerando = Considerandos.query.get_or_404(id)
    
    if request.method == 'POST':        
        try:
            # Get form data
            document_type = request.form.get('document_type', '').strip()
            visibility = request.form.get('visibility', '').strip()
            considerandos_json = request.form.get('considerandos_data', '').strip()
            
            # Validate required fields
            if not document_type or not visibility:
                flash('Document type and visibility are required.', 'error')
                return render_template('admin/api_data/considerandos_form.html', 
                                     considerando=considerando,
                                     data={'document_type': document_type, 'visibility': visibility, 
                                           'considerandos_data': considerandos_json})
            
            # Check if document_type already exists (excluding current record)
            existing = Considerandos.query.filter(
                Considerandos.document_type == document_type,
                Considerandos.id != id
            ).first()
            if existing:
                flash(f'Considerando with document type "{document_type}" already exists.', 'error')
                return render_template('admin/api_data/considerandos_form.html', 
                                     considerando=considerando,
                                     data={'document_type': document_type, 'visibility': visibility, 
                                           'considerandos_data': considerandos_json})
            # Parse JSON data
            try:
                considerandos_data = json.loads(considerandos_json) if considerandos_json else {}
            except json.JSONDecodeError as e:
                flash(f'Invalid JSON format in considerandos data: {str(e)}', 'error')
                return render_template('admin/api_data/considerandos_form.html', 
                                     considerando=considerando,
                                     data={'document_type': document_type, 'visibility': visibility, 
                                           'considerandos_data': considerandos_json})
            
            # Update considerando
            considerando.document_type = document_type
            considerando.visibility = visibility
            considerando.considerandos_data = considerandos_data
            
            db.session.commit()
            
            flash(f'Considerando "{document_type}" updated successfully.', 'success')
            return redirect(url_for('admin_api_data.considerandos_list'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating considerando: {str(e)}', 'error')
    
    # For GET request, prepare data for form
    data = {
        'document_type': considerando.document_type,
        'visibility': considerando.visibility,
        'considerandos_data': json.dumps(considerando.considerandos_data, indent=2)
    }
    
    return render_template('admin/api_data/considerandos_form.html', considerando=considerando, data=data)

@admin_api_data_bp.route('/considerandos/<int:id>/delete', methods=['POST'])
@admin_required
def considerandos_delete(id):
    """Delete considerando (soft delete)."""
    try:
        considerando = Considerandos.query.get_or_404(id)
        considerando.is_active = False
        db.session.commit()
        
        flash(f'Considerando "{considerando.document_type}" deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting considerando: {str(e)}', 'error')
    
    return redirect(url_for('admin_api_data.considerandos_list'))

@admin_api_data_bp.route('/departamento-heads')
@admin_required
def departamento_heads_list():
    """List all departamento heads."""
    heads = DepartamentoHead.query.filter_by(is_active=True).order_by(DepartamentoHead.departamento).all()
    return render_template('admin/api_data/departamento_heads_list.html', heads=heads)

@admin_api_data_bp.route('/departamento-heads/new', methods=['GET', 'POST'])
@admin_required
def departamento_heads_new():
    """Create new departamento head."""
    if request.method == 'POST':
        try:
            # Get form data
            departamento = request.form.get('departamento', '').strip()
            responsable = request.form.get('responsable', '').strip()
            correo = request.form.get('correo', '').strip()
            prefijo = request.form.get('prefijo', '').strip()
            
            # Validate required fields
            if not departamento:
                flash('Departamento is required.', 'error')
                return render_template('admin/api_data/departamento_heads_form.html', 
                                     data={'departamento': departamento, 'responsable': responsable, 
                                           'correo': correo, 'prefijo': prefijo})
            
            # Check if departamento already exists
            existing = DepartamentoHead.query.filter_by(departamento=departamento).first()
            if existing:
                flash(f'Departamento head for "{departamento}" already exists.', 'error')
                return render_template('admin/api_data/departamento_heads_form.html', 
                                     data={'departamento': departamento, 'responsable': responsable, 
                                           'correo': correo, 'prefijo': prefijo})
            
            # Create new departamento head
            head = DepartamentoHead(
                departamento=departamento,
                responsable=responsable,
                correo=correo,
                prefijo=prefijo
            )
            
            db.session.add(head)
            db.session.commit()
            
            flash(f'Departamento head for "{departamento}" created successfully.', 'success')
            return redirect(url_for('admin_api_data.departamento_heads_list'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating departamento head: {str(e)}', 'error')
    
    return render_template('admin/api_data/departamento_heads_form.html')

@admin_api_data_bp.route('/departamento-heads/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def departamento_heads_edit(id):
    """Edit existing departamento head."""
    head = DepartamentoHead.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            # Get form data
            departamento = request.form.get('departamento', '').strip()
            responsable = request.form.get('responsable', '').strip()
            correo = request.form.get('correo', '').strip()
            prefijo = request.form.get('prefijo', '').strip()
            
            # Validate required fields
            if not departamento:
                flash('Departamento is required.', 'error')
                return render_template('admin/api_data/departamento_heads_form.html', 
                                     head=head,
                                     data={'departamento': departamento, 'responsable': responsable, 
                                           'correo': correo, 'prefijo': prefijo})
            
            # Check if departamento already exists (excluding current record)
            existing = DepartamentoHead.query.filter(
                DepartamentoHead.departamento == departamento,
                DepartamentoHead.id != id
            ).first()
            if existing:
                flash(f'Departamento head for "{departamento}" already exists.', 'error')
                return render_template('admin/api_data/departamento_heads_form.html', 
                                     head=head,
                                     data={'departamento': departamento, 'responsable': responsable, 
                                           'correo': correo, 'prefijo': prefijo})
            
            # Update departamento head
            head.departamento = departamento
            head.responsable = responsable
            head.correo = correo
            head.prefijo = prefijo
            
            db.session.commit()
            
            flash(f'Departamento head for "{departamento}" updated successfully.', 'success')
            return redirect(url_for('admin_api_data.departamento_heads_list'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating departamento head: {str(e)}', 'error')
    
    # For GET request, prepare data for form
    data = {
        'departamento': head.departamento,
        'responsable': head.responsable,
        'correo': head.correo,
        'prefijo': head.prefijo
    }
    
    return render_template('admin/api_data/departamento_heads_form.html', head=head, data=data)

@admin_api_data_bp.route('/departamento-heads/<int:id>/delete', methods=['POST'])
@admin_required
def departamento_heads_delete(id):
    """Delete departamento head (soft delete)."""
    try:
        head = DepartamentoHead.query.get_or_404(id)
        head.is_active = False
        db.session.commit()
        
        flash(f'Departamento head for "{head.departamento}" deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting departamento head: {str(e)}', 'error')
    
    return redirect(url_for('admin_api_data.departamento_heads_list'))

# API endpoints for JSON responses (for backward compatibility)
@admin_api_data_bp.route('/api/considerandos')
@admin_required
def api_considerandos_list():
    """API endpoint to get all considerandos as JSON."""
    considerandos = Considerandos.query.filter_by(is_active=True).all()
    return jsonify([c.to_dict() for c in considerandos])

@admin_api_data_bp.route('/api/departamento-heads')
@admin_required
def api_departamento_heads_list():
    """API endpoint to get all departamento heads as JSON."""
    heads = DepartamentoHead.query.filter_by(is_active=True).all()
    return jsonify([h.to_dict() for h in heads])

@admin_api_data_bp.route('/placeholders')
@admin_required
def placeholders_list():
    """List all available placeholders with descriptions and examples."""
    
    # Define placeholder categories and descriptions
    placeholder_info = {
        'concurso_general': {
            'name': 'Información General del Concurso',
            'placeholders': {
                'id_concurso': 'ID único del concurso',
                'expediente': 'Número de expediente',
                'tipo_concurso': 'Tipo de concurso (Regular, Interino, etc.)',
                'area': 'Área académica',
                'orientacion': 'Orientación específica',
                'categoria_codigo': 'Código de la categoría (Profesor, JTP, etc.)',
                'categoria_nombre': 'Nombre completo de la categoría',
                'dedicacion': 'Tipo de dedicación (Exclusiva, Parcial, Simple)',
                'cant_cargos_numero': 'Número de cargos (como número)',
                'cant_cargos_texto': 'Descripción textual de los cargos',
                'descripcion_cargo': 'Descripción completa del cargo',
                'departamento_nombre': 'Nombre del departamento',
                'origen_vacante': 'Origen de la vacante',
                'docente_que_genera_vacante': 'Docente que genera la vacante',
                'licencia': 'Información de licencia (si aplica)',
                'tkd': 'Código TKD'
            }
        },
        'resoluciones': {
            'name': 'Números de Resoluciones',
            'placeholders': {
                'nro_res_llamado': 'Número de resoluciones asociadas al llamado',
                'nro_res_tribunal': 'Número de resoluciones asociadas al tribunal',
                'nro_res_otras': 'Otras resoluciones'
            }
        },
        'fechas': {
            'name': 'Fechas',
            'placeholders': {
                'fecha_actual': 'Fecha actual (formato DD/MM/YYYY)',
                'yyyy': 'Año actual',
                'cierre_inscripcion_fecha': 'Fecha de cierre de inscripción'
            }
        },
        'departamento': {
            'name': 'Responsable de Departamento',
            'placeholders': {
                'resp_departamento': 'Nombre del responsable del departamento',
                'prefijo_resp_departamento': 'Prefijo del responsable (Dr., Mg., etc.)'
            }
        },
        'tribunal': {
            'name': 'Tribunal',
            'placeholders': {
                'tribunal_presidente': 'Presidente del tribunal',
                'tribunal_titulares_lista': 'Lista de miembros titulares',
                'tribunal_suplentes_lista': 'Lista de miembros suplentes',
                'tribunal_titular_docente_lista': 'Lista de titulares docentes',
                'tribunal_titular_estudiante_lista': 'Lista de titulares estudiantes',
                'tribunal_suplente_docente_lista': 'Lista de suplentes docentes',
                'tribunal_suplente_estudiante_lista': 'Lista de suplentes estudiantes'
            }
        },
        'postulantes': {
            'name': 'Postulantes',
            'placeholders': {
                'postulantes_lista_completa': 'Lista completa de postulantes',
                'postulantes_activos_lista': 'Lista de postulantes activos'
            }
        },
        'sustanciacion': {
            'name': 'Sustanciación',
            'placeholders': {
                'constitucion_fecha': 'Fecha de constitución del tribunal',
                'constitucion_lugar': 'Lugar de constitución del tribunal',
                'constitucion_virtual_link': 'Link virtual para constitución',
                'sorteo_fecha': 'Fecha del sorteo',
                'sorteo_lugar': 'Lugar del sorteo',
                'sorteo_virtual_link': 'Link virtual para sorteo',
                'exposicion_fecha': 'Fecha de exposición',
                'exposicion_lugar': 'Lugar de exposición',
                'exposicion_virtual_link': 'Link virtual para exposición',
                'temas_exposicion': 'Temas de exposición (formato raw)',
                'temas_todos': 'Temas formateados con encabezado',
                'temas_sorteados': 'Temas sorteados formateados'
            }
        },
        'notificaciones': {
            'name': 'Notificaciones',
            'placeholders': {
                'nombre_concurso_notificacion': 'Nombre del concurso para notificaciones',
                'nombre_destinatario': 'Nombre del destinatario (requiere persona_id)'
            }
        }
    }
    
    return render_template('admin/api_data/placeholders_list.html', placeholder_info=placeholder_info)
