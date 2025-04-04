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
    
    # Authentication and notification fields
    username = db.Column(db.String(50), nullable=True)
    password_hash = db.Column(db.String(128), nullable=True)
    reset_token = db.Column(db.String(100), nullable=True)  # For password setup
    notificado = db.Column(db.Boolean, default=False)
    notificado_sustanciacion = db.Column(db.Boolean, default=False)  # New field
    fecha_notificacion = db.Column(db.DateTime, nullable=True)
    fecha_notificacion_sustanciacion = db.Column(db.DateTime, nullable=True)  # New field
    ultimo_acceso = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    recusaciones = db.relationship('Recusacion', backref='miembro', lazy='dynamic')
    documentos = db.relationship('DocumentoTribunal', backref='miembro', lazy='dynamic')
    firmas = db.relationship('FirmaDocumento', 
                           back_populates='miembro',
                           overlaps="miembro_tribunal,firmas_realizadas",
                           lazy=True)
    
    __table_args__ = (
        db.UniqueConstraint('username', name='uq_tribunal_miembro_username'),
    )
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        self.reset_token = None  # Clear reset token after password is set

    def check_password(self, password):
        return check_password_hash(self.password_hash, password) if self.password_hash else False
    
    def generate_reset_token(self):
        """Generate a unique token for password setup."""
        from secrets import token_urlsafe
        self.reset_token = token_urlsafe(32)
        return self.reset_token
    
    def check_reset_token(self, token):
        """Check if a reset token is valid."""
        if not self.reset_token or self.reset_token != token:
            return False
        # Could add expiration check here if needed
        return True
    
    def get_concursos(self):
        return Concurso.query.join(TribunalMiembro).filter(TribunalMiembro.id == self.id).all()

class DocumentoTribunal(db.Model):
    __tablename__ = 'documentos_tribunal'
    id = db.Column(db.Integer, primary_key=True)
    miembro_id = db.Column(db.Integer, db.ForeignKey('tribunal_miembros.id'), nullable=False)
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
    postulante_id = db.Column(db.Integer, db.ForeignKey('postulantes.id', name='fk_postulante_documentos'))
    tipo = db.Column(db.String(50), nullable=False)  # CV, DNI, etc.
    url = db.Column(db.String(255), nullable=False)
    creado = db.Column(db.DateTime, default=datetime.utcnow)

class DocumentoConcurso(db.Model):
    __tablename__ = 'documentos_concurso'
    id = db.Column(db.Integer, primary_key=True)
    concurso_id = db.Column(db.Integer, db.ForeignKey('concursos.id'))
    tipo = db.Column(db.String(50), nullable=False)  # RESOLUCION_LLAMADO, ACTA_CIERRE, etc.
    url = db.Column(db.String(255))
    estado = db.Column(db.String(20), default="CREADA")
    creado = db.Column(db.DateTime, default=datetime.utcnow)
    firma_count = db.Column(db.Integer, nullable=False, default=0)
    # Separate file IDs for borrador and firmado versions
    borrador_file_id = db.Column(db.String(100), nullable=True)  # ID of the draft file in borradores folder
    file_id = db.Column(db.String(100), nullable=True)  # ID of the uploaded/signed file in documentos_firmados folder

    firmas = db.relationship('FirmaDocumento', 
                           back_populates='documento_concurso',
                           lazy=True,
                           cascade='all, delete-orphan')

    def ya_firmado_por(self, miembro_id):
        """Check if a tribunal member has already signed this document."""
        return any(firma.miembro_id == miembro_id for firma in self.firmas)

    def is_visible_to_tribunal(self):
        """
        Determine if this document should be visible to tribunal members.
        
        Returns:
            bool: True if the document should be visible to tribunal members
        """
        # Document types that are always visible to tribunal members regardless of state
        always_visible = [
            'ACTA_CONSTITUCION_TRIBUNAL_REGULAR',
            'ACTA_DICTAMEN',
            'ACTA_SORTEO'
        ]
        
        if self.tipo in always_visible:
            return True
            
        # Check if the document type contains "acta constitucion tribunal" (case insensitive)
        if 'acta constitucion tribunal' in self.tipo.lower().replace('_', ' '):
            return True

        # Documents with FIRMADO state are always visible
        if self.estado == 'FIRMADO':
            return True
            
        # Documents in PENDIENTE DE FIRMA state are visible
        if self.estado == 'PENDIENTE DE FIRMA':
            return True
            
        # All other documents (typically BORRADOR) are not visible to tribunal
        return False
        
    def get_friendly_name(self):
        """
        Convert the document type code to a friendly display name.
        Example: 'RESOLUCION_LLAMADO_TRIBUNAL' -> 'Resolución Llamado Tribunal'
        
        Returns:
            str: A user-friendly name for the document type
        """
        # Split by underscore
        words = self.tipo.split('_')
        
        # Convert each word to title case (first letter uppercase, rest lowercase)
        words = [word.title() for word in words]
        
        # Join with spaces
        return ' '.join(words)

    # Keep the property for backward compatibility, but make it read/write
    @property
    def drive_file_id(self):
        """Extract Google Drive file ID from URL."""
        if self.file_id:
            return self.file_id
        
        if not self.url:
            return None
        try:
            # URLs are in format https://drive.google.com/file/d/FILE_ID/view
            return self.url.split('/d/')[1].split('/')[0]
        except (IndexError, AttributeError):
            return None

