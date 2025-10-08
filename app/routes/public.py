from flask import Blueprint, render_template, redirect, url_for, request, Response, send_file
from app.models.models import Concurso, Categoria, Departamento, DocumentoConcurso
from app.helpers.api_services import get_asignaturas_from_external_api
from app.integrations.google_drive import GoogleDriveAPI
from app.helpers.pdf_utils import generate_formulario_inscripcion_pdf
from app.services.placeholder_resolver import get_core_placeholders
import requests
import base64
import io
import logging

# Set up logger
logger = logging.getLogger(__name__)

# Create public blueprint
public = Blueprint('public', __name__, url_prefix='')
drive_api = GoogleDriveAPI()

@public.route('/')
def index():
    """Display list of all active concursos for public viewing with filtering."""
    from datetime import date, datetime, timezone, timedelta
    
    # Get Argentina timezone (UTC-3)
    argentina_offset = timedelta(hours=-3)
    argentina_tz = timezone(argentina_offset)
    today = datetime.now(argentina_tz).date()
    
    # Get filter parameters from request
    departamento_filter = request.args.get('departamento', '')
    estado_filter = request.args.get('estado', '')
    
    # Base query - hide only INICIO, CREADO, and DESPUBLICAR estados from public
    hidden_estados = ['INICIO', 'CREADO', 'DESPUBLICAR']
    query = Concurso.query.filter(~Concurso.estado_actual.in_(hidden_estados))
    
    # Apply departamento filter if provided
    if departamento_filter:
        query = query.filter(Concurso.departamento_id == departamento_filter)
    
    # Get all concursos first to apply dynamic estado logic
    concursos_list = query.order_by(Concurso.creado.desc()).all()
    
    # Apply dynamic estado logic based on cierre_inscripcion date and current estado
    for concurso in concursos_list:
        if concurso.estado_actual == 'FINALIZADO':
            concurso.dynamic_estado = 'FINALIZADO'
        elif concurso.cierre_inscripcion:
            if concurso.cierre_inscripcion <= today:
                concurso.dynamic_estado = 'INSCRIPCIÓN CERRADA'
            else:
                concurso.dynamic_estado = 'INSCRIPCIÓN ABIERTA'
        else:
            # If no cierre_inscripcion date, default to INSCRIPCIÓN ABIERTA
            concurso.dynamic_estado = 'INSCRIPCIÓN ABIERTA'
    
    # Apply estado filter after dynamic estado calculation
    if estado_filter:
        concursos_list = [c for c in concursos_list if c.dynamic_estado == estado_filter]
    
    # Get all departamentos for the filter dropdown
    departamentos = Departamento.query.order_by(Departamento.nombre).all()
    
    # Available estados for filtering - only the dynamic ones
    estados_disponibles = ['INSCRIPCIÓN ABIERTA', 'INSCRIPCIÓN CERRADA', 'FINALIZADO']
    
    return render_template('public/index.html', 
                         concursos=concursos_list,
                         departamentos=departamentos,
                         estados_disponibles=estados_disponibles,
                         departamento_filter=departamento_filter,
                         estado_filter=estado_filter)

