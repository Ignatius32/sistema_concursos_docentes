"""
API service utilities for external API interactions.
Contains functions for fetching data from external APIs used in the application.
"""
import requests
from requests.auth import HTTPBasicAuth, HTTPDigestAuth
import json
from flask import current_app

# URL to fetch considerandos options
CONSIDERANDOS_API_URL = "https://script.google.com/macros/s/AKfycbz48ziHckZ-Ir6_gmXnUZF_S42AapQLnvpjktJXTnSbD1ps1lWimgkrxTzLXyiH_Eorlw/exec"
# URL to fetch departamento heads data
DEPTO_HEADS_API_URL = "https://script.google.com/macros/s/AKfycbyWU4h92lRGefLzLRSS82JhytafKIZl0jey3DuuoiCUicQcVf_1u1vzZzx7mI-0HTOg4w/exec"
# URL to fetch asignaturas data
ASIGNATURAS_API_URL = "https://huayca.crub.uncoma.edu.ar/catedras/1.0/rest/materias"
# URL to fetch programas data
PROGRAMAS_API_URL = "https://huayca.crub.uncoma.edu.ar/catedras/1.0/rest/programas"
# URL to download a programa file
PROGRAMA_DOWNLOAD_URL = "https://huayca.crub.uncoma.edu.ar/programas/download/programa/{id_programa}"

def get_considerandos_data(document_type, tipo_concurso=None):
    """
    Fetch considerandos data from the API for a specific document type.
    This function now only retrieves the actual content of considerandos options,
    as visibility and uniqueness checks are now handled by DocumentTemplateConfig.
    
    Args:
        document_type (str): Type of document to get considerandos for (e.g., 'RESOLUCION_LLAMADO_TRIBUNAL')
        tipo_concurso (str, optional): Type of concurso (kept for backward compatibility)
    
    Returns:
        dict or None: Dictionary with document information including considerandos,
                     or None if error or not found
    """
    try:
        response = requests.get(CONSIDERANDOS_API_URL)
        if response.status_code != 200:
            return None
        
        data = response.json()
        for item in data:
            if item.get('document_type') == document_type:
                # Return the item with considerandos data
                return item
                
        return None
    except Exception as e:
        print(f"Error fetching considerandos data: {str(e)}")
        return None

def get_departamento_heads_data():
    """
    Fetch departamento heads data from the API.
    
    Returns:
        list or None: List of departamento heads or None if error
    """
    try:
        response = requests.get(DEPTO_HEADS_API_URL)
        if response.status_code != 200:
            return None
        
        return response.json()
    except Exception as e:
        print(f"Error fetching departamento heads data: {str(e)}")
        return None

