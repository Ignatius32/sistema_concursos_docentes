from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), default='admin')  # admin, staff, etc.
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Departamento(db.Model):
    __tablename__ = 'departamentos'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    responsable = db.Column(db.String(100))
    correo = db.Column(db.String(100))
    areas = db.relationship('Area', backref='departamento', lazy='dynamic')
    concursos = db.relationship('Concurso', backref='departamento_rel', lazy='dynamic')

class Area(db.Model):
    __tablename__ = 'areas'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    departamento_id = db.Column(db.Integer, db.ForeignKey('departamentos.id'))
    orientaciones = db.relationship('Orientacion', backref='area', lazy='dynamic')

class Orientacion(db.Model):
    __tablename__ = 'orientaciones'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    area_id = db.Column(db.Integer, db.ForeignKey('areas.id'))

class Categoria(db.Model):
    __tablename__ = 'categorias'
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(10), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    rol = db.Column(db.String(50), nullable=False)  # 'Profesor' or 'Auxiliar'

class Concurso(db.Model):
    __tablename__ = 'concursos'
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(50), nullable=False)  # Regular/Interino
    cerrado_abierto = db.Column(db.String(20), nullable=False)  # Abierto/Cerrado
    cant_cargos = db.Column(db.Integer, nullable=False)
    departamento_id = db.Column(db.Integer, db.ForeignKey('departamentos.id'))
    area = db.Column(db.String(100), nullable=False)
    orientacion = db.Column(db.String(100), nullable=False)
    categoria = db.Column(db.String(10), nullable=False)  # PAD, JTP, etc
    categoria_nombre = db.Column(db.String(100), nullable=True)  # Full name of the categoria
    dedicacion = db.Column(db.String(20), nullable=False)  # Simple, Parcial, Exclusiva
    localizacion = db.Column(db.String(100))
    asignaturas = db.Column(db.String(255), nullable=True)  # Optional field for subjects
    expediente = db.Column(db.String(100), nullable=True)  # Optional field for file number
    origen_vacante = db.Column(db.String(50), nullable=True)  # LICENCIA SIN GOCE DE HABERES, RENUNCIA
    docente_vacante = db.Column(db.String(100), nullable=True)  # Name of the teacher who generated the vacancy
    categoria_vacante = db.Column(db.String(10), nullable=True)  # PAD, JTP, etc of the vacancy position
    dedicacion_vacante = db.Column(db.String(20), nullable=True)  # Simple, Parcial, Exclusiva of the vacancy position
    id_designacion_mocovi = db.Column(db.String(50), nullable=True)  # ID from MOCOVI system
    creado = db.Column(db.DateTime, default=datetime.utcnow)
    cierre_inscripcion = db.Column(db.Date, nullable=True)  # Changed to nullable=True
    vencimiento = db.Column(db.Date, nullable=True)  # Already nullable
    estado_actual = db.Column(db.String(50), default="CREADO")
    drive_folder_id = db.Column(db.String(100), nullable=True)  # Google Drive folder ID
    borradores_folder_id = db.Column(db.String(100), nullable=True)  # Borradores subfolder ID
    postulantes_folder_id = db.Column(db.String(100), nullable=True)  # Postulantes subfolder ID
    documentos_firmados_folder_id = db.Column(db.String(100), nullable=True)  # Documentos firmados subfolder ID
    tribunal_folder_id = db.Column(db.String(100), nullable=True)  # Tribunal subfolder ID

    nro_res_llamado_interino = db.Column(db.String(50), nullable=True)
    nro_res_llamado_regular = db.Column(db.String(50), nullable=True)
    nro_res_tribunal_regular = db.Column(db.String(50), nullable=True)

    # New fields for committee and council information
    fecha_comision_academica = db.Column(db.Date, nullable=True)
    despacho_comision_academica = db.Column(db.String(255), nullable=True)
    sesion_consejo_directivo = db.Column(db.String(100), nullable=True)
    fecha_consejo_directivo = db.Column(db.Date, nullable=True)
    despacho_consejo_directivo = db.Column(db.String(255), nullable=True)
    
    # Relationships
    tribunal = db.relationship('TribunalMiembro', backref='concurso', lazy='dynamic')
    postulantes = db.relationship('Postulante', backref='concurso', lazy='dynamic')
    documentos = db.relationship('DocumentoConcurso', backref='concurso', lazy='dynamic')
    historial_estados = db.relationship('HistorialEstado', backref='concurso', lazy='dynamic')
    sustanciacion = db.relationship('Sustanciacion', backref='concurso', uselist=False)
    impugnaciones = db.relationship('Impugnacion', backref='concurso', lazy='dynamic')
    recusaciones = db.relationship('Recusacion', backref='concurso', lazy='dynamic')

