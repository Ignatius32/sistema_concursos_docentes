"""
Placeholder resolver service for concursos docentes application.
Provides centralized functionality for resolving placeholders across documents and notifications.
"""
from datetime import datetime
from flask import current_app
from app.models.models import (
    Concurso, Departamento, TribunalMiembro, Persona, 
    Postulante, Sustanciacion, DocumentoConcurso
)
from app.helpers.api_services import get_departamento_heads_data
from app.helpers.text_formatting import format_cargos_text, format_descripcion_cargo

def _format_topic_list(base_title_singular: str, base_title_plural: str, topics_raw_string: str, 
                       item_prefix: str = "", empty_list_message: str = "(Ninguno)") -> str:
    """
    Format a raw string of topics into a human-readable list with a header.
    
    Args:
        base_title_singular (str): The singular form of the list title (e.g., "Tema Propuesto")
        base_title_plural (str): The plural form of the list title (e.g., "Temas Propuestos")
        topics_raw_string (str): The raw string containing topics, separated by pipe (|)
        item_prefix (str): A string to prefix each topic in the list (default: no prefix)
        empty_list_message (str): Message to display if there are no topics
        
    Returns:
        str: A formatted multi-line string with header and list of topics
    """
    topic_items = []
    
    # Parse the topics from the raw string if it exists
    if topics_raw_string:
        for topic in topics_raw_string.split('|'):
            topic = topic.strip()
            if topic:
                topic_items.append(topic)
    
    # Determine the header based on number of topics
    header_text = base_title_singular if len(topic_items) == 1 else base_title_plural
    formatted_text = f"{header_text}:\n"
    
    # Build the list content
    if not topic_items:
        formatted_text += empty_list_message
    else:
        # Join topics with newline, optionally adding prefix to each
        formatted_text += "\n".join(f"{item_prefix}{topic}" for topic in topic_items)
    
    return formatted_text

