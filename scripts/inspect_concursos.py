from app import create_app
from app.models.models import Concurso

app = create_app()

if __name__ == "__main__":
    with app.app_context():
        uri = app.config.get('SQLALCHEMY_DATABASE_URI')
        print(f"DB URI: {uri}")
        count = Concurso.query.count()
        print(f"Concursos count: {count}")
        for c in Concurso.query.order_by(Concurso.id).all():
            apertura = getattr(c, 'fecha_apertura_inscripcion', None)
            cierre = getattr(c, 'cierre_inscripcion', None)
            venc = getattr(c, 'vencimiento', None)
            depto = getattr(c, 'departamento_id', None)
            print(f"- id={c.id} tipo={c.tipo} categoria={c.categoria} depto_id={depto} apertura={apertura} cierre={cierre} venc={venc}")
