"""
Routes for template management in the admin area.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, make_response
from app.models.models import db, DocumentTemplateConfig
from app.utils.keycloak_auth import keycloak_login_required, admin_required
from werkzeug.exceptions import Forbidden
import json
from datetime import datetime
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
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
    # New fields    c
    concurso_visibility = SelectField('Visibilidad para Tipo de Concurso', 
                                     choices=[('BOTH', 'Ambos'), ('REGULAR', 'Regular'), ('INTERINO', 'Interino')],
                                     default='BOTH')
    is_unique_per_concurso = BooleanField('Único por Concurso', default=True)
    tribunal_visibility_rules = TextAreaField('Reglas de Visibilidad para Tribunal', 
                                             validators=[validate_json],
                                             render_kw={"rows": 10, "placeholder": '{\n  "BORRADOR": {"roles": ["Presidente", "Titular"], "claustros": ["Docente", "No Docente"]},\n  "PENDIENTE DE FIRMA": {"roles": ["Presidente", "Titular", "Suplente"], "claustros": ["Docente", "No Docente", "Estudiante", "Graduado"]},\n  "FIRMADO": {"roles": ["Presidente", "Titular", "Suplente"], "claustros": ["Docente", "No Docente", "Estudiante", "Graduado"]}\n}'})
    public_visibility_rules = TextAreaField('Reglas de Visibilidad Pública', 
                                           validators=[validate_json],
                                           render_kw={"rows": 6, "placeholder": '{\n  "BORRADOR": false,\n  "PENDIENTE DE FIRMA": false,\n  "FIRMADO": true\n}'})
    # New permission fields
    admin_can_send_for_signature = BooleanField('Admin puede enviar para firma', default=True)
    tribunal_can_sign = BooleanField('Tribunal puede firmar', default=False)
    tribunal_can_upload_signed = BooleanField('Tribunal puede subir firmado', default=False)
    admin_can_sign = BooleanField('Administración puede firmar', default=False)    # New fields for estado and subestado control
    estado_al_generar_borrador = StringField('Estado al generar documento borrador', validators=[Length(max=50)])
    subestado_al_generar_borrador = TextAreaField('Subestado al generar documento borrador', 
                                                render_kw={"rows": 3, "placeholder": 'Valor que se agregará a subestado'})
    estado_al_subir_firmado = StringField('Estado al subir firmado', validators=[Length(max=50)])
    subestado_al_subir_firmado = TextAreaField('Subestado al subir firmado', 
                                             render_kw={"rows": 3, "placeholder": 'Valor que se agregará a subestado'})    # New document properties fields
    subida_directa = BooleanField('Permite subida directa', default=False)
    es_res = BooleanField('Es una resolución', default=False)
    parentesco = StringField('Parentesco', validators=[Length(max=255)])
    submit = SubmitField('Guardar')

class ImportForm(FlaskForm):
    import_file = FileField('Archivo de Configuración', 
                           validators=[FileRequired(), FileAllowed(['json'], 'Solo archivos JSON permitidos')])
    overwrite_existing = BooleanField('Sobrescribir plantillas existentes', default=False)
    submit = SubmitField('Importar')

# Access control decorator - now using Keycloak auth directly in routes
# The admin_required decorator from keycloak_auth handles both authentication and authorization

# Routes
@admin_templates_bp.route('/')
@keycloak_login_required
@admin_required
def index():
    """List all templates"""
    templates = DocumentTemplateConfig.query.all()
    return render_template('admin_templates/index.html', templates=templates)

@admin_templates_bp.route('/export')
@keycloak_login_required
@admin_required
def export_templates():
    """Export all template configurations as JSON"""
    templates = DocumentTemplateConfig.query.all()
    
    # Convert templates to dictionary format
    templates_data = []
    for template in templates:
        template_dict = {
            'google_doc_id': template.google_doc_id,
            'document_type_key': template.document_type_key,
            'display_name': template.display_name,
            'uses_considerandos_builder': template.uses_considerandos_builder,
            'requires_tribunal_info': template.requires_tribunal_info,
            'is_active': template.is_active,
            'concurso_visibility': template.concurso_visibility,
            'is_unique_per_concurso': template.is_unique_per_concurso,
            'tribunal_visibility_rules': template.tribunal_visibility_rules,
            'public_visibility_rules': template.public_visibility_rules,
            'admin_can_send_for_signature': template.admin_can_send_for_signature,
            'tribunal_can_sign': template.tribunal_can_sign,
            'tribunal_can_upload_signed': template.tribunal_can_upload_signed,
            'admin_can_sign': template.admin_can_sign,
            'estado_al_generar_borrador': template.estado_al_generar_borrador,
            'subestado_al_generar_borrador': template.subestado_al_generar_borrador,
            'estado_al_subir_firmado': template.estado_al_subir_firmado,
            'subestado_al_subir_firmado': template.subestado_al_subir_firmado,
            'subida_directa': template.subida_directa,
            'es_res': template.es_res,
            'parentesco': template.parentesco,
            # Include metadata
            'created_at': template.created_at.isoformat() if template.created_at else None,
            'updated_at': template.updated_at.isoformat() if template.updated_at else None
        }
        templates_data.append(template_dict)
    
    # Create export data with metadata
    export_data = {
        'export_metadata': {
            'export_date': datetime.utcnow().isoformat(),
            'total_templates': len(templates_data),
            'version': '1.0'
        },
        'templates': templates_data
    }
    
    # Create response with JSON file download
    response = make_response(json.dumps(export_data, indent=2, ensure_ascii=False))
    response.headers['Content-Type'] = 'application/json'
    response.headers['Content-Disposition'] = f'attachment; filename=template_configurations_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.json'
    
    flash(f'Configuraciones de plantillas exportadas exitosamente. {len(templates_data)} plantillas incluidas.', 'success')
    return response

@admin_templates_bp.route('/import', methods=['GET', 'POST'])
@keycloak_login_required
@admin_required
def import_templates():
    """Import template configurations from JSON"""
    form = ImportForm()
    
    if form.validate_on_submit():
        try:
            # Read the uploaded file
            file_content = form.import_file.data.read().decode('utf-8')
            import_data = json.loads(file_content)
            
            # Validate the import data structure
            if 'templates' not in import_data:
                flash('El archivo JSON debe contener una clave "templates".', 'danger')
                return render_template('admin_templates/import.html', form=form)
            
            templates_data = import_data['templates']
            imported_count = 0
            updated_count = 0
            skipped_count = 0
            errors = []
            
            for template_data in templates_data:
                try:
                    # Check if template already exists
                    existing_template = DocumentTemplateConfig.query.filter_by(
                        document_type_key=template_data.get('document_type_key')
                    ).first()
                    
                    if existing_template and not form.overwrite_existing.data:
                        skipped_count += 1
                        continue
                    
                    # Prepare template data (excluding metadata fields)
                    template_fields = {
                        'google_doc_id': template_data.get('google_doc_id'),
                        'document_type_key': template_data.get('document_type_key'),
                        'display_name': template_data.get('display_name'),
                        'uses_considerandos_builder': template_data.get('uses_considerandos_builder', False),
                        'requires_tribunal_info': template_data.get('requires_tribunal_info', False),
                        'is_active': template_data.get('is_active', True),
                        'concurso_visibility': template_data.get('concurso_visibility', 'BOTH'),
                        'is_unique_per_concurso': template_data.get('is_unique_per_concurso', True),
                        'tribunal_visibility_rules': template_data.get('tribunal_visibility_rules'),
                        'public_visibility_rules': template_data.get('public_visibility_rules'),
                        'admin_can_send_for_signature': template_data.get('admin_can_send_for_signature', True),
                        'tribunal_can_sign': template_data.get('tribunal_can_sign', False),
                        'tribunal_can_upload_signed': template_data.get('tribunal_can_upload_signed', False),
                        'admin_can_sign': template_data.get('admin_can_sign', False),
                        'estado_al_generar_borrador': template_data.get('estado_al_generar_borrador'),
                        'subestado_al_generar_borrador': template_data.get('subestado_al_generar_borrador'),
                        'estado_al_subir_firmado': template_data.get('estado_al_subir_firmado'),
                        'subestado_al_subir_firmado': template_data.get('subestado_al_subir_firmado'),
                        'subida_directa': template_data.get('subida_directa', False),
                        'es_res': template_data.get('es_res', False),
                        'parentesco': template_data.get('parentesco')
                    }
                    
                    if existing_template:
                        # Update existing template
                        for field, value in template_fields.items():
                            setattr(existing_template, field, value)
                        existing_template.updated_at = datetime.utcnow()
                        updated_count += 1
                    else:
                        # Create new template
                        template = DocumentTemplateConfig(**template_fields)
                        template.created_at = datetime.utcnow()
                        template.updated_at = datetime.utcnow()
                        db.session.add(template)
                        imported_count += 1
                        
                except Exception as e:
                    errors.append(f"Error procesando plantilla {template_data.get('document_type_key', 'desconocida')}: {str(e)}")
            
            # Commit changes
            db.session.commit()
            
            # Show results
            success_msg = []
            if imported_count > 0:
                success_msg.append(f"{imported_count} plantillas importadas")
            if updated_count > 0:
                success_msg.append(f"{updated_count} plantillas actualizadas")
            if skipped_count > 0:
                success_msg.append(f"{skipped_count} plantillas omitidas (ya existían)")
                
            if success_msg:
                flash(f"Importación completada: {', '.join(success_msg)}.", 'success')
            
            if errors:
                for error in errors:
                    flash(error, 'warning')
                    
            return redirect(url_for('admin_templates.index'))
            
        except json.JSONDecodeError:
            flash('El archivo no contiene un JSON válido.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al importar las configuraciones: {str(e)}', 'danger')
    
    return render_template('admin_templates/import.html', form=form)

@admin_templates_bp.route('/nuevo', methods=['GET', 'POST'])
@keycloak_login_required
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
            public_visibility_rules=form.public_visibility_rules.data,
            # New permission fields
            admin_can_send_for_signature=form.admin_can_send_for_signature.data,
            tribunal_can_sign=form.tribunal_can_sign.data,
            tribunal_can_upload_signed=form.tribunal_can_upload_signed.data,
            admin_can_sign=form.admin_can_sign.data,            # New estado and subestado fields
            estado_al_generar_borrador=form.estado_al_generar_borrador.data,
            subestado_al_generar_borrador=form.subestado_al_generar_borrador.data,
            estado_al_subir_firmado=form.estado_al_subir_firmado.data,
            subestado_al_subir_firmado=form.subestado_al_subir_firmado.data,            # New document properties fields
            subida_directa=form.subida_directa.data,
            es_res=form.es_res.data,
            parentesco=form.parentesco.data
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
@keycloak_login_required
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
@keycloak_login_required
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
