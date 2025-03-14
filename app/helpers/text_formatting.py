"""
Text formatting utilities for concursos docentes application.
Contains functions for formatting text descriptions of positions and other fields.
"""

def format_cargos_text(cant_cargos, tipo, categoria=None, categoria_nombre=None, dedicacion=None):
    """
    Format the cargo count text with number in words and proper pluralization.
    
    Args:
        cant_cargos (int): Number of positions
        tipo (str): Type of position (Regular/Interino)
        categoria (str, optional): Category code (e.g. PAD)
        categoria_nombre (str, optional): Full category name (e.g. Profesor Adjunto)
        dedicacion (str, optional): Dedication level (Simple/Parcial/Exclusiva)
        
    Returns:
        str: Formatted cargo count text
    """
    # Format the cargo count with number in words
    numeros_texto = {
        1: "un",
        2: "dos",
        3: "tres",
        4: "cuatro",
        5: "cinco",
        6: "seis",
        7: "siete",
        8: "ocho",
        9: "nueve",
        10: "diez"
    }
    
    numero = numeros_texto.get(cant_cargos, str(cant_cargos))
    
    # Pluralize cargo if needed
    cargo_text = "cargo" if cant_cargos == 1 else "cargos"
    
    # Format the position type (interino/regular)
    tipo_text = "interino" if tipo == "Interino" else "regular"
    tipo_text = tipo_text if cant_cargos == 1 else tipo_text + ("es" if tipo == "Regular" else "s")
    
    # Basic format if no category or dedication provided
    if not categoria or not categoria_nombre or not dedicacion:
        return f"{numero} ({cant_cargos}) {cargo_text} {tipo_text}"
    
    # Get dedication code if full information is provided
    dedicacion_code = "1"  # Default: Simple
    if dedicacion == "Parcial":
        dedicacion_code = "2"
    elif dedicacion == "Exclusiva":
        dedicacion_code = "3"
    
    # Full format with category and dedication
    return f"{numero} ({cant_cargos}) {cargo_text} {tipo_text} de {categoria_nombre} con dedicación {dedicacion.lower()} ({categoria}-{dedicacion_code})"

def format_descripcion_cargo(cant_cargos, tipo, categoria, categoria_nombre, dedicacion):
    """
    Format a complete cargo description for considerandos.
    
    Args:
        cant_cargos (int): Number of positions
        tipo (str): Type of position (Regular/Interino)
        categoria (str): Category code (e.g. PAD)
        categoria_nombre (str): Full category name (e.g. Profesor Adjunto)
        dedicacion (str): Dedication level (Simple/Parcial/Exclusiva)
    
    Returns:
        str: Formatted cargo description
    """
    # Format the cargo count with number in words
    numeros_texto = {
        1: "un",
        2: "dos",
        3: "tres",
        4: "cuatro",
        5: "cinco",
        6: "seis",
        7: "siete",
        8: "ocho",
        9: "nueve",
        10: "diez"
    }
    
    numero = numeros_texto.get(cant_cargos, str(cant_cargos))
    
    # Pluralize cargo if needed
    cargo_text = "cargo" if cant_cargos == 1 else "cargos"
    
    # Format the position type (interino/regular)
    tipo_text = "interino" if tipo == "Interino" else "regular"
    tipo_text = tipo_text if cant_cargos == 1 else tipo_text + ("es" if tipo == "Regular" else "s")
    
    # Get dedication code
    dedicacion_code = "1"  # Default: Simple
    if dedicacion == "Parcial":
        dedicacion_code = "2"
    elif dedicacion == "Exclusiva":
        dedicacion_code = "3"
        
    # Format the full description with the full category name first, then code in parentheses
    return f"{numero} {cargo_text} ({cant_cargos}) {tipo_text} de {categoria_nombre} con dedicación {dedicacion.lower()} ({categoria}-{dedicacion_code})"