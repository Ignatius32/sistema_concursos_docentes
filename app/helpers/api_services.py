"""
API service utilities for external API interactions.
Contains functions for fetching data from external APIs used in the application.
"""
import requests

# URL to fetch considerandos options
CONSIDERANDOS_API_URL = "https://script.google.com/macros/s/AKfycbz48ziHckZ-Ir6_gmXnUZF_S42AapQLnvpjktJXTnSbD1ps1lWimgkrxTzLXyiH_Eorlw/exec"
# URL to fetch departamento heads data
DEPTO_HEADS_API_URL = "https://script.google.com/macros/s/AKfycbyWU4h92lRGefLzLRSS82JhytafKIZl0jey3DuuoiCUicQcVf_1u1vzZzx7mI-0HTOg4w/exec"

def get_considerandos_data(document_type, tipo_concurso=None):
    """
    Fetch considerandos data from the API for a specific document type.
    
    Args:
        document_type (str): Type of document to get considerandos for (e.g., 'RESOLUCION_LLAMADO_TRIBUNAL', 'RESOLUCION_LLAMADO_REGULAR')
        tipo_concurso (str, optional): Type of concurso ('INTERINO' or 'REGULAR') to check visibility
    
    Returns:
        dict or None: Dictionary with document information including considerandos, visibility, and uniqueness,
                     or None if error or not found
    """
    try:
        response = requests.get(CONSIDERANDOS_API_URL)
        if response.status_code != 200:
            return None
        
        data = response.json()
        for item in data:
            if item.get('document_type') == document_type:
                # If no visibility is specified, or tipo_concurso is not provided, 
                # return the item regardless of concurso type
                if not tipo_concurso or 'visibility' not in item or not item.get('visibility'):
                    return item
                
                # Get visibility values and normalize them
                visibility_values = [v.strip().lower() for v in item.get('visibility', '').split(',')]
                tipo = tipo_concurso.strip().lower()
                
                print(f"Document type: {document_type}")
                print(f"Visibility from API: '{visibility_values}'")
                print(f"Tipo concurso: '{tipo}'")
                
                # If 'both' is in visibility values, return the item
                if 'both' in visibility_values:
                    print(f"Visibility match: 'both' allows access to both types")
                    return item
                
                # Special handling for regular/interino
                if ('regular' in visibility_values and tipo in ('regular', 'ordinario')) or \
                   ('interino' in visibility_values and tipo in ('interino', 'suplente')):
                    print(f"Visibility match: '{visibility_values}' matches '{tipo}'")
                    return item
                else:
                    print(f"Visibility mismatch: '{visibility_values}' doesn't match '{tipo}'")
                    return None
                
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