@public.route('/concurso/<int:concurso_id>')
def ver_concurso(concurso_id):
    """Display details of a specific concurso for public viewing, including instructivos."""
    from datetime import date
    
    concurso = Concurso.query.get_or_404(concurso_id)
    
    # Only allow public viewing of concursos (hide only INICIO, CREADO, and DESPUBLICAR)
    hidden_estados = ['INICIO', 'CREADO', 'DESPUBLICAR']
    if concurso.estado_actual in hidden_estados:
        return "Concurso no disponible para visualización pública", 404
    
    # Resolve instructivo via service with concurso tipo awareness
    from app.services.instructivo_service import instructivo_service
    categoria = Categoria.query.filter_by(codigo=concurso.categoria).first()
    instructivo = instructivo_service.get_structured_postulantes(concurso)
    # Legacy fallback if service returns nothing
    if (not instructivo) and categoria and categoria.instructivo_postulantes:
        base_instructivo = categoria.instructivo_postulantes.get('base', '')
        dedicacion_instructivo = categoria.instructivo_postulantes.get('porDedicacion', {}).get(concurso.dedicacion, '')
        instructivo = {'base': base_instructivo, 'dedicacion': dedicacion_instructivo}
    
    # Get documents visible to public
    all_documents = DocumentoConcurso.query.filter_by(concurso_id=concurso_id).all()
    public_documents = [doc for doc in all_documents if doc.is_visible_to_public()]
    
    # Get asignaturas from external API based on concurso criteria
    asignaturas_externas = []
    if concurso.departamento_rel:
        asignaturas_externas = get_asignaturas_from_external_api(
            departamento=concurso.departamento_rel.nombre,
            area=concurso.area,
            orientacion_concurso=concurso.orientacion
        )
    
    # Check if registration is closed (using Argentina timezone and FINALIZADO estado)
    from datetime import datetime, timezone, timedelta
    
    # Get Argentina timezone (UTC-3)
    argentina_offset = timedelta(hours=-3)
    argentina_tz = timezone(argentina_offset)
    today = datetime.now(argentina_tz).date()
    
    # Registration is closed if:
    # 1. Estado is FINALIZADO, or
    # 2. cierre_inscripcion date has passed
    is_registration_closed = (
        concurso.estado_actual == 'FINALIZADO' or 
        (concurso.cierre_inscripcion and concurso.cierre_inscripcion <= today)
    )
    
    return render_template('public/detalle_concurso.html', 
                          concurso=concurso, 
                          instructivo=instructivo,
                          asignaturas_externas=asignaturas_externas,
                          public_documents=public_documents,
                          is_registration_closed=is_registration_closed,
                          today=today)

@public.route('/concurso/<int:concurso_id>/documento/<int:documento_id>')
def ver_documento_publico(concurso_id, documento_id):
    """View a public document (PDF) in embedded viewer."""
    try:
        # Verify the concurso exists and is public
        concurso = Concurso.query.get_or_404(concurso_id)
        hidden_estados = ['INICIO', 'CREADO', 'DESPUBLICAR']
        if concurso.estado_actual in hidden_estados:
            return "Documento no disponible", 404
        
        # Get the document and verify it's visible to public
        documento = DocumentoConcurso.query.filter_by(
            id=documento_id, 
            concurso_id=concurso_id
        ).first_or_404()
        
        if not documento.is_visible_to_public():
            return "Documento no disponible para visualización pública", 403
        
        # Get correct file_id based on document state
        if documento.estado in ['PENDIENTE_DE_FIRMA', 'FIRMADO'] and documento.file_id:
            file_id = documento.file_id  # Use the signed/uploaded version
        elif documento.drive_file_id:
            file_id = documento.drive_file_id  # Use drive_file_id if available
        else:
            file_id = documento.borrador_file_id  # Use the draft version
            
        if not file_id:
            return "Documento no disponible", 404
            
        # Get file content from Drive using the same method as tribunal
        file_content_response = drive_api.get_file_content(file_id)
        if not file_content_response.get('fileData'):
            return "No se pudo obtener el contenido del archivo", 500
            
        # Decode base64 content
        pdf_content = base64.b64decode(file_content_response['fileData'])
        
        # Return the PDF content with proper headers
        return send_file(
            io.BytesIO(pdf_content),
            mimetype='application/pdf',
            as_attachment=False,
            download_name=f"{documento.get_friendly_name()}.pdf"
        )
        
    except Exception as e:
        return f"Error al obtener el documento: {str(e)}", 500

