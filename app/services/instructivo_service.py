from typing import Optional
from app.models.models import db, Instructivo, Concurso, Categoria


class InstructivoService:
    """Service layer for retrieving and managing instructivos.

    Resolution precedence for tipo in (POSTULANTES, TRIBUNAL):
      1. Exact (tipo, categoria_id, dedicacion)
      2. Base  (tipo, categoria_id, dedicacion IS NULL)
      3. Global fallback (GENERAL, NULL, NULL)
    """

    def _normalize_concurso_tipo(self, concurso_tipo: Optional[str]) -> Optional[str]:
        if not concurso_tipo:
            return None
        val = concurso_tipo.strip().upper()
        if val.startswith('REG'):
            return 'REGULAR'
        if val.startswith('INT'):
            return 'INTERINO'
        return None

    def get_for_concurso(self, concurso: Concurso, tipo: str) -> Optional[str]:
        categoria = Categoria.query.filter_by(codigo=concurso.categoria).first()
        categoria_id = categoria.id if categoria else None
        dedicacion = concurso.dedicacion
        concurso_tipo = self._normalize_concurso_tipo(getattr(concurso, 'tipo', None))
        return self.resolve(tipo=tipo, concurso_tipo=concurso_tipo, categoria_id=categoria_id, dedicacion=dedicacion)

    def resolve(self, tipo: str, concurso_tipo: Optional[str], categoria_id: Optional[int], dedicacion: Optional[str]) -> Optional[str]:
        # Precedence including concurso_tipo dimension
        filters = []
        # 1) Exact within concurso_tipo
        filters.append(dict(tipo=tipo, concurso_tipo=concurso_tipo, categoria_id=categoria_id, dedicacion=dedicacion))
        # 2) Base within concurso_tipo (no dedicacion)
        filters.append(dict(tipo=tipo, concurso_tipo=concurso_tipo, categoria_id=categoria_id, dedicacion=None))
        # 3) Exact without concurso_tipo (legacy/base)
        filters.append(dict(tipo=tipo, concurso_tipo=None, categoria_id=categoria_id, dedicacion=dedicacion))
        # 4) Base without concurso_tipo
        filters.append(dict(tipo=tipo, concurso_tipo=None, categoria_id=categoria_id, dedicacion=None))
        # 5) Tipo-level global within concurso_tipo
        filters.append(dict(tipo=tipo, concurso_tipo=concurso_tipo, categoria_id=None, dedicacion=None))
        # 6) Audience global (no concurso_tipo)
        filters.append(dict(tipo=tipo, concurso_tipo=None, categoria_id=None, dedicacion=None))
        for f in filters:
            q = Instructivo.query.filter_by(is_active=True, **f).first()
            if q:
                return q.contenido
        # 7) GENERAL global fallback
        if tipo != 'GENERAL':
            q = Instructivo.query.filter_by(tipo='GENERAL', concurso_tipo=None, categoria_id=None, dedicacion=None, is_active=True).first()
            if q:
                return q.contenido
        return None

    def resolve_with_meta(self, tipo: str, categoria_id: Optional[int], dedicacion: Optional[str], concurso_tipo: Optional[str] = None):
        """Return (contenido, source_level, InstructivoObj) where source_level in
        ['exact','base','general','none'].
        """
        # Normalize concurso_tipo
        concurso_tipo = self._normalize_concurso_tipo(concurso_tipo)
        # exact within concurso_tipo
        inst = Instructivo.query.filter_by(tipo=tipo, concurso_tipo=concurso_tipo, categoria_id=categoria_id, dedicacion=dedicacion, is_active=True).first()
        if inst:
            return inst.contenido, 'exact', inst
        # base within concurso_tipo
        if categoria_id is not None:
            inst = Instructivo.query.filter_by(tipo=tipo, concurso_tipo=concurso_tipo, categoria_id=categoria_id, dedicacion=None, is_active=True).first()
            if inst:
                return inst.contenido, 'base', inst
        # exact without concurso_tipo (legacy)
        inst = Instructivo.query.filter_by(tipo=tipo, concurso_tipo=None, categoria_id=categoria_id, dedicacion=dedicacion, is_active=True).first()
        if inst:
            return inst.contenido, 'exact', inst
        # base without concurso_tipo
        if categoria_id is not None:
            inst = Instructivo.query.filter_by(tipo=tipo, concurso_tipo=None, categoria_id=categoria_id, dedicacion=None, is_active=True).first()
            if inst:
                return inst.contenido, 'base', inst
        # tipo-level global within concurso_tipo (treat as 'general' for source labeling)
        inst = Instructivo.query.filter_by(tipo=tipo, concurso_tipo=concurso_tipo, categoria_id=None, dedicacion=None, is_active=True).first()
        if inst:
            return inst.contenido, 'general', inst
        # general fallback within audience without concurso_tipo
        inst = Instructivo.query.filter_by(tipo=tipo, concurso_tipo=None, categoria_id=None, dedicacion=None, is_active=True).first()
        if inst:
            return inst.contenido, 'general', inst
        # global fallback to tipo='GENERAL'
        if tipo != 'GENERAL':
            inst = Instructivo.query.filter_by(tipo='GENERAL', concurso_tipo=None, categoria_id=None, dedicacion=None, is_active=True).first()
            if inst:
                return inst.contenido, 'general', inst
        return None, 'none', None

    def create_or_update(self, *, tipo: str, categoria_id: Optional[int], dedicacion: Optional[str], contenido: str, actor_persona_id: Optional[int] = None, concurso_tipo: Optional[str] = None) -> Instructivo:
        concurso_tipo = self._normalize_concurso_tipo(concurso_tipo)
        inst = Instructivo.query.filter_by(tipo=tipo, concurso_tipo=concurso_tipo, categoria_id=categoria_id, dedicacion=dedicacion).first()
        if inst:
            inst.contenido = contenido
            inst.bump_version()
            inst.updated_by_persona_id = actor_persona_id
        else:
            inst = Instructivo(
                tipo=tipo,
                concurso_tipo=concurso_tipo,
                categoria_id=categoria_id,
                dedicacion=dedicacion,
                contenido=contenido,
                created_by_persona_id=actor_persona_id,
            )
            db.session.add(inst)
        db.session.commit()
        return inst

    def list(self, *, tipo: Optional[str] = None, categoria_id: Optional[int] = None, concurso_tipo: Optional[str] = None):
        q = Instructivo.query.filter_by(is_active=True)
        if tipo:
            q = q.filter_by(tipo=tipo)
        if categoria_id is not None:
            q = q.filter_by(categoria_id=categoria_id)
        if concurso_tipo is not None:
            q = q.filter_by(concurso_tipo=self._normalize_concurso_tipo(concurso_tipo))
        return q.order_by(Instructivo.tipo, Instructivo.concurso_tipo, Instructivo.categoria_id, Instructivo.dedicacion).all()

    # Structured helpers returning dict in legacy shape {base, dedicacion}
    def get_structured_postulantes(self, concurso: Concurso):
        categoria = Categoria.query.filter_by(codigo=concurso.categoria).first()
        cat_id = categoria.id if categoria else None
        concurso_tipo = self._normalize_concurso_tipo(getattr(concurso, 'tipo', None))
        dedic_content, dedic_level, dedic_inst = self.resolve_with_meta('POSTULANTES', cat_id, concurso.dedicacion, concurso_tipo)
        base_content, base_level, base_inst = self.resolve_with_meta('POSTULANTES', cat_id, None, concurso_tipo)
        # Decide structure
        if dedic_level == 'exact' and base_content and dedic_content != base_content:
            return {
                'base': base_content,
                'dedicacion': dedic_content,
                'meta': {
                    'base_source': base_level,
                    'dedic_source': dedic_level,
                    'version': dedic_inst.version if dedic_inst else base_inst.version if base_inst else None,
                    'updated_at': (dedic_inst.updated_at if dedic_inst else base_inst.updated_at if base_inst else None)
                }
            }
        merged = dedic_content or base_content
        if merged:
            chosen_inst = dedic_inst or base_inst
            return {
                'base': merged,
                'dedicacion': '',
                'meta': {
                    'base_source': dedic_level if dedic_content else base_level,
                    'version': chosen_inst.version if chosen_inst else None,
                    'updated_at': chosen_inst.updated_at if chosen_inst else None
                }
            }
        return None

    def seed_from_roles_categorias(self, json_path: str):
        """Seed instructivos from legacy roles_categorias.json if table is empty.
        Safe to run multiple times (no-op if rows exist).
        """
        if Instructivo.query.first():
            return 0
        import json, os
        if not os.path.exists(json_path):
            return 0
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        inserted = 0
        from app.models.models import Categoria as Cat
        cats_by_code = {c.codigo: c for c in Cat.query.all()}
        for rol in data:
            for cat in rol.get('categorias', []):
                codigo = cat.get('codigo')
                categoria = cats_by_code.get(codigo)
                if not categoria:
                    continue
                # Postulantes
                ip = cat.get('instructivo_postulantes') or {}
                base = ip.get('base')
                if base:
                    db.session.add(Instructivo(tipo='POSTULANTES', categoria_id=categoria.id, dedicacion=None, contenido=base))
                    inserted += 1
                for dedic, text in (ip.get('porDedicacion') or {}).items():
                    if text:
                        db.session.add(Instructivo(tipo='POSTULANTES', categoria_id=categoria.id, dedicacion=dedic, contenido=text))
                        inserted += 1
                # Tribunal
                it = cat.get('instructivo_tribunal') or {}
                base_t = it.get('base')
                if base_t:
                    db.session.add(Instructivo(tipo='TRIBUNAL', categoria_id=categoria.id, dedicacion=None, contenido=base_t))
                    inserted += 1
                for dedic, text in (it.get('porDedicacion') or {}).items():
                    if text:
                        db.session.add(Instructivo(tipo='TRIBUNAL', categoria_id=categoria.id, dedicacion=dedic, contenido=text))
                        inserted += 1
        db.session.commit()
        return inserted

    def get_structured_tribunal(self, concurso: Concurso):
        categoria = Categoria.query.filter_by(codigo=concurso.categoria).first()
        cat_id = categoria.id if categoria else None
        concurso_tipo = self._normalize_concurso_tipo(getattr(concurso, 'tipo', None))
        dedic_content, dedic_level, dedic_inst = self.resolve_with_meta('TRIBUNAL', cat_id, concurso.dedicacion, concurso_tipo)
        base_content, base_level, base_inst = self.resolve_with_meta('TRIBUNAL', cat_id, None, concurso_tipo)
        if dedic_level == 'exact' and base_content and dedic_content != base_content:
            return {
                'base': base_content,
                'dedicacion': dedic_content,
                'meta': {
                    'base_source': base_level,
                    'dedic_source': dedic_level,
                    'version': dedic_inst.version if dedic_inst else base_inst.version if base_inst else None,
                    'updated_at': (dedic_inst.updated_at if dedic_inst else base_inst.updated_at if base_inst else None)
                }
            }
        merged = dedic_content or base_content
        if merged:
            chosen_inst = dedic_inst or base_inst
            return {
                'base': merged,
                'dedicacion': '',
                'meta': {
                    'base_source': dedic_level if dedic_content else base_level,
                    'version': chosen_inst.version if chosen_inst else None,
                    'updated_at': chosen_inst.updated_at if chosen_inst else None
                }
            }
        return None

instructivo_service = InstructivoService()