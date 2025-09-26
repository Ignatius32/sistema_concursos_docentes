from flask import Blueprint, request, jsonify, render_template, g
from app.utils.keycloak_auth import (
    keycloak_login_required,
    admin_required,
    get_current_user_name,
    get_current_user_roles,
    is_admin as keycloak_is_admin,
)
from app.services.instructivo_service import instructivo_service
from app.models.models import Categoria

bp = Blueprint('admin_instructivos', __name__, url_prefix='/admin/instructivos')


@bp.route('/', methods=['GET'])
@keycloak_login_required
@admin_required
def list_instructivos():
    tipo = request.args.get('tipo')
    categoria_id = request.args.get('categoria_id', type=int)
    data = [
        {
            'id': i.id,
            'tipo': i.tipo,
            'categoria_id': i.categoria_id,
            'categoria_codigo': Categoria.query.get(i.categoria_id).codigo if i.categoria_id else None,
            'dedicacion': i.dedicacion,
            'version': i.version,
            'contenido': i.contenido,
            'updated_at': i.updated_at.isoformat() if getattr(i, 'updated_at', None) else None,
        }
        for i in instructivo_service.list(tipo=tipo, categoria_id=categoria_id)
    ]
    return jsonify(data)


@bp.route('/ui', methods=['GET'])
@keycloak_login_required
@admin_required
def ui_page():
    # Template can rely on context processors for role info
    return render_template('admin/instructivos.html')


@bp.route('/', methods=['POST'])
@keycloak_login_required
@admin_required
def create_or_update():
    payload = request.get_json() or {}
    required = ['tipo', 'contenido']
    for r in required:
        if r not in payload:
            return jsonify({'error': f'missing {r}'}), 400
    inst = instructivo_service.create_or_update(
        tipo=payload['tipo'],
        categoria_id=payload.get('categoria_id'),
        dedicacion=payload.get('dedicacion'),
        contenido=payload['contenido'],
        # actor_persona_id mapping from Keycloak user -> persona not yet integrated here
        actor_persona_id=None,
    )
    return jsonify({'id': inst.id, 'version': inst.version}), 201