def get_asignaturas_from_external_api(departamento, area, orientacion_concurso):
    """
    Fetch and filter asignaturas from external API based on concurso criteria.
    
    Args:
        departamento (str): Department name to match
        area (str): Area name to match
        orientacion_concurso (str): Orientation from the concurso to match
    
    Returns:
        list: Filtered list of asignaturas matching the criteria
    """
    result = []
    
    try:
        # Log input parameters for debugging
        current_app.logger.info(f"Fetching asignaturas with parameters - departamento: '{departamento}', area: '{area}', orientacion: '{orientacion_concurso}'")
        
        # Authenticate and get response
        response = authenticate_catedras_api(ASIGNATURAS_API_URL)
        if not response:
            return []
        
        # Parse JSON response
        current_app.logger.info(f"Successfully authenticated to API. Content length: {len(response.text)}")
        asignaturas = response.json()
        current_app.logger.info(f"Received {len(asignaturas)} asignaturas from API")
        
        # Log a few sample items to verify structure
        if asignaturas and len(asignaturas) > 0:
            current_app.logger.info(f"Sample item from API: {str(asignaturas[0])[:500]}")
        
        # Normalize inputs for comparison
        departamento_norm = departamento.lower().strip() if departamento else ""
        area_norm = area.lower().strip() if area else ""
        orientacion_concurso_norm = orientacion_concurso.lower().strip() if orientacion_concurso else ""
        
        current_app.logger.info(f"Normalized search criteria - depto: '{departamento_norm}', area: '{area_norm}', orientacion: '{orientacion_concurso_norm}'")
        
        # Debug counter for filtered items
        skipped_optativa = 0
        skipped_depto_area = 0
        skipped_orientacion = 0
        matched_items = 0
        
        # Enable very verbose debugging if the list is empty or small
        verbose_debug = len(asignaturas) < 50
        
        # Filter asignaturas based on criteria
        for idx, asignatura in enumerate(asignaturas):
            # Extra verbose debugging for small result sets
            if verbose_debug:
                current_app.logger.info(f"Item {idx+1}: {asignatura}")
            
            # Regular debug for some items
            if matched_items < 2 and matched_items + skipped_optativa + skipped_depto_area + skipped_orientacion < 10:
                current_app.logger.info(f"Checking asignatura: {asignatura.get('nombre_materia', 'N/A')} - depto: '{asignatura.get('depto', 'N/A')}', "
                                      f"area: '{asignatura.get('area', 'N/A')}', orientacion: '{asignatura.get('orientacion', 'N/A')}', "
                                      f"optativa: '{asignatura.get('optativa', 'N/A')}'")
            
            # No longer skip optativa subjects
            optativa = asignatura.get('optativa', '').lower().strip()
            
            # Match departamento and area (case insensitive)
            depto_api = asignatura.get('depto', '').lower().strip()
            area_api = asignatura.get('area', '').lower().strip()
            
            # Function to normalize accents for comparison
            def normalize_text(text):
                return text.replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
            
            # Compare with normalized inputs, including accent-insensitive comparison
            depto_match = depto_api == departamento_norm
            
            # First try direct match for area
            area_match = area_api == area_norm
            
            # If direct match fails, try without accents
            if not area_match:
                area_match = normalize_text(area_api) == normalize_text(area_norm)
                if area_match:
                    current_app.logger.info(f"Area matched after accent normalization")
            
            # Log partial matches
            if matched_items < 1 and (depto_match or area_match):
                current_app.logger.info(f"Partial match found - depto_match: {depto_match}, area_match: {area_match}")
                current_app.logger.info(f"Comparing - API depto: '{depto_api}' vs input: '{departamento_norm}'")
                current_app.logger.info(f"Comparing - API area: '{area_api}' vs input: '{area_norm}'")
            
            if not depto_match or not area_match:
                skipped_depto_area += 1
                continue
            
            # Handle orientacion matching
            orientacion_api = asignatura.get('orientacion', '').lower().strip()
            
            # Debug orientacion matching
            current_app.logger.info(f"Matching orientacion: API='{orientacion_api}' vs Input='{orientacion_concurso_norm}'")
            
            # Special case: if input orientacion contains "orientacion", is empty, or is "sin orientacion"
            # then we should only match "sin orientación" in the API
            if (not orientacion_concurso_norm or
                "orientacion" in orientacion_concurso_norm or
                orientacion_concurso_norm == "sin orientacion"):
                    
                if "sin orientacion" not in orientacion_api and "sin orientación" not in orientacion_api:
                    skipped_orientacion += 1
                    continue
            # For specific orientations, check exact match or compare with normalized accents
            elif orientacion_api != orientacion_concurso_norm:
                # Try matching with normalized accents
                if normalize_text(orientacion_api) == normalize_text(orientacion_concurso_norm):
                    current_app.logger.info("Orientation matched after accent normalization")
                else:
                    skipped_orientacion += 1
                    continue
            
            matched_items += 1
            
            # Debug for matched items
            current_app.logger.info(f"Match found! - {asignatura.get('nombre_materia', 'N/A')}")
            
            # Extract relevant fields for the filtered asignatura - no programa data lookup for initial load
            result.append({
                'id_materia': asignatura.get('id_materia', ''),
                'nombre_carrera': asignatura.get('nombre_carrera', ''),
                'nombre_materia': asignatura.get('nombre_materia', ''),
                'contenidos_minimos': asignatura.get('contenidos_minimos', ''),
                'correlativas_para_cursar': asignatura.get('correlativas_para_cursar', ''),
                'correlativas_para_aprobar': asignatura.get('correlativas_para_aprobar', ''),
                'depto': asignatura.get('depto', ''),
                'area': asignatura.get('area', ''),
                'orientacion': asignatura.get('orientacion', ''),
                'optativa': asignatura.get('optativa', '').upper()
            })
        
        # Log filtering results
        current_app.logger.info(f"Filtering results - total: {len(asignaturas)}, "
                              f"skipped_optativa: {skipped_optativa}, "
                              f"skipped_depto_area: {skipped_depto_area}, "
                              f"skipped_orientacion: {skipped_orientacion}, "
                              f"matched: {len(result)}")
                                
        # Log a few results for validation
        for i, asig in enumerate(result[:3]):
            current_app.logger.info(f"Result {i+1}: {asig['nombre_materia']} ({asig['nombre_carrera']})")
    
    except requests.exceptions.Timeout:
        current_app.logger.error("Timeout while connecting to asignaturas API")
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Error connecting to asignaturas API: {str(e)}")
    except json.JSONDecodeError as e:
        current_app.logger.error(f"Invalid JSON response from asignaturas API: {str(e)}")
        if 'response' in locals():
            current_app.logger.error(f"Response content: {response.text[:500]}")
    except Exception as e:
        current_app.logger.error(f"Unexpected error fetching asignaturas: {str(e)}")
        import traceback
        current_app.logger.error(traceback.format_exc())
    
    return result

