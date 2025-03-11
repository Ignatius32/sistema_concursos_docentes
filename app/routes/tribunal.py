from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from app.models.models import db, Concurso, TribunalMiembro, Recusacion
from datetime import datetime

tribunal = Blueprint('tribunal', __name__, url_prefix='/tribunal')

@tribunal.route('/concurso/<int:concurso_id>')
@login_required
def index(concurso_id):
    """Display tribunal members for a specific concurso."""
    concurso = Concurso.query.get_or_404(concurso_id)
    miembros = TribunalMiembro.query.filter_by(concurso_id=concurso_id).all()
    return render_template('tribunal/index.html', concurso=concurso, miembros=miembros)

@tribunal.route('/concurso/<int:concurso_id>/agregar', methods=['GET', 'POST'])
@login_required
def agregar(concurso_id):
    """Add a new member to the tribunal of a concurso."""
    concurso = Concurso.query.get_or_404(concurso_id)
    
    if request.method == 'POST':
        try:
            # Extract form data
            rol = request.form.get('rol')
            nombre = request.form.get('nombre')
            apellido = request.form.get('apellido')
            dni = request.form.get('dni')
            correo = request.form.get('correo')
            
            # Create new tribunal member
            miembro = TribunalMiembro(
                concurso_id=concurso_id,
                rol=rol,
                nombre=nombre,
                apellido=apellido,
                dni=dni,
                correo=correo
            )
            
            db.session.add(miembro)
            db.session.commit()
            
            flash('Miembro del tribunal agregado exitosamente.', 'success')
            return redirect(url_for('tribunal.index', concurso_id=concurso_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al agregar miembro del tribunal: {str(e)}', 'danger')
    
    return render_template('tribunal/agregar.html', concurso=concurso)

@tribunal.route('/<int:miembro_id>/editar', methods=['GET', 'POST'])
@login_required
def editar(miembro_id):
    """Edit an existing tribunal member."""
    miembro = TribunalMiembro.query.get_or_404(miembro_id)
    concurso = Concurso.query.get_or_404(miembro.concurso_id)
    
    if request.method == 'POST':
        try:
            # Update member data from form
            miembro.rol = request.form.get('rol')
            miembro.nombre = request.form.get('nombre')
            miembro.apellido = request.form.get('apellido')
            miembro.dni = request.form.get('dni')
            miembro.correo = request.form.get('correo')
            
            db.session.commit()
            
            flash('Miembro del tribunal actualizado exitosamente.', 'success')
            return redirect(url_for('tribunal.index', concurso_id=miembro.concurso_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar miembro del tribunal: {str(e)}', 'danger')
    
    return render_template('tribunal/editar.html', miembro=miembro, concurso=concurso)

@tribunal.route('/<int:miembro_id>/eliminar', methods=['POST'])
@login_required
def eliminar(miembro_id):
    """Delete a tribunal member."""
    miembro = TribunalMiembro.query.get_or_404(miembro_id)
    concurso_id = miembro.concurso_id
    
    try:
        db.session.delete(miembro)
        db.session.commit()
        flash('Miembro del tribunal eliminado exitosamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar miembro del tribunal: {str(e)}', 'danger')
    
    return redirect(url_for('tribunal.index', concurso_id=concurso_id))

@tribunal.route('/<int:miembro_id>/recusar', methods=['GET', 'POST'])
@login_required
def recusar(miembro_id):
    """Submit a recusation against a tribunal member."""
    miembro = TribunalMiembro.query.get_or_404(miembro_id)
    concurso = Concurso.query.get_or_404(miembro.concurso_id)
    
    if request.method == 'POST':
        try:
            # Create recusation
            recusacion = Recusacion(
                concurso_id=miembro.concurso_id,
                miembro_id=miembro_id,
                motivo=request.form.get('motivo'),
                estado='PRESENTADA'
            )
            
            db.session.add(recusacion)
            db.session.commit()
            
            flash('Recusación presentada correctamente.', 'success')
            return redirect(url_for('tribunal.index', concurso_id=miembro.concurso_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al presentar recusación: {str(e)}', 'danger')
    
    return render_template('tribunal/recusar.html', miembro=miembro, concurso=concurso)