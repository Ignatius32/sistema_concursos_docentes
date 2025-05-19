"""
Routes for template management in the admin area.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models.models import db, DocumentTemplateConfig, User
from werkzeug.exceptions import Forbidden
import json
from datetime import datetime
from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, SubmitField, HiddenField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Length, ValidationError

# Create Blueprint
admin_templates_bp = Blueprint('admin_templates', __name__, url_prefix='/admin/templates')

# Helper function to validate JSON
def validate_json(form, field):
    if not field.data:
        return
    try:
        json.loads(field.data)
    except json.JSONDecodeError:
        raise ValidationError('El campo debe contener un JSON válido')

# Forms
class TemplateForm(FlaskForm):
    google_doc_id = StringField('ID de Google Doc', validators=[DataRequired(), Length(max=255)])
    document_type_key = StringField('Clave de Tipo de Documento', validators=[DataRequired(), Length(max=100)])
    display_name = StringField('Nombre para Mostrar', validators=[DataRequired(), Length(max=255)])
    uses_considerandos_builder = BooleanField('Usa Constructor de Considerandos')
    requires_tribunal_info = BooleanField('Requiere Información de Tribunal')
    is_active = BooleanField('Activo', default=True)
    # New fields
    concurso_visibility = SelectField('Visibilidad para Tipo de Concurso', 
                                     choices=[('BOTH', 'Ambos'), ('REGULAR', 'Regular'), ('INTERINO', 'Interino')],
                                     default='BOTH')
    is_unique_per_concurso = BooleanField('Único por Concurso', default=True)
    tribunal_visibility_rules = TextAreaField('Reglas de Visibilidad para Tribunal', 
                                             validators=[validate_json],
                                             render_kw={"rows": 10, "placeholder": '{\n  "BORRADOR": {"roles": ["Presidente", "Titular"], "claustros": ["Docente", "No Docente"]},\n  "PENDIENTE DE FIRMA": {"roles": ["Presidente", "Titular", "Suplente"], "claustros": ["Docente", "No Docente", "Estudiante", "Graduado"]},\n  "FIRMADO": {"roles": ["Presidente", "Titular", "Suplente"], "claustros": ["Docente", "No Docente", "Estudiante", "Graduado"]}\n}'})    # New permission fields
    admin_can_send_for_signature = BooleanField('Admin puede enviar para firma', default=True)
    tribunal_can_sign = BooleanField('Tribunal puede firmar', default=False)
    tribunal_can_upload_signed = BooleanField('Tribunal puede subir firmado', default=False)
    admin_can_sign = BooleanField('Administración puede firmar', default=False)
    submit = SubmitField('Guardar')

# Access control decorator
def admin_required(f):
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('No tienes permiso para acceder a esta área.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# Routes
@admin_templates_bp.route('/')
@login_required
@admin_required
def index():
    """List all templates"""
    templates = DocumentTemplateConfig.query.all()
    return render_template('admin_templates/index.html', templates=templates)

@admin_templates_bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
@admin_required
def nuevo():
    """Add a new template"""
    form = TemplateForm()    
    if form.validate_on_submit():
        template = DocumentTemplateConfig(
            google_doc_id=form.google_doc_id.data,
            document_type_key=form.document_type_key.data,
            display_name=form.display_name.data,
            uses_considerandos_builder=form.uses_considerandos_builder.data,
            requires_tribunal_info=form.requires_tribunal_info.data,
            is_active=form.is_active.data,
            # New fields
            concurso_visibility=form.concurso_visibility.data,
            is_unique_per_concurso=form.is_unique_per_concurso.data,
            tribunal_visibility_rules=form.tribunal_visibility_rules.data,
            # New permission fields
            admin_can_send_for_signature=form.admin_can_send_for_signature.data,
            tribunal_can_sign=form.tribunal_can_sign.data,
            tribunal_can_upload_signed=form.tribunal_can_upload_signed.data
        )
        db.session.add(template)
        try:
            db.session.commit()
            flash('Plantilla agregada correctamente.', 'success')
            return redirect(url_for('admin_templates.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al guardar la plantilla: {str(e)}', 'danger')
    
    return render_template('admin_templates/form.html', form=form, action='nuevo')

@admin_templates_bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def editar(id):
    """Edit an existing template"""
    template = DocumentTemplateConfig.query.get_or_404(id)
    form = TemplateForm(obj=template)
    
    if form.validate_on_submit():
        form.populate_obj(template)
        template.updated_at = datetime.utcnow()
        
        try:
            db.session.commit()
            flash('Plantilla actualizada correctamente.', 'success')
            return redirect(url_for('admin_templates.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar la plantilla: {str(e)}', 'danger')
    
    return render_template('admin_templates/form.html', form=form, template=template, action='editar')

@admin_templates_bp.route('/eliminar/<int:id>', methods=['POST'])
@login_required
@admin_required
def eliminar(id):
    """Delete a template"""
    template = DocumentTemplateConfig.query.get_or_404(id)
    try:
        db.session.delete(template)
        db.session.commit()
        flash('Plantilla eliminada correctamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar la plantilla: {str(e)}', 'danger')
    
    return redirect(url_for('admin_templates.index'))
