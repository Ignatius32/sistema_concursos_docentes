from flask import Blueprint, render_template, redirect, url_for, request
from app.models.models import Concurso, Categoria
from app.helpers.api_services import get_asignaturas_from_external_api

# Create public blueprint
public = Blueprint('public', __name__, url_prefix='')

@public.route('/')
def index():
    """Display list of all active concursos for public viewing."""
    # Get all concursos ordered by creation date
    concursos_list = Concurso.query.order_by(Concurso.creado.desc()).all()
    return render_template('public/index.html', concursos=concursos_list)

@public.route('/concurso/<int:concurso_id>')
def ver_concurso(concurso_id):
    """Display details of a specific concurso for public viewing, including instructivos."""
    concurso = Concurso.query.get_or_404(concurso_id)
    
    # Get the categoria to access instructivos
    categoria = Categoria.query.filter_by(codigo=concurso.categoria).first()
    instructivo = None
    
    if categoria and categoria.instructivo_postulantes:
        # Build the complete instructivo text based on dedicacion
        base_instructivo = categoria.instructivo_postulantes.get('base', '')
        dedicacion_instructivo = categoria.instructivo_postulantes.get('porDedicacion', {}).get(concurso.dedicacion, '')
        
        instructivo = {
            'base': base_instructivo,
            'dedicacion': dedicacion_instructivo
        }
    
    # Get asignaturas from external API based on concurso criteria
    asignaturas_externas = []
    if concurso.departamento_rel:
        asignaturas_externas = get_asignaturas_from_external_api(
            departamento=concurso.departamento_rel.nombre,
            area=concurso.area,
            orientacion_concurso=concurso.orientacion
        )
    
    return render_template('public/detalle_concurso.html', 
                          concurso=concurso, 
                          instructivo=instructivo,
                          asignaturas_externas=asignaturas_externas)