@public.route('/concurso/<int:concurso_id>/documento/<int:documento_id>/descargar')
def descargar_documento_publico(concurso_id, documento_id):
    """Download a public document (PDF) as attachment."""
    try:
        # Verify the concurso exists and is public
        concurso = Concurso.query.get_or_404(concurso_id)
        hidden_estados = ['INICIO', 'CREADO', 'DESPUBLICAR']
        if concurso.estado_actual in hidden_estados:
            return "Documento no disponible", 404
        
        # Get the document and verify it's visible to public
        documento = DocumentoConcurso.query.filter_by(
            id=documento_id, 
            concurso_id=concurso_id
        ).first_or_404()
        
        if not documento.is_visible_to_public():
            return "Documento no disponible para visualización pública", 403
        
        # Get correct file_id based on document state
        if documento.estado in ['PENDIENTE_DE_FIRMA', 'FIRMADO'] and documento.file_id:
            file_id = documento.file_id  # Use the signed/uploaded version
        elif documento.drive_file_id:
            file_id = documento.drive_file_id  # Use drive_file_id if available
        else:
            file_id = documento.borrador_file_id  # Use the draft version
            
        if not file_id:
            return "Documento no disponible", 404
            
        # Get file content from Drive using the same method as tribunal
        file_content_response = drive_api.get_file_content(file_id)
        if not file_content_response.get('fileData'):
            return "No se pudo obtener el contenido del archivo", 500
            
        # Decode base64 content
        pdf_content = base64.b64decode(file_content_response['fileData'])
        
        # Return the PDF content with download headers
        return send_file(
            io.BytesIO(pdf_content),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f"{documento.get_friendly_name()}.pdf"
        )
        
    except Exception as e:
        return f"Error al descargar el documento: {str(e)}", 500

@public.route('/concurso/<int:concurso_id>/formulario-inscripcion')
def descargar_formulario_inscripcion(concurso_id):
    """Generate and download the inscription form PDF for a specific concurso."""
    try:
        # Verify the concurso exists and is public
        concurso = Concurso.query.get_or_404(concurso_id)
        hidden_estados = ['INICIO', 'CREADO', 'DESPUBLICAR']
        if concurso.estado_actual in hidden_estados:
            return "Formulario no disponible", 404
        
        # Get placeholders for this concurso
        placeholders = get_core_placeholders(concurso_id)
        
        # Generate the PDF
        pdf_content = generate_formulario_inscripcion_pdf(concurso, placeholders)
        
        if not pdf_content:
            return "Error al generar el formulario", 500
        
        # Create detailed filename with sanitized names
        def sanitize_filename(text):
            """Sanitize text for use in filename"""
            import re
            import unicodedata
            # Remove accents and normalize unicode
            text = unicodedata.normalize('NFD', text)
            text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')
            # Replace spaces and special characters with underscores
            sanitized = re.sub(r'[^\w\s-]', '', text)
            sanitized = re.sub(r'[-\s]+', '_', sanitized)
            # Limit length and clean up
            sanitized = sanitized.strip('_')[:20]  # Limit each part to 20 chars
            return sanitized
        
        # Build detailed filename
        departamento_name = sanitize_filename(concurso.departamento_rel.nombre) if concurso.departamento_rel else "Sin_Depto"
        area_name = sanitize_filename(concurso.area or "Sin_Area")
        orientacion_name = sanitize_filename(concurso.orientacion or "Sin_Orientacion")
        categoria_name = sanitize_filename(concurso.categoria or "Sin_Categoria")

        filename = f"Solicitud_Inscripcion_Declaracion_Jurada_C{concurso.id}_{departamento_name}_{area_name}_{orientacion_name}_{categoria_name}.pdf"

        # Return the PDF as a downloadable file with proper headers
        response = Response(
            pdf_content,
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Content-Type': 'application/pdf',
                'Content-Length': str(len(pdf_content)),
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            }
        )
        return response
        
    except Exception as e:
        logger.error(f"Error generating inscription form: {str(e)}")
        return f"Error al generar el formulario: {str(e)}", 500