class TribunalMiembro(db.Model):
    __tablename__ = 'tribunal_miembros'
    id = db.Column(db.Integer, primary_key=True)
    concurso_id = db.Column(db.Integer, db.ForeignKey('concursos.id', name='fk_tribunal_miembro_concurso'))
    rol = db.Column(db.String(50), nullable=False)  # Presidente, Vocal, Suplente
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    dni = db.Column(db.String(20), nullable=False)
    correo = db.Column(db.String(100))
    drive_folder_id = db.Column(db.String(100), nullable=True)  # Google Drive folder ID
    recusaciones = db.relationship('Recusacion', backref='miembro', lazy='dynamic')
    documentos = db.relationship('DocumentoTribunal', backref='miembro', lazy='dynamic')
    
    # Auth and notification fields with explicit constraint names
    username = db.Column(db.String(50), unique=True, nullable=True)
    password_hash = db.Column(db.String(128), nullable=True)
    notificado = db.Column(db.Boolean, default=False)
    fecha_notificacion = db.Column(db.DateTime, nullable=True)
    ultimo_acceso = db.Column(db.DateTime, nullable=True)
    
    __table_args__ = (
        db.UniqueConstraint('username', name='uq_tribunal_miembro_username'),
    )
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    # Helper function to get all concursos this member is part of
    def get_concursos(self):
        return Concurso.query.join(TribunalMiembro).filter(TribunalMiembro.id == self.id).all()

class DocumentoTribunal(db.Model):
    __tablename__ = 'documentos_tribunal'
    id = db.Column(db.Integer, primary_key=True)
    miembro_id = db.Column(db.Integer, db.ForeignKey('tribunal_miembros.id', name='fk_documento_tribunal_miembro'))
    tipo = db.Column(db.String(50), nullable=False)  # CV, DNI
    url = db.Column(db.String(255), nullable=False)
    creado = db.Column(db.DateTime, default=datetime.utcnow)

class Postulante(db.Model):
    __tablename__ = 'postulantes'
    id = db.Column(db.Integer, primary_key=True)
    concurso_id = db.Column(db.Integer, db.ForeignKey('concursos.id'))
    dni = db.Column(db.String(20), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    correo = db.Column(db.String(100))
    telefono = db.Column(db.String(20))
    drive_folder_id = db.Column(db.String(100), nullable=True)  # Google Drive folder ID
    
    # Relationships
    documentos = db.relationship('DocumentoPostulante', backref='postulante', lazy='dynamic')
    impugnaciones = db.relationship('Impugnacion', backref='postulante', lazy='dynamic')

class DocumentoPostulante(db.Model):
    __tablename__ = 'documentos_postulante'
    id = db.Column(db.Integer, primary_key=True)
    postulante_id = db.Column(db.Integer, db.ForeignKey('postulantes.id', name='fk_documento_postulante_id'))
    tipo = db.Column(db.String(50), nullable=False)  # CV, DNI, etc.
    url = db.Column(db.String(255), nullable=False)
    creado = db.Column(db.DateTime, default=datetime.utcnow)

class DocumentoConcurso(db.Model):
    __tablename__ = 'documentos_concurso'