def authenticate_catedras_api(url):
    """
    Authenticate with the catedras API using multiple methods if needed.
    
    Args:
        url (str): The API URL to authenticate with
        
    Returns:
        response: The requests response object or None if authentication failed
    """
    session = requests.Session()
    
    try:
        # Method 1: Try Digest authentication
        current_app.logger.info(f"Trying authentication method 1: Digest auth for {url}")
        response = session.get(
            url, 
            auth=HTTPDigestAuth('usuario1', 'pdf'),
            timeout=15
        )
        
        # If first method fails, try Basic auth
        if response.status_code == 401:
            current_app.logger.info("Method 1 (Digest) failed with 401. Trying method 2: Basic auth")
            response = session.get(
                url, 
                auth=HTTPBasicAuth('usuario1', 'pdf'),
                timeout=15
            )
            
            # If Basic auth fails, try the Basic auth header approach
            if response.status_code == 401:
                current_app.logger.info("Method 2 (Basic) failed with 401. Trying method 3: Basic auth header")
                import base64
                auth_header = base64.b64encode(b'usuario1:pdf').decode('ascii')
                headers = {'Authorization': f'Basic {auth_header}'}
                
                response = session.get(
                    url,
                    headers=headers,
                    timeout=15
                )
        
        # Check response status
        if response.status_code != 200:
            current_app.logger.error(f"API returned status code {response.status_code}")
            current_app.logger.error(f"Response content: {response.text[:500]}")
            current_app.logger.error(f"Response headers: {response.headers}")
            return None
            
        return response
        
    except requests.exceptions.Timeout:
        current_app.logger.error(f"Timeout while connecting to API: {url}")
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Error connecting to API: {str(e)}")
    except Exception as e:
        current_app.logger.error(f"Unexpected error connecting to API: {str(e)}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        
    return None

def get_programa_by_id_materia(id_materia):
    """
    Fetch programa information for a specific materia from the API.
    
    Args:
        id_materia (int): The ID of the materia to fetch programa for
    
    Returns:
        dict: Dictionary with programa information or dict with not_found flag if no program exists,
              or None if error
    """
    try:
        current_app.logger.info(f"Fetching programa for materia ID: {id_materia}")
        
        # Use the new bulk fetching function with a single ID
        programas_map = get_programas_by_materia_ids([id_materia])
        
        if not programas_map:
            current_app.logger.warning(f"No response received from get_programas_by_materia_ids for ID {id_materia}")
            return {'status': 'error', 'message': 'Error fetching programa', 'id_materia': str(id_materia)}
        
        # Extract the programa for the requested ID
        id_materia_str = str(id_materia)
        programa = programas_map.get(id_materia_str)
        
        if not programa:
            current_app.logger.warning(f"No programa found in response for materia ID {id_materia}")
            return {'status': 'not_found', 'message': 'No programa found', 'id_materia': id_materia_str}
        
        # Check if the programa has a 'not_found' flag
        if programa.get('not_found'):
            current_app.logger.info(f"Programa marked as not found for materia ID {id_materia}: {programa.get('reason', 'unknown reason')}")
            return {'status': 'not_found', 'message': programa.get('reason', 'Programa not found'), 'id_materia': id_materia_str, 'manual_url': "https://huayca.crub.uncoma.edu.ar/programas/"}
        
        # Ensure id_programa exists
        if not programa.get('id_programa'):
            current_app.logger.warning(f"No id_programa found in programa for materia ID {id_materia}")
            return {'status': 'not_found', 'message': 'No id_programa found', 'id_materia': id_materia_str, 'manual_url': "https://huayca.crub.uncoma.edu.ar/programas/"}
        
        current_app.logger.info(f"Successfully retrieved programa for materia ID {id_materia} with id_programa: {programa.get('id_programa')}")
        
        # Add success status and download URL
        programa['status'] = 'success'
        programa['download_url'] = get_programa_download_url(programa.get('id_programa'))
        
        # Add the requested ID for verification
        programa['requested_id_materia'] = id_materia_str
        return programa
            
    except Exception as e:
        current_app.logger.error(f"Unexpected error in get_programa_by_id_materia: {str(e)}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return {'status': 'error', 'message': 'Unexpected error', 'id_materia': str(id_materia)}

def get_programas_by_materia_ids(materia_ids_list):
    """
    Fetch programa information for multiple materiasIDs in a single API call.
    
    Args:
        materia_ids_list (list): List of materia IDs to fetch programas for
    
    Returns:
        dict: Dictionary mapping each materia ID (as string) to its programa information
              or to a not_found entry if no programa exists
    """
    # Initialize the result dictionary
    final_result = {}
    
    # If the input list is empty, return an empty dictionary
    if not materia_ids_list or len(materia_ids_list) == 0:
        current_app.logger.info("Empty materia_ids_list provided to get_programas_by_materia_ids")
        return final_result
    
    try:
        # Convert all IDs to strings for consistent keying and URL parameter formatting
        materia_ids_str_list = [str(mid) for mid in materia_ids_list]
        
        # Construct the comma-separated string of IDs for the URL parameter
        ids_param = ",".join(materia_ids_str_list)
        
        # Construct the URL with the ids_materia parameter
        url = f"{PROGRAMAS_API_URL}?ids_materia={ids_param}"
        current_app.logger.info(f"Fetching programas with URL: {url}")
        
        # Use the existing authentication function to make the API call
        response = authenticate_catedras_api(url)
        
        # If the API call failed, return a dictionary with not_found entries for all IDs
        if not response:
            current_app.logger.error(f"Failed to authenticate to programas API for IDs: {ids_param}")
            return {mid: {'not_found': True, 'id_materia': mid, 'error': 'api_call_failed'} 
                    for mid in materia_ids_str_list}
        
        # Parse the JSON response (should be a list of programa objects)
        programas_list = response.json()
        current_app.logger.info(f"Received {len(programas_list)} programas from API for {len(materia_ids_str_list)} requested IDs")
        
        # Transform the API response list into a dictionary with materia_id as keys
        programas_map = {}
        for programa in programas_list:
            # Extract the materia ID and ensure it's a string for consistent dictionary keying
            id_materia = str(programa.get('id_materia'))
            if not id_materia:
                # Try alternative field names if id_materia not found
                for field in ['id_materia', 'materia_id', 'id_materia_prog']:
                    if programa.get(field):
                        id_materia = str(programa.get(field))
                        current_app.logger.info(f"Found materia ID in alternative field: {field} = {id_materia}")
                        break
            
            if not id_materia:
                current_app.logger.warning(f"Received programa without id_materia field: {programa}")
                continue
            
            # Ensure each program has an id_programa field
            id_programa = programa.get('id_programa')
            if not id_programa:
                # Try alternative field names if id_programa not found
                for field in ['id_programa', 'programa_id', 'id', 'id_prog']:
                    if programa.get(field):
                        id_programa = programa.get(field)
                        current_app.logger.info(f"Found program ID in alternative field: {field} = {id_programa}")
                        programa['id_programa'] = id_programa  # Store it under the standard key
                        break
            
            # Add the programa to the map
            programas_map[id_materia] = programa
        
        # Construct the final result dictionary based on the original input list
        for mid in materia_ids_str_list:
            if mid in programas_map:
                programa = programas_map[mid]
                # Check if the programa has a valid id_programa
                if programa.get('id_programa'):
                    final_result[mid] = programa
                else:
                    # Programa exists but has no id_programa
                    final_result[mid] = {
                        'not_found': True, 
                        'id_materia': mid, 
                        'reason': 'no_id_programa_field'
                    }
            else:
                # No programa found for this materia ID
                final_result[mid] = {
                    'not_found': True, 
                    'id_materia': mid, 
                    'reason': 'not_returned_by_api'
                }
        
        return final_result
    except requests.exceptions.Timeout:
        current_app.logger.error(f"Timeout while connecting to programas API for IDs: {ids_param if 'ids_param' in locals() else materia_ids_list}")
        # Check if materia_ids_str_list exists, otherwise use the original list
        id_list = materia_ids_str_list if 'materia_ids_str_list' in locals() else materia_ids_list
        return {str(mid): {'not_found': True, 'id_materia': str(mid), 'error': 'api_timeout'} 
                for mid in id_list}
                
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Error connecting to programas API: {str(e)}")
        # Check if materia_ids_str_list exists, otherwise use the original list
        id_list = materia_ids_str_list if 'materia_ids_str_list' in locals() else materia_ids_list
        return {str(mid): {'not_found': True, 'id_materia': str(mid), 'error': 'request_exception'} 
                for mid in id_list}
                
    except json.JSONDecodeError as e:
        current_app.logger.error(f"Invalid JSON response from programas API: {str(e)}")
        if 'response' in locals():
            current_app.logger.error(f"Response content: {response.text[:500]}")
        # Check if materia_ids_str_list exists, otherwise use the original list
        id_list = materia_ids_str_list if 'materia_ids_str_list' in locals() else materia_ids_list
        return {str(mid): {'not_found': True, 'id_materia': str(mid), 'error': 'invalid_json'} 
                for mid in id_list}
    except Exception as e:
        current_app.logger.error(f"Unexpected error fetching programas: {str(e)}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        # Check if materia_ids_str_list exists, otherwise use the original list
        id_list = materia_ids_str_list if 'materia_ids_str_list' in locals() else materia_ids_list
        return {str(mid): {'not_found': True, 'id_materia': str(mid), 'error': 'unexpected_error'} 
                for mid in id_list}

def get_programa_download_url(id_programa):
    """
    Get the URL to download a programa file.
    
    Args:
        id_programa (int): The ID of the programa to download
    
    Returns:
        str: The URL to download the programa file
    """
    return PROGRAMA_DOWNLOAD_URL.format(id_programa=id_programa)