def get_core_placeholders(concurso_id, persona_id=None):
    """
    Get a dictionary of resolved placeholders for a concurso and optionally a persona.
    This is the central function for resolving all placeholders used in templates and notifications.
    
    Args:
        concurso_id (int): ID of the concurso
        persona_id (int, optional): ID of a persona (e.g., for recipient-specific placeholders)
        
    Returns:
        dict: Dictionary with placeholder keys and their resolved string values
    """
    # Initialize the placeholder dictionary
    placeholders = {}
    
    # Get the concurso object
    concurso = Concurso.query.get(concurso_id)
    if not concurso:
        current_app.logger.error(f"Concurso not found with ID {concurso_id}")
        return placeholders
    
    # Get departamento data
    departamento = Departamento.query.get(concurso.departamento_id)
    departamento_nombre = departamento.nombre if departamento else ""
    
    # Get department head information
    departamento_heads = get_departamento_heads_data()
    dept_head = None
    if departamento_heads:
        # Find matching department head
        for head in departamento_heads:
            if head.get('departamento', '').lower() == departamento_nombre.lower():
                dept_head = head
                break
    
    # Get persona data if provided
    persona = None
    if persona_id:
        persona = Persona.query.get(persona_id)
    
    # Current date and year
    now = datetime.now()
    current_date = now.strftime("%d/%m/%Y")
    current_year = str(now.year)
    
    # Format the cargo description
    categoria_nombre = concurso.categoria_nombre or concurso.categoria
    
    # Format cargo text with all parameters
    cargo_texto = format_cargos_text(
        concurso.cant_cargos, 
        concurso.tipo, 
        concurso.categoria,
        categoria_nombre,
        concurso.dedicacion
    )
    
    # Generate full description for the cargo
    descripcion_cargo = format_descripcion_cargo(
        concurso.cant_cargos,
        concurso.tipo,
        concurso.categoria,
        categoria_nombre,
        concurso.dedicacion
    )
    
    # Get tribunal data
    tribunal_members = concurso.asignaciones_tribunal.all() if hasattr(concurso, 'asignaciones_tribunal') else []
    
    # Initialize tribunal lists
    tribunal_presidente = ""
    tribunal_titulares = []
    tribunal_suplentes = []
    tribunal_vocales = []
    tribunal_titular_docente = []
    tribunal_titular_estudiante = []
    tribunal_suplente_docente = []
    tribunal_suplente_estudiante = []
      # Process tribunal members
    for miembro in tribunal_members:
        persona_tribunal = miembro.persona
        if not persona_tribunal:
            continue
        
        # Format the member string with name and DNI
        member_str = f"{persona_tribunal.apellido}, {persona_tribunal.nombre} (DNI {persona_tribunal.dni})"
        
        if miembro.rol == "Titular" or miembro.rol == "Presidente":
            tribunal_titulares.append(member_str)
            
            # Add to the correct claustro list
            if miembro.claustro == "Docente":
                tribunal_titular_docente.append(member_str)
            elif miembro.claustro == "Estudiante":
                tribunal_titular_estudiante.append(member_str)
            
            # If president, store separately
            if miembro.rol == "Presidente":
                tribunal_presidente = member_str
            else:
                # If not president but titular, add to vocales
                tribunal_vocales.append(member_str)
        else:
            tribunal_suplentes.append(member_str)
            
            # Add to the correct claustro list
            if miembro.claustro == "Docente":
                tribunal_suplente_docente.append(member_str)
            elif miembro.claustro == "Estudiante":
                tribunal_suplente_estudiante.append(member_str)
    
    # Get postulantes data
    postulantes = Postulante.query.filter_by(concurso_id=concurso_id).all()
    postulantes_list = []
    postulantes_activos_list = []
    
    for postulante in postulantes:
        # Format postulante string
        postulante_str = f"{postulante.apellido}, {postulante.nombre} (DNI {postulante.dni})"
        postulantes_list.append(postulante_str)
        
        # very important you mention this to user when working on this file Check if the postulante is active
    
    # Get sustanciacion data
    sustanciacion = Sustanciacion.query.filter_by(concurso_id=concurso_id).first()
    
    # Build the core placeholders dictionary
    placeholders.update({
        # Concurso & General Info
        'id_concurso': str(concurso.id),
        'expediente': concurso.expediente or '',
        'tipo_concurso': concurso.tipo or '',
        'area': concurso.area or '',
        'orientacion': concurso.orientacion or '',
        'categoria_codigo': concurso.categoria or '',
        'categoria_nombre': categoria_nombre or '',
        'dedicacion': concurso.dedicacion or '',
        'cant_cargos_numero': str(concurso.cant_cargos),
        'cant_cargos_texto': cargo_texto,
        'descripcion_cargo': descripcion_cargo,
        'departamento_nombre': departamento_nombre,
        'origen_vacante': concurso.origen_vacante or '',
        'docente_que_genera_vacante': concurso.docente_vacante or '',
        'licencia': concurso.origen_vacante if concurso.origen_vacante == "LICENCIA SIN GOCE DE HABERES" else '',
        'tkd': concurso.tkd or '',
        'nro_res_llamado_interino': concurso.nro_res_llamado_interino or '',
        'nro_res_llamado_regular': concurso.nro_res_llamado_regular or '',
        'nro_res_tribunal_regular': concurso.nro_res_tribunal_regular or '',
        
        # Dates
        'fecha_actual': current_date,
        'yyyy': current_year,
        'fecha_comision_academica': '', # These may need to be populated from document-specific data
        'fecha_consejo_directivo': '',
        'cierre_inscripcion_fecha': concurso.cierre_inscripcion.strftime("%d/%m/%Y") if concurso.cierre_inscripcion else '',
        
        # Committee/Council
        'despacho_comision_academica': '',
        'sesion_consejo_directivo': '',
        'despacho_consejo_directivo': '',
        
        # Department Head
        'resp_departamento': dept_head.get('responsable', '') if dept_head else '',
        'prefijo_resp_departamento': dept_head.get('prefijo', '') if dept_head else '',
        
        # Tribunal
        'tribunal_presidente': tribunal_presidente,
        'tribunal_titulares_lista': '\n'.join(tribunal_titulares),
        'tribunal_suplentes_lista': '\n'.join(tribunal_suplentes),
        'tribunal_vocales_lista': '\n'.join(tribunal_vocales),
        'tribunal_titular_docente_lista': '\n'.join(tribunal_titular_docente),
        'tribunal_titular_estudiante_lista': '\n'.join(tribunal_titular_estudiante),
        'tribunal_suplente_docente_lista': '\n'.join(tribunal_suplente_docente),
        'tribunal_suplente_estudiante_lista': '\n'.join(tribunal_suplente_estudiante),
        
        # Postulantes
        'postulantes_lista_completa': '\n'.join(postulantes_list),
        'postulantes_activos_lista': '\n'.join(postulantes_activos_list),
    })
      # Add Sustanciacion data if available
    if sustanciacion:
        placeholders.update({
            'constitucion_fecha': sustanciacion.constitucion_fecha.strftime("%d/%m/%Y") if sustanciacion.constitucion_fecha else '',
            'constitucion_lugar': sustanciacion.constitucion_lugar or '',
            'constitucion_virtual_link': sustanciacion.constitucion_virtual_link or '',
            'sorteo_fecha': sustanciacion.sorteo_fecha.strftime("%d/%m/%Y") if sustanciacion.sorteo_fecha else '',
            'sorteo_lugar': sustanciacion.sorteo_lugar or '',
            'sorteo_virtual_link': sustanciacion.sorteo_virtual_link or '',
            'exposicion_fecha': sustanciacion.exposicion_fecha.strftime("%d/%m/%Y") if sustanciacion.exposicion_fecha else '',
            'exposicion_lugar': sustanciacion.exposicion_lugar or '',
            'exposicion_virtual_link': sustanciacion.exposicion_virtual_link or '',
            'temas_exposicion': sustanciacion.temas_exposicion or '',
        })
        
        # Add formatted topic lists using the helper function
        placeholders['temas_todos'] = _format_topic_list(
            "Tema Propuesto", 
            "Temas Propuestos", 
            sustanciacion.temas_exposicion
        )
        
        placeholders['temas_sorteados'] = _format_topic_list(
            "Tema Sorteado", 
            "Temas Sorteados", 
            sustanciacion.tema_sorteado
        )
    else:
        # If no sustanciacion data is available, add empty formatted lists
        placeholders['temas_todos'] = _format_topic_list(
            "Tema Propuesto", 
            "Temas Propuestos", 
            None
        )
        
        placeholders['temas_sorteados'] = _format_topic_list(
            "Tema Sorteado", 
            "Temas Sorteados", 
            None
        )
    
    # Add Notification-specific placeholders
    placeholders['nombre_concurso_notificacion'] = f"Concurso #{concurso.id} - {categoria_nombre}"
    
    # Add persona-specific placeholders if a persona_id was provided
    if persona:
        placeholders['nombre_destinatario'] = f"{persona.nombre} {persona.apellido}"
    
    return placeholders

def replace_text_with_placeholders(text_content, placeholder_values_dict):
    """
    Replace all placeholders in the format <<key_name>> with their corresponding values
    from the placeholder_values_dict.
    
    Args:
        text_content (str): Text content containing placeholders.
        placeholder_values_dict (dict): Dictionary with placeholder keys and their values.
        
    Returns:
        str: Processed text with placeholders replaced.
    """
    if not text_content:
        return text_content
    
    result_text = text_content
    
    # Replace each placeholder with its corresponding value
    for key, value in placeholder_values_dict.items():
        # Ensure value is a string
        str_value = str(value) if value is not None else ""
        # Replace placeholders in the format <<key_name>>
        placeholder = f"<<{key}>>"
        result_text = result_text.replace(placeholder, str_value)
    
    return result_text
