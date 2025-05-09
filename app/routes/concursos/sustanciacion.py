from flask import redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
import random
from app.models.models import db, Concurso, HistorialEstado
from . import concursos

@concursos.route('/<int:concurso_id>/reset-temas', methods=['POST'])
@login_required
def reset_temas(concurso_id):
    """Reset sorteo temas for a concurso. Only accessible by admin."""
    concurso = Concurso.query.get_or_404(concurso_id)
    
    if not concurso.sustanciacion:
        flash('El concurso no tiene información de sustanciación.', 'danger')
        return redirect(url_for('concursos.ver', concurso_id=concurso_id))
    
    try:
        concurso.sustanciacion.temas_exposicion = None
        
        # Add entry to history
        historial = HistorialEstado(
            concurso=concurso,
            estado="TEMAS_SORTEO_ELIMINADOS",
            observaciones=f"Temas de sorteo eliminados por administrador {current_user.username}"
        )
        db.session.add(historial)
        db.session.commit()
        
        flash('Temas de sorteo eliminados exitosamente.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar los temas: {str(e)}', 'danger')
    
    return redirect(url_for('concursos.ver', concurso_id=concurso_id))

@concursos.route('/<int:concurso_id>/realizar-sorteo', methods=['POST'])
@login_required
def realizar_sorteo(concurso_id):
    """Randomly select one tema from the list of temas_exposicion."""
    concurso = Concurso.query.get_or_404(concurso_id)
    
    if not concurso.sustanciacion or not concurso.sustanciacion.temas_exposicion:
        return jsonify({'error': 'No hay temas definidos para este concurso'}), 400
    
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
