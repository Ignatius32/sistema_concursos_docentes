import json
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
        if self.password_hash is None:
            return False
        return check_password_hash(self.password_hash, password)
        
    @property
    def is_admin(self): # Optional: for consistency if checking current_user.is_admin
        return self.role == 'admin'

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
    instructivo_postulantes = db.Column(db.JSON, nullable=True)
    instructivo_tribunal = db.Column(db.JSON, nullable=True)
    
class Persona(db.Model, UserMixin):
    __tablename__ = 'personas'
    id = db.Column(db.Integer, primary_key=True)
    dni = db.Column(db.String(20), nullable=False, unique=True, index=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    correo = db.Column(db.String(100))
    telefono = db.Column(db.String(20), nullable=True)
    username = db.Column(db.String(50), nullable=True, unique=True)    # Password fields removed - authentication handled by Keycloak
    # password_hash = db.Column(db.String(128), nullable=True)  # DEPRECATED - Removed for Keycloak
    # reset_token = db.Column(db.String(100), nullable=True)   # DEPRECATED - Removed for Keycloak
    ultimo_acceso = db.Column(db.DateTime, nullable=True)
    cv_drive_file_id = db.Column(db.String(100), nullable=True)
    cv_drive_web_link = db.Column(db.String(255), nullable=True)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    cargo = db.Column(db.String(100), nullable=True) 
    
    # Keycloak integration
    keycloak_user_id = db.Column(db.String(36), unique=True, nullable=True, index=True)
    
    # Relationships
    asignaciones = db.relationship('TribunalMiembro', back_populates='persona', lazy='dynamic')
      # Password-related methods removed - authentication handled by Keycloak
    # def set_password(self, password): - DEPRECATED
    # def check_password(self, password): - DEPRECATED  
    # def generate_reset_token(self): - DEPRECATED
    # def check_reset_token(self, token): - DEPRECATED
    def get_concursos(self):
        """Get all concursos this person is assigned to."""
        # This joins with TribunalMiembro and returns the Concurso objects
        # The relationship in Concurso (asignaciones_tribunal) will have the proper role info
        return Concurso.query.join(TribunalMiembro).filter(TribunalMiembro.persona_id == self.id).all()

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
    subestado = db.Column(db.Text, nullable=True)  # New field for subestado values (can hold multiple values as JSON)
    drive_folder_id = db.Column(db.String(100), nullable=True)  # Google Drive folder ID
    borradores_folder_id = db.Column(db.String(100), nullable=True)  # Borradores subfolder ID
    postulantes_folder_id = db.Column(db.String(100), nullable=True)  # Postulantes subfolder ID
    documentos_firmados_folder_id = db.Column(db.String(100), nullable=True)  # Documentos firmados subfolder ID
    tribunal_folder_id = db.Column(db.String(100), nullable=True)  # Tribunal subfolder ID
    nota_solicitud_sac_file_id = db.Column(db.String(100), nullable=True)  # Google Drive file ID for Nota Solicitud SAC
    nota_centro_estudiantes_file_id = db.Column(db.String(100), nullable=True)  # Google Drive file ID for Nota Centro Estudiantes
    nota_consulta_depto_file_id = db.Column(db.String(100), nullable=True)  # Google Drive file ID for Nota Consulta a Depto. Académico

    nro_res_llamado_interino = db.Column(db.String(50), nullable=True)
    nro_res_llamado_regular = db.Column(db.String(50), nullable=True)
    nro_res_tribunal_regular = db.Column(db.String(50), nullable=True)

    # New fields for committee and council information
    fecha_comision_academica = db.Column(db.Date, nullable=True)    
    despacho_comision_academica = db.Column(db.String(255), nullable=True)    
    sesion_consejo_directivo = db.Column(db.String(100), nullable=True)
    fecha_consejo_directivo = db.Column(db.Date, nullable=True)    
    despacho_consejo_directivo = db.Column(db.String(255), nullable=True)
    tkd = db.Column(db.String(100), nullable=True)
    tkd_file_id = db.Column(db.String(100), nullable=True)  # Google Drive file ID for TKD document
    nota_solicitud_sac_file_id = db.Column(db.String(100), nullable=True)  # Google Drive file ID for Nota Solicitud SAC
      # Relationships
    asignaciones_tribunal = db.relationship('TribunalMiembro', backref='concurso', lazy='dynamic')
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
    persona_id = db.Column(db.Integer, db.ForeignKey('personas.id'), nullable=False)
    rol = db.Column(db.String(50), nullable=False)  # Presidente, Titular, Suplente, Veedor
    claustro = db.Column(db.String(20), nullable=True, default='Docente')  # Docente, Estudiante
    drive_folder_id = db.Column(db.String(100), nullable=True)  # Google Drive folder ID
      # Permission fields
    can_add_tema = db.Column(db.Boolean, default=False)  # Permission to add topics
    can_upload_file = db.Column(db.Boolean, default=False)  # Permission to upload files
    can_sign_file = db.Column(db.Boolean, default=False)  # Permission to sign documents
    can_view_postulante_docs = db.Column(db.Boolean, default=False)  # Permission to view applicant documents
    
    # Notification fields (specific to this assignment)
    notificado = db.Column(db.Boolean, default=False)
    notificado_sustanciacion = db.Column(db.Boolean, default=False)
    fecha_notificacion = db.Column(db.DateTime, nullable=True)
    fecha_notificacion_sustanciacion = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    persona = db.relationship('Persona', back_populates='asignaciones')
    recusaciones = db.relationship('Recusacion', backref='miembro', lazy='dynamic')
    documentos = db.relationship('DocumentoTribunal', backref='miembro', lazy='dynamic')
    firmas = db.relationship('FirmaDocumento', 
                           back_populates='miembro',
                           overlaps="miembro_tribunal,firmas_realizadas",
                           lazy=True)
    
    __table_args__ = (
        db.UniqueConstraint('persona_id', 'concurso_id', name='uq_persona_concurso'),
    )

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
    domicilio = db.Column(db.String(255), nullable=True)
    estado = db.Column(db.String(50), nullable=False, default='activo')

    
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

    def is_visible_to_tribunal(self, miembro_tribunal=None):
        """
        Determine if this document should be visible to tribunal members based on configuration.
        
        Args:
            miembro_tribunal (TribunalMiembro, optional): The tribunal member to check visibility for.
                                                          If None, uses basic visibility rules.
                                                          
        Returns:
            bool: True if the document should be visible to the tribunal member
        """
        # Import here to avoid circular imports
        from app.models.models import DocumentTemplateConfig
        
        # Get the template configuration for this document type
        template_config = DocumentTemplateConfig.query.filter_by(document_type_key=self.tipo).first()
        
        # If no template configuration is found, fall back to basic visibility rules
        if not template_config or not template_config.tribunal_visibility_rules:
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
        
        # Use the configuration-based visibility rules
        try:
            rules = json.loads(template_config.tribunal_visibility_rules)
            
            # If no rules for the current state, document is not visible
            if self.estado not in rules:
                return False
                
            # If no miembro_tribunal provided, we can't check role/claustro-specific rules
            if not miembro_tribunal:
                # Return True if there are rules for this state, meaning someone should see it
                return bool(rules.get(self.estado))
            
            # Check if the member's role and claustro match the rules
            state_rules = rules.get(self.estado, {})
            allowed_roles = state_rules.get('roles', [])
            allowed_claustros = state_rules.get('claustros', [])
            
            # Document is visible if both role and claustro match the rules
            return (miembro_tribunal.rol in allowed_roles and 
                    miembro_tribunal.claustro in allowed_claustros)
                    
        except (json.JSONDecodeError, AttributeError, TypeError):
            # In case of any error parsing the rules, fall back to the document being invisible
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
    subestado_snapshot = db.Column(db.Text, nullable=True)  # Snapshot of subestado at the time of the change
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
    temas_cerrados = db.Column(db.Boolean, default=False)  # Flag to indicate if temas are closed
    
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

class NotificationCampaign(db.Model):
    __tablename__ = 'notification_campaigns'
    id = db.Column(db.Integer, primary_key=True)
    nombre_campana = db.Column(db.String(255), nullable=False)
    asunto_email = db.Column(db.String(500), nullable=False)
    cuerpo_email_html = db.Column(db.Text, nullable=False)
    destinatarios_config = db.Column(db.Text, nullable=False)  # JSON stored as text
    documentos_adjuntos_config = db.Column(db.JSON, nullable=True)  # List of dictionaries with "tipo" and "version" keys
                                                                     # Example: [{"tipo": "RESOLUCION_LLAMADO", "version": "borrador"}, 
                                                                     #           {"tipo": "ACTA_CIERRE", "version": "firmado"}]
    adjuntos_personalizados = db.Column(db.JSON, nullable=True)  # List of Google Drive IDs for custom attachments
                                                                  # Example: ["1abc123def456", "9xyz987uvw654"]
    # New fields for estado and subestado control
    estado_al_enviar = db.Column(db.String(50), nullable=True)
    subestado_al_enviar = db.Column(db.Text, nullable=True)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    actualizado_en = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    creado_por_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Relationships
    creado_por = db.relationship('User')
    logs = db.relationship('NotificationLog', back_populates='campaign', cascade="all, delete-orphan")
    
    # Helper methods to work with JSON field
    @property
    def destinatarios_json(self):
        """Return the destinatarios_config as a Python dictionary.
        
        Returns a dictionary with the following structure:
        {
            "tribunal_destinatarios": [
                {"rol": "Presidente", "claustro": "Docente"},
                {"rol": "Titular", "claustro": "Estudiante"},
                ...
            ],
            "otros_roles_destinatarios": ["postulantes", "jefe_departamento", ...],
            "emails_estaticos": ["email1@example.com", "email2@example.com", ...]
        }
        """
        if not self.destinatarios_config:
            return {'tribunal_destinatarios': [], 'otros_roles_destinatarios': [], 'emails_estaticos': []}
        return json.loads(self.destinatarios_config)
    
    @destinatarios_json.setter
    def destinatarios_json(self, value):
        """Set the destinatarios_config from a Python dictionary."""
        self.destinatarios_config = json.dumps(value)

class NotificationLog(db.Model):
    __tablename__ = 'notification_logs'
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('notification_campaigns.id', ondelete='CASCADE'), nullable=False, index=True)
    concurso_id = db.Column(db.Integer, db.ForeignKey('concursos.id', ondelete='CASCADE'), nullable=False, index=True)
    destinatario_email = db.Column(db.String(255), nullable=False)
    asunto_enviado = db.Column(db.String(500), nullable=False)
    cuerpo_enviado_html = db.Column(db.Text, nullable=False)
    fecha_envio = db.Column(db.DateTime, default=datetime.utcnow)
    estado_envio = db.Column(db.String(50), nullable=False)  # ENVIADO, FALLIDO
    error_envio = db.Column(db.Text, nullable=True)
    
    # Relationships    
    campaign = db.relationship('NotificationCampaign', back_populates='logs')
    concurso = db.relationship('Concurso')

