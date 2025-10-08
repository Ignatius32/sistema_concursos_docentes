from typing import List, Optional, Tuple
from app.models.models import db, RequiredDocumentSet, Categoria, Concurso

# Canonical catalog of document codes and their human labels
DOCUMENT_CATALOG = {
    'DNI': 'Fotocopia certificada del DNI',
    'CV': 'Curriculum Vitae actualizado y documentación respaldatoria',
    'DOCUMENTACION_RESPALDATORIA_CV': 'Documentación respaldatoria del CV',
    'TITULO_UNIVERSITARIO': 'Fotocopia certificada del título universitario',
    'ANTECEDENTES_IDONEIDAD': 'Certificados de antecedentes de idoneidad',
    'PROPUESTA_PROGRAMA': 'Propuesta de programa detallada',
    'ACTIVIDADES_PREVISTAS': 'Plan de actividades previstas',
    'PLAN_FORMACION_RRHH': 'Programa de formación de recursos humanos',
    'PLAN_IVE': 'Plan de investigación/vinculación/extensión',
    'PLAN_IVE_OPCIONAL': 'Plan de investigación/vinculación/extensión (opcional)',
    'PLAN_O_PROGRAMA_ACTIVIDADES': 'Plan o programa de actividades',
    'PROPUESTA_EJERCICIO_O_TP': 'Propuesta de ejercicio o trabajo práctico',
}

class RequiredDocsService:
    """Service for configurable required documents per categoria/dedicacion.

    Resolution precedence (including concurso_tipo when provided):
        1. (categoria_id, dedicacion, concurso_tipo)
        2. (categoria_id, dedicacion, NULL)
        3. (categoria_id, NULL, concurso_tipo)
        4. (categoria_id, NULL, NULL)
        5. (NULL, NULL, concurso_tipo)
        6. (NULL, NULL, NULL)
    """

    def resolve(self, *, categoria_id: Optional[int], dedicacion: Optional[str], concurso_tipo: Optional[str]) -> List[str]:
        q = RequiredDocumentSet.query.filter_by(is_active=True)
        # Try exact category+dedicacion+tipo
        if categoria_id is not None and dedicacion is not None and concurso_tipo is not None:
            inst = q.filter_by(categoria_id=categoria_id, dedicacion=dedicacion, concurso_tipo=concurso_tipo).first()
            if inst:
                return inst.documentos or []
        # Category+dedicacion base (tipo NULL)
        if categoria_id is not None and dedicacion is not None:
            inst = q.filter_by(categoria_id=categoria_id, dedicacion=dedicacion, concurso_tipo=None).first()
            if inst:
                return inst.documentos or []
        # Category base by tipo
        if categoria_id is not None and concurso_tipo is not None:
            inst = q.filter_by(categoria_id=categoria_id, dedicacion=None, concurso_tipo=concurso_tipo).first()
            if inst:
                return inst.documentos or []
        # Category base (both NULL)
        if categoria_id is not None:
            inst = q.filter_by(categoria_id=categoria_id, dedicacion=None, concurso_tipo=None).first()
            if inst:
                return inst.documentos or []
        # Global by tipo
        if concurso_tipo is not None:
            inst = q.filter_by(categoria_id=None, dedicacion=None, concurso_tipo=concurso_tipo).first()
            if inst:
                return inst.documentos or []
        # Global fallback
        inst = q.filter_by(categoria_id=None, dedicacion=None, concurso_tipo=None).first()
        if inst:
            return inst.documentos or []
        return []

    def resolve_for_concurso(self, concurso: Concurso) -> List[str]:
        categoria = Categoria.query.filter_by(codigo=concurso.categoria).first()
        categoria_id = categoria.id if categoria else None
        dedicacion = concurso.dedicacion
        concurso_tipo = concurso.tipo if getattr(concurso, 'tipo', None) else None
        return self.resolve(categoria_id=categoria_id, dedicacion=dedicacion, concurso_tipo=concurso_tipo)

    def create_or_update(self, *, categoria_id: Optional[int], dedicacion: Optional[str], documentos: List[str], actor_persona_id: Optional[int] = None, concurso_tipo: Optional[str] = None) -> RequiredDocumentSet:
        row = RequiredDocumentSet.query.filter_by(categoria_id=categoria_id, dedicacion=dedicacion, concurso_tipo=concurso_tipo).first()
        if row:
            row.documentos = documentos
            row.bump_version()
            row.updated_by_persona_id = actor_persona_id
        else:
            row = RequiredDocumentSet(
                categoria_id=categoria_id,
                dedicacion=dedicacion,
                concurso_tipo=concurso_tipo,
                documentos=documentos,
                created_by_persona_id=actor_persona_id,
            )
            db.session.add(row)
        db.session.commit()
        return row

    def list(self, *, categoria_id: Optional[int] = None, concurso_tipo: Optional[str] = None):
        q = RequiredDocumentSet.query.filter_by(is_active=True)
        if categoria_id is not None:
            q = q.filter_by(categoria_id=categoria_id)
        if concurso_tipo is not None:
            q = q.filter_by(concurso_tipo=concurso_tipo)
        return q.order_by(RequiredDocumentSet.categoria_id, RequiredDocumentSet.dedicacion, RequiredDocumentSet.concurso_tipo).all()

    def seed_from_roles_categorias(self, json_path: str) -> int:
        """Seed initial data from legacy roles_categorias.json if table empty."""
        if RequiredDocumentSet.query.first():
            return 0
        import json, os
        if not os.path.exists(json_path):
            return 0
        from app.models.models import Categoria as Cat
        cats_by_code = {c.codigo: c for c in Cat.query.all()}
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        inserted = 0
        for rol in data:
            for cat in rol.get('categorias', []):
                codigo = cat.get('codigo')
                categoria = cats_by_code.get(codigo)
                if not categoria:
                    continue
                doc_req = cat.get('documentacionRequerida') or {}
                base_docs = doc_req.get('base') or []
                if base_docs:
                    db.session.add(RequiredDocumentSet(categoria_id=categoria.id, dedicacion=None, documentos=base_docs))
                    inserted += 1
                por_ded = doc_req.get('porDedicacion') or {}
                for dedic, docs in por_ded.items():
                    if docs:
                        db.session.add(RequiredDocumentSet(categoria_id=categoria.id, dedicacion=dedic, documentos=docs))
                        inserted += 1
        db.session.commit()
        return inserted

required_docs_service = RequiredDocsService()
