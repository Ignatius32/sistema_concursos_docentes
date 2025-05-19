from flask import redirect, url_for, flash, jsonify, request
from flask_login import login_required, current_user
import random
from app.models.models import db, Concurso, HistorialEstado
from . import concursos

@concursos.route('/<int:concurso_id>/reset-temas', methods=['POST'])
@login_required
def reset_temas(concurso_id):
    """Reset all sorteo temas for a concurso. Only accessible by admin."""
    concurso = Concurso.query.get_or_404(concurso_id)
    
    if not concurso.sustanciacion:
        flash('El concurso no tiene información de sustanciación.', 'danger')
        return redirect(url_for('concursos.ver', concurso_id=concurso_id))
    
    try:
        # Import the TemaSetTribunal model
        from app.models.models import TemaSetTribunal
        
        # Delete all individual tema proposals for this concurso
        tema_propuestas = TemaSetTribunal.query.filter_by(
            sustanciacion_id=concurso.sustanciacion.id
        ).all()
        
        for propuesta in tema_propuestas:
            db.session.delete(propuesta)
        
        # Clear consolidated temas_exposicion
        concurso.sustanciacion.temas_exposicion = None
        
        # Always reset the temas_cerrados flag to allow tribunal to restart
        concurso.sustanciacion.temas_cerrados = False
        
        estado = "TEMAS_SORTEO_REINICIADOS"
        observaciones = f"Todos los temas de sorteo eliminados y proceso reabierto para el tribunal por administrador {current_user.username}"
        
        # Add entry to history
        historial = HistorialEstado(
            concurso=concurso,
            estado=estado,
            observaciones=observaciones
        )
        db.session.add(historial)
        db.session.commit()
        
        flash('Temas de sorteo eliminados exitosamente. El tribunal podrá cargar nuevos temas.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar los temas: {str(e)}', 'danger')
    
    return redirect(url_for('concursos.ver', concurso_id=concurso_id))

