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