class TemaSetTribunal(db.Model):
    """
    Stores topic proposals from individual tribunal members.
    Each tribunal member can propose up to 3 topics for a concurso.
    """
    __tablename__ = 'temas_set_tribunal'
    id = db.Column(db.Integer, primary_key=True)
    sustanciacion_id = db.Column(db.Integer, db.ForeignKey('sustanciacion.id', ondelete='CASCADE'), nullable=False)
    miembro_id = db.Column(db.Integer, db.ForeignKey('tribunal_miembros.id', ondelete='CASCADE'), nullable=False)
    temas_propuestos = db.Column(db.Text, nullable=False)  # Pipe-delimited topics: "Tema A|Tema B|Tema C"
    fecha_propuesta = db.Column(db.DateTime, default=datetime.utcnow)
    propuesta_cerrada = db.Column(db.Boolean, default=False)  # True when member has finalized their submission
    
    # Relationships
    sustanciacion = db.relationship('Sustanciacion', backref=db.backref('temas_propuestos', lazy='dynamic'))
    miembro = db.relationship('TribunalMiembro', backref=db.backref('temas_propuestos', lazy='dynamic'))
    
    __table_args__ = (
        db.UniqueConstraint('sustanciacion_id', 'miembro_id', name='uq_sustanciacion_miembro'),
    )

class DocumentTemplateConfig(db.Model):
    __tablename__ = 'document_template_configs'
    id = db.Column(db.Integer, primary_key=True)
    google_doc_id = db.Column(db.String(255), nullable=False)
    document_type_key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    display_name = db.Column(db.String(255), nullable=False)
    uses_considerandos_builder = db.Column(db.Boolean, default=False, nullable=False)
    requires_tribunal_info = db.Column(db.Boolean, default=False, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    # New fields for enhanced document template configuration
    concurso_visibility = db.Column(db.String(50), nullable=False, default='BOTH')  # REGULAR, INTERINO, BOTH
    is_unique_per_concurso = db.Column(db.Boolean, default=True, nullable=False)
    tribunal_visibility_rules = db.Column(db.Text, nullable=True)  # JSON stored as text    
    # New fields for permission control
    admin_can_send_for_signature = db.Column(db.Boolean, default=True, nullable=False)
    tribunal_can_sign = db.Column(db.Boolean, default=False, nullable=False)
    tribunal_can_upload_signed = db.Column(db.Boolean, default=False, nullable=False)
    admin_can_sign = db.Column(db.Boolean, default=False, nullable=False)
    # New fields for estado and subestado control
    estado_al_generar_borrador = db.Column(db.String(50), nullable=True)
    subestado_al_generar_borrador = db.Column(db.Text, nullable=True)
    estado_al_subir_firmado = db.Column(db.String(50), nullable=True)
    subestado_al_subir_firmado = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def get_tribunal_visibility_rules(self):
        """
        Parse and return the tribunal visibility rules as a Python dictionary.
        
        Returns:
            dict: A dictionary with document states as keys and rules for roles and claustros as values,
                  or an empty dict if no rules are defined.
        """
        if not self.tribunal_visibility_rules:
            return {}
        try:
            return json.loads(self.tribunal_visibility_rules)
        except json.JSONDecodeError:
            return {}
    
    def set_tribunal_visibility_rules(self, rules_dict):
        """
        Set the tribunal visibility rules from a Python dictionary.
        
        Args:
            rules_dict (dict): A dictionary with document states as keys and rules for roles and claustros as values.
        """
        self.tribunal_visibility_rules = json.dumps(rules_dict)
    def is_visible_for_concurso_tipo(self, tipo_concurso):
        """
        Check if this template is available for the specified concurso type.
        
        Args:
            tipo_concurso (str): The concurso type (Regular, Interino) - case insensitive
            
        Returns:
            bool: True if the template is available for this concurso type
        """
        # Make the comparison case-insensitive
        return (self.concurso_visibility.upper() == 'BOTH' or 
                self.concurso_visibility.upper() == tipo_concurso.upper())

class SorteoConfig(db.Model):
    """
    Configuration for sorteo rules based on Concurso tipo and categoria.
    Determines how many topics should be drawn in a sorteo.
    """
    __tablename__ = 'sorteo_config'
    id = db.Column(db.Integer, primary_key=True)
    concurso_tipo = db.Column(db.String(50), nullable=False)  # REGULAR, INTERINO
    categoria_codigo = db.Column(db.String(10), nullable=False)  # PAD, JTP, etc.
    numero_temas_sorteados = db.Column(db.Integer, nullable=False, default=1)
    
    __table_args__ = (
        db.UniqueConstraint('concurso_tipo', 'categoria_codigo', name='uq_sorteo_config_tipo_categoria'),
    )

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
                    rol=rol_name,
                    instructivo_postulantes=cat.get('instructivo_postulantes'),
                    instructivo_tribunal=cat.get('instructivo_tribunal')
                )
                db.session.add(categoria)
        
        db.session.commit()