@concursos.route('/<int:concurso_id>/realizar-sorteo', methods=['POST'])
@login_required
def realizar_sorteo(concurso_id):
    """Randomly select one tema from the list of consolidated temas_exposicion."""
    concurso = Concurso.query.get_or_404(concurso_id)
    
    if not concurso.sustanciacion:
        return jsonify({'error': 'No hay información de sustanciación para este concurso'}), 400
    
    if not concurso.sustanciacion.temas_exposicion:
        return jsonify({'error': 'No hay temas consolidados para este concurso'}), 400
    
    if not concurso.sustanciacion.temas_cerrados:
        return jsonify({'error': 'La carga de temas no ha sido finalizada. Un administrador debe finalizar la carga antes de realizar el sorteo.'}), 400
    
    try:
        # Split temas by the separator and filter out empty strings
        temas = [tema.strip() for tema in concurso.sustanciacion.temas_exposicion.split('|') if tema.strip()]
        
        if not temas:
            return jsonify({'error': 'No hay temas válidos definidos'}), 400
        
        # Randomly select one tema
        selected_tema = random.choice(temas)
        
        # Save the selected tema to the database
        concurso.sustanciacion.tema_sorteado = selected_tema
        
        # Add an entry to the history
        historial = HistorialEstado(
            concurso=concurso,
            estado="TEMA_SORTEADO",
            observaciones=f"Tema sorteado: {selected_tema}"
        )
        db.session.add(historial)
        db.session.commit()
        
        # Return the selected tema and all temas
        return jsonify({
            'success': True,
            'selectedTema': selected_tema,
            'allTemas': temas
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@concursos.route('/<int:concurso_id>/reset-tema-sorteado', methods=['POST'])
@login_required
def reset_tema_sorteado(concurso_id):
    """Reset only the tema_sorteado for a concurso, keeping temas_exposicion intact."""
    concurso = Concurso.query.get_or_404(concurso_id)
    
    if not concurso.sustanciacion or not concurso.sustanciacion.tema_sorteado:
        flash('No hay tema sorteado para este concurso.', 'warning')
        return redirect(url_for('concursos.ver', concurso_id=concurso_id))
    
    try:
        # Store the tema that was reset for the history
        tema_anterior = concurso.sustanciacion.tema_sorteado
        
        # Reset only the tema_sorteado field
        concurso.sustanciacion.tema_sorteado = None
        
        # Add entry to history
        historial = HistorialEstado(
            concurso=concurso,
            estado="TEMA_SORTEADO_ELIMINADO",
            observaciones=f"Tema sorteado eliminado por administrador {current_user.username}. Tema anterior: {tema_anterior}"
        )
        db.session.add(historial)
        db.session.commit()
        
        flash('Tema sorteado eliminado exitosamente. Puede realizar un nuevo sorteo.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el tema sorteado: {str(e)}', 'danger')
    
    return redirect(url_for('concursos.ver', concurso_id=concurso_id))

@concursos.route('/<int:concurso_id>/finalizar-carga-temas', methods=['POST'])
@login_required
def finalizar_carga_temas(concurso_id):
    """Consolidate temas from all tribunal members who have closed their proposals
    and mark the global temas as closed, ready for sorteo. Only accessible by admin."""
    concurso = Concurso.query.get_or_404(concurso_id)
    
    if not concurso.sustanciacion:
        flash('El concurso no tiene información de sustanciación.', 'danger')
        return redirect(url_for('concursos.ver', concurso_id=concurso_id))
    
    # Check if already closed
    if concurso.sustanciacion.temas_cerrados:
        flash('La carga de temas ya está finalizada.', 'warning')
        return redirect(url_for('concursos.ver', concurso_id=concurso_id))
    
    try:
        # Import the TemaSetTribunal model
        from app.models.models import TemaSetTribunal, TribunalMiembro
        
        # Get all closed tema proposals
        tema_propuestas = TemaSetTribunal.query.filter_by(
            sustanciacion_id=concurso.sustanciacion.id,
            propuesta_cerrada=True
        ).all()
        
        if not tema_propuestas:
            flash('No hay propuestas de temas cerradas para consolidar. Los miembros del tribunal deben cerrar sus propuestas primero.', 'warning')
            return redirect(url_for('concursos.ver', concurso_id=concurso_id))
        
        # Option B: Pool all unique topics from all closed proposals
        all_temas = set()  # Using a set to eliminate duplicates
        
        # Parse each proposal to extract individual themes
        for propuesta in tema_propuestas:
            temas_list = [tema.strip() for tema in propuesta.temas_propuestos.split('|') if tema.strip()]
            all_temas.update(temas_list)
        
        # Convert back to string format
        consolidated_temas = '|'.join(all_temas)
        
        if not consolidated_temas:
            flash('No se encontraron temas válidos en las propuestas cerradas.', 'warning')
            return redirect(url_for('concursos.ver', concurso_id=concurso_id))
        
        # Save consolidated temas and mark as closed
        concurso.sustanciacion.temas_exposicion = consolidated_temas
        concurso.sustanciacion.temas_cerrados = True
        
        # Add entry to history with details
        contributors = ", ".join([f"{p.miembro.persona.nombre} {p.miembro.persona.apellido}" for p in tema_propuestas])
        
        historial = HistorialEstado(
            concurso=concurso,
            estado="TEMAS_SORTEO_CONSOLIDADOS",
            observaciones=f"Propuestas de temas consolidadas por administrador {current_user.username}. Miembros que aportaron temas: {contributors}"
        )
        db.session.add(historial)
        db.session.commit()
        
        flash('Temas de sorteo consolidados y finalizados exitosamente. Ya se puede realizar el sorteo.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al consolidar los temas: {str(e)}', 'danger')
    
    return redirect(url_for('concursos.ver', concurso_id=concurso_id))

@concursos.route('/<int:concurso_id>/desconsolidar-temas', methods=['POST'])
@login_required
def desconsolidar_temas(concurso_id):
    """Un-consolidate topics for a concurso. This action reverts the consolidation without deleting
    individual tribunal member proposals. Only accessible by admin."""
    concurso = Concurso.query.get_or_404(concurso_id)
    
    if not concurso.sustanciacion:
        flash('El concurso no tiene información de sustanciación.', 'danger')
        return redirect(url_for('concursos.ver', concurso_id=concurso_id))
    
    # Check if topics are currently consolidated
    if not concurso.sustanciacion.temas_cerrados:
        flash('Los temas no están actualmente consolidados.', 'warning')
        return redirect(url_for('concursos.ver', concurso_id=concurso_id))
    
    try:
        # Clear the consolidated topics and reset flags
        concurso.sustanciacion.temas_exposicion = None
        concurso.sustanciacion.temas_cerrados = False
        
        # If a topic was drawn, it's no longer valid
        if concurso.sustanciacion.tema_sorteado:
            concurso.sustanciacion.tema_sorteado = None
        
        # Add entry to history with details
        historial = HistorialEstado(
            concurso=concurso,
            estado="TEMAS_SORTEO_DESCONSOLIDADOS",
            observaciones=f"Consolidación de temas revertida por administrador {current_user.username}. Propuestas individuales conservadas."
        )
        db.session.add(historial)
        db.session.commit()
        
        flash('Consolidación de temas revertida. Las propuestas individuales están conservadas. Puede gestionar propuestas individuales o re-consolidar.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al desconsolidar los temas: {str(e)}', 'danger')
    
    return redirect(url_for('concursos.ver', concurso_id=concurso_id))
