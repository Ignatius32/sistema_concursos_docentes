from flask import request, jsonify
from app.models.models import Departamento, Area, Orientacion
from . import concursos
from app.helpers.api_services import get_programa_by_id_materia, get_programas_by_materia_ids

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

@concursos.route('/api/programa/<int:id_materia>')
def get_programa(id_materia):
    """API endpoint to fetch programa information for a specific materia."""
    programa_info = get_programa_by_id_materia(id_materia)
    if not programa_info:
        return jsonify({"status": "error", "message": "Error fetching programa information"})
    return jsonify(programa_info)

@concursos.route('/api/programas-bulk', methods=['POST'])
def get_programas_bulk():
    """API endpoint to fetch programa information for multiple materias in one request."""
    data = request.get_json()
    if not data or 'materia_ids' not in data:
        return jsonify({"status": "error", "message": "materia_ids required in request body"})
    
    materia_ids = data.get('materia_ids', [])
    if not materia_ids or not isinstance(materia_ids, list):
        return jsonify({"status": "error", "message": "materia_ids must be a non-empty list"})
    
    # Call the helper function to get all programas
    programas_info = get_programas_by_materia_ids(materia_ids)
    if not programas_info:
        return jsonify({"status": "error", "message": "Error fetching programas information"})
    
    return jsonify({"status": "success", "results": programas_info})
