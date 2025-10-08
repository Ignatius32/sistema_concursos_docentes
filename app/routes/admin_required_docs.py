from flask import Blueprint, request, jsonify, render_template
from app.utils.keycloak_auth import keycloak_login_required, admin_required
from app.models.models import Categoria
from app.services.required_docs_service import required_docs_service, DOCUMENT_CATALOG

bp = Blueprint('admin_required_docs', __name__, url_prefix='/admin/required-docs')

@bp.route('/catalog', methods=['GET'])
@keycloak_login_required
@admin_required
def catalog():
    return jsonify([
        {'code': code, 'label': label}
        for code, label in DOCUMENT_CATALOG.items()
    ])

@bp.route('/', methods=['GET'])
@keycloak_login_required
@admin_required
def list_sets():
    categoria_id = request.args.get('categoria_id', type=int)
    concurso_tipo = request.args.get('concurso_tipo') or None
    rows = required_docs_service.list(categoria_id=categoria_id, concurso_tipo=concurso_tipo)
    return jsonify([
        {
            'id': r.id,
            'categoria_id': r.categoria_id,
            'categoria_codigo': r.categoria.codigo if r.categoria_id and r.categoria else None,
            'dedicacion': r.dedicacion,
            'concurso_tipo': r.concurso_tipo,
            'documentos': r.documentos,
            'version': r.version,
            'updated_at': r.updated_at.isoformat() if r.updated_at else None,
        } for r in rows
    ])

@bp.route('/', methods=['POST'])
@keycloak_login_required
@admin_required
def create_or_update():
    payload = request.get_json() or {}
    documentos = payload.get('documentos')
    if not isinstance(documentos, list):
        return jsonify({'error': 'documentos must be list'}), 400
    categoria_id = payload.get('categoria_id')
    dedicacion = payload.get('dedicacion') or None
    concurso_tipo = payload.get('concurso_tipo') or None
    row = required_docs_service.create_or_update(
        categoria_id=categoria_id,
        dedicacion=dedicacion,
        concurso_tipo=concurso_tipo,
        documentos=documentos,
        actor_persona_id=None
    )
    return jsonify({'id': row.id, 'version': row.version}), 201

@bp.route('/ui', methods=['GET'])
@keycloak_login_required
@admin_required
def ui():
    categorias = Categoria.query.order_by(Categoria.codigo).all()
    return render_template('admin/required_docs.html', categorias=categorias)