class FirmaDocumento(db.Model):
    __tablename__ = 'firmas_documento'
    id = db.Column(db.Integer, primary_key=True)
    documento_id = db.Column(db.Integer, db.ForeignKey('documentos_concurso.id', ondelete='CASCADE'), nullable=False)
    miembro_id = db.Column(db.Integer, db.ForeignKey('tribunal_miembros.id', ondelete='CASCADE'), nullable=False)
    fecha_firma = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Update relationships with back_populates
    documento_concurso = db.relationship('DocumentoConcurso', back_populates='firmas')
    miembro = db.relationship('TribunalMiembro', back_populates='firmas')

class HistorialEstado(db.Model):
    __tablename__ = 'historial_estados'
    id = db.Column(db.Integer, primary_key=True)
    concurso_id = db.Column(db.Integer, db.ForeignKey('concursos.id'))
    estado = db.Column(db.String(50), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    observaciones = db.Column(db.Text)

class Sustanciacion(db.Model):
    __tablename__ = 'sustanciacion'
    id = db.Column(db.Integer, primary_key=True)
    concurso_id = db.Column(db.Integer, db.ForeignKey('concursos.id'))
    
    # Constitución del jurado
    constitucion_fecha = db.Column(db.DateTime)
    constitucion_lugar = db.Column(db.String(100))
    constitucion_observaciones = db.Column(db.Text)
    constitucion_virtual_link = db.Column(db.String(255), nullable=True)  # Link to virtual meeting
    
    # Sorteo tema exposición
    sorteo_fecha = db.Column(db.DateTime)
    sorteo_lugar = db.Column(db.String(100))
    sorteo_observaciones = db.Column(db.Text)
    sorteo_virtual_link = db.Column(db.String(255), nullable=True)  # Link to virtual meeting
    temas_exposicion = db.Column(db.Text, nullable=True)  # List of topics for exposition
    tema_sorteado = db.Column(db.Text, nullable=True)  # The randomly selected topic
    
    # Exposición
    exposicion_fecha = db.Column(db.DateTime)
    exposicion_lugar = db.Column(db.String(100))
    exposicion_observaciones = db.Column(db.Text)
    exposicion_virtual_link = db.Column(db.String(255), nullable=True)  # Link to virtual meeting
    
    # Dictamen
    dictamen_fecha = db.Column(db.DateTime)
    dictamen_lugar = db.Column(db.String(100))
    dictamen_observaciones = db.Column(db.Text)
    
    # Resolución
    resolucion_fecha = db.Column(db.DateTime)
    resolucion_observaciones = db.Column(db.Text)

class Impugnacion(db.Model):
    __tablename__ = 'impugnaciones'
    id = db.Column(db.Integer, primary_key=True)
    concurso_id = db.Column(db.Integer, db.ForeignKey('concursos.id'))
    postulante_id = db.Column(db.Integer, db.ForeignKey('postulantes.id'))
    fecha_presentacion = db.Column(db.DateTime, default=datetime.utcnow)
    motivo = db.Column(db.Text)
    estado = db.Column(db.String(50))  # PRESENTADA, RESUELTA, etc.
    resolucion = db.Column(db.Text)
    fecha_resolucion = db.Column(db.DateTime)

class Recusacion(db.Model):
    __tablename__ = 'recusaciones'
    id = db.Column(db.Integer, primary_key=True)
    concurso_id = db.Column(db.Integer, db.ForeignKey('concursos.id'))
    miembro_id = db.Column(db.Integer, db.ForeignKey('tribunal_miembros.id'))
    fecha_presentacion = db.Column(db.DateTime, default=datetime.utcnow)
    motivo = db.Column(db.Text)
    estado = db.Column(db.String(50))  # PRESENTADA, RESUELTA, etc.
    resolucion = db.Column(db.Text)
    fecha_resolucion = db.Column(db.DateTime)

# Function to initialize the database with departments, areas, and orientations from JSON
def init_db_from_json(app, json_data):
    with app.app_context():
        # Create departamentos, areas and orientaciones from the JSON
        departments_created = {}
        areas_created = {}
        
        for dept_name, dept_data in json_data.items():
            # Create department if it doesn't exist
            if dept_name not in departments_created:
                dept = Departamento(nombre=dept_name)
                db.session.add(dept)
                db.session.flush()  # To get the ID
                departments_created[dept_name] = dept.id
            
            # Create areas and orientations for this department
            for area_name, orientations in dept_data.items():
                # Create area if it doesn't exist
                area_key = f"{dept_name}_{area_name}"
                if area_key not in areas_created:
                    area = Area(nombre=area_name, departamento_id=departments_created[dept_name])
                    db.session.add(area)
                    db.session.flush()  # To get the ID
                    areas_created[area_key] = area.id
                
                # Create orientations for this area
                for orientation_name in orientations:
                    if orientation_name:  # Skip empty orientation names
                        orientacion = Orientacion(nombre=orientation_name, area_id=areas_created[area_key])
                        db.session.add(orientacion)
        
        # Commit all changes
        db.session.commit()

# Function to initialize categories from the roles_categorias.json
def init_categories_from_json(app, json_data):
    with app.app_context():
        for rol in json_data:
            rol_name = rol['nombre']
            for cat in rol['categorias']:
                categoria = Categoria(
                    codigo=cat['codigo'],
                    nombre=cat['nombre'],
                    rol=rol_name
                )
                db.session.add(categoria)
        
        db.session.commit()