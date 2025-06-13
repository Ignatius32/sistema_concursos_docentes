"""
Routes for sorteo configuration management in the admin area.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.utils.keycloak_auth import keycloak_login_required, admin_required
from app.models.models import db, SorteoConfig, Categoria

# Create Blueprint
admin_sorteo_config_bp = Blueprint('admin_sorteo_config', __name__, url_prefix='/admin/sorteo-config')

# Access control is now handled by keycloak_auth decorators

@admin_sorteo_config_bp.route('/', methods=['GET', 'POST'])
@keycloak_login_required
@admin_required
def index():
    """Configure the number of temas to draw for each categoria and concurso tipo"""
    # Get all categorias
    categorias = Categoria.query.all()
      # Get existing configurations
    configs = SorteoConfig.query.all()
    
    # Create a dictionary for easy lookup in the template
    config_dict = {}
    for config in configs:
        key = f"{config.concurso_tipo}_{config.categoria_codigo}"
        config_dict[key] = config.numero_temas_sorteados
    
    if request.method == 'POST':
        try:
            # Process each categoria for both Regular and Interino tipos
            for categoria in categorias:
                for tipo in ['REGULAR', 'INTERINO']:                    # Get the form field value
                    field_name = f"{tipo.lower()}_{categoria.codigo}"
                    num_temas_str = request.form.get(field_name)
                    
                    # Try to convert to integer
                    try:
                        num_temas = int(num_temas_str)
                    except (ValueError, TypeError):
                        num_temas = 1
                        
                    # Ensure the number is at least 1
                    num_temas = max(1, num_temas)
                    
                    # Find existing config or create new one
                    config = SorteoConfig.query.filter_by(
                        concurso_tipo=tipo,
                        categoria_codigo=categoria.codigo
                    ).first()
                    
                    if config:
                        # Update existing config
                        config.numero_temas_sorteados = num_temas
                    else:
                        # Create new config
                        config = SorteoConfig(
                            concurso_tipo=tipo,
                            categoria_codigo=categoria.codigo,
                            numero_temas_sorteados=num_temas
                        )
                        db.session.add(config)
            
            db.session.commit()
            flash('Configuración de sorteo guardada correctamente.', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al guardar la configuración: {str(e)}', 'danger')
        
        return redirect(url_for('admin_sorteo_config.index'))
    
    return render_template('admin/sorteo_config/index.html', 
                           categorias=categorias, 
                           config_dict=config_dict)

# Function to initialize sorteo configuration with default values
def init_sorteo_config():
    """Initialize sorteo configuration with default rules"""
    try:
        # Check if we need to initialize (if there are no configs)
        if SorteoConfig.query.first() is None:
            # Default rules for Regular concursos
            regular_rules = {
                'PAD': 1, 'PAS': 1, 'PTIT': 1,  # 1 tema for Profesores
                'JTP': 3, 'AYP': 3  # 3 temas for Auxiliares
            }
            
            # Default rules for Interino concursos
            interino_rules = {
                'PAD': 1, 'PAS': 1, 'PTIT': 1,  # 1 tema for Profesores
                'JTP': 1, 'AYP': 1  # 1 tema for Auxiliares
            }
            
            # Add Regular configs
            for categoria, num_temas in regular_rules.items():
                config = SorteoConfig(
                    concurso_tipo='REGULAR',
                    categoria_codigo=categoria,
                    numero_temas_sorteados=num_temas
                )
                db.session.add(config)
            
            # Add Interino configs
            for categoria, num_temas in interino_rules.items():
                config = SorteoConfig(
                    concurso_tipo='INTERINO',
                    categoria_codigo=categoria,
                    numero_temas_sorteados=num_temas
                )
                db.session.add(config)
            
            db.session.commit()
            print("Sorteo configuration initialized with default values.")
    except Exception as e:
        db.session.rollback()
        print(f"Error initializing sorteo configuration: {str(e)}")
