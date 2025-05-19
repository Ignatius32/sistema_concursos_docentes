"""
API routes for fetching programa information.
"""

from flask import Blueprint, jsonify, current_app, request
from app.helpers.api_services import get_programa_by_id_materia, get_programa_download_url, get_programas_by_materia_ids

# Create a blueprint for API routes
api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/programa/<int:id_materia>', methods=['GET'])
def get_programa(id_materia):
    """
    API endpoint to get programa information for a specific materia.
    
    Args:
        id_materia (int): The ID of the materia to get programa for
        
    Returns:
        JSON response with programa information or error message
    """
    try:
        current_app.logger.info(f"API request for programa with materia ID: {id_materia}")
        
        # Get programa information
        programa = get_programa_by_id_materia(id_materia)
        current_app.logger.info(f"Received programa response: {programa}")
        
        # If programa not found, return not found response
        if not programa:
            current_app.logger.warning(f"No program data received for materia ID {id_materia}")
            return jsonify({
                'status': 'error',
                'message': 'No se pudo obtener información del programa',
                'manual_url': 'https://huayca.crub.uncoma.edu.ar/programas/'
            }), 404
            
        # Check if not found flag is set
        if programa.get('not_found'):
            current_app.logger.info(f"Program not found for materia ID {id_materia}")
            return jsonify({
                'status': 'not_found',
                'message': 'Programa no encontrado',
                'manual_url': 'https://huayca.crub.uncoma.edu.ar/programas/'
            }), 200
        
        # Extract id_programa for download URL
        id_programa = programa.get('id_programa')
        
        # Try alternative field names if not found
        if not id_programa:
            possible_id_fields = ['id_programa', 'programa_id', 'id', 'id_prog']
            for field in possible_id_fields:
                if programa.get(field):
                    id_programa = programa.get(field)
                    current_app.logger.info(f"Found program ID in field: {field} = {id_programa}")
                    break
        
        current_app.logger.info(f"Extracted id_programa: {id_programa}")
        
        if not id_programa:
            current_app.logger.warning(f"No id_programa found in response for materia ID {id_materia}")
            # Log the keys available in the programa object to help debug
            current_app.logger.warning(f"Available keys in programa: {list(programa.keys()) if hasattr(programa, 'keys') and hasattr(programa, 'get') else 'Not a dict'}")
            return jsonify({
                'status': 'error',
                'message': 'El programa no tiene ID válido',
                'manual_url': 'https://huayca.crub.uncoma.edu.ar/programas/'
            }), 404
            
        # Check if the programa's materia ID matches the requested materia ID
        prog_materia_id = None
        possible_materia_id_fields = ['id_materia', 'id_materia_prog', 'materia_id']
        
        for field in possible_materia_id_fields:
            if field in programa and programa[field] is not None:
                prog_materia_id = str(programa[field])
                break
                
        # Compare with requested ID
        if prog_materia_id and str(prog_materia_id) != str(id_materia):
            current_app.logger.warning(f"ID mismatch: Requested materia ID {id_materia} but got program for materia ID {prog_materia_id}")
            return jsonify({
                'status': 'not_found',
                'message': 'Programa no coincide con la asignatura solicitada',
                'manual_url': 'https://huayca.crub.uncoma.edu.ar/programas/'
            }), 200
            
        # Get download URL
        download_url = get_programa_download_url(id_programa)
        current_app.logger.info(f"Generated download URL: {download_url}")
        
        # Return success response with download URL
        return jsonify({
            'status': 'success',
            'message': 'Programa encontrado',
            'download_url': download_url,
            'programa': programa
        }), 200
            
    except Exception as e:
        current_app.logger.error(f"Error fetching programa: {str(e)}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': 'Error al obtener el programa',
            'manual_url': 'https://huayca.crub.uncoma.edu.ar/programas/'
        }), 500

@api_bp.route('/programas-bulk', methods=['POST'])
def get_programas_bulk():
    """
    API endpoint to get programa information for multiple materias at once.
    
    Request Body:
        JSON with materia_ids array
    
    Returns:
        JSON response with programa information for each materia ID
    """
    try:
        data = request.get_json()
        if not data or 'materia_ids' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Se requiere una lista de IDs de materias'
            }), 400
            
        materia_ids = data['materia_ids']
        current_app.logger.info(f"API request for bulk programas with {len(materia_ids)} materia IDs")
        
        # Ensure all IDs are converted to strings for consistent handling
        materia_ids_str_list = [str(mid) for mid in materia_ids]
        
        # Use the new bulk fetch function to get all programas at once
        programas_data_map = get_programas_by_materia_ids(materia_ids_str_list)
        
        if programas_data_map is None:
            current_app.logger.error("Failed to fetch programas data")
            return jsonify({
                'status': 'error',
                'message': 'Error al obtener información de programas',
                'manual_url': 'https://huayca.crub.uncoma.edu.ar/programas/'
            }), 500
        
        # Construct the results for frontend
        results_for_frontend = {}
        
        # Process each materia ID
        for id_materia_str in materia_ids_str_list:
            programa_info = programas_data_map.get(id_materia_str)
            
            if not programa_info:
                results_for_frontend[id_materia_str] = {
                    'status': 'not_found',
                    'id_programa': None,
                    'reason': 'programa_not_found'
                }
                continue
                
            # Check if programa was found and has an id_programa
            if not programa_info.get('not_found') and programa_info.get('id_programa'):
                # Success case
                results_for_frontend[id_materia_str] = {
                    'status': 'success',
                    'id_programa': programa_info['id_programa'],
                    'download_url': get_programa_download_url(programa_info['id_programa']),
                    'programa_data': programa_info  # Include the full program data
                }
            else:
                # Not found or no id_programa case
                results_for_frontend[id_materia_str] = {
                    'status': 'not_found',
                    'id_programa': None,
                    'reason': programa_info.get('reason', 'unknown_error') if programa_info else 'programa_not_in_response'
                }
        
        # Return results
        return jsonify({
            'status': 'success',
            'results': results_for_frontend
        }), 200
            
    except Exception as e:
        current_app.logger.error(f"Error in bulk programa fetch: {str(e)}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': 'Error al obtener información de programas',
            'manual_url': 'https://huayca.crub.uncoma.edu.ar/programas/'
        }), 500
