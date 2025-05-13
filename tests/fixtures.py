"""
Shared mock fixtures for tests
"""
import pytest
from unittest.mock import patch

@pytest.fixture
def mock_get_core_placeholders():
    """Create a fixture to mock the get_core_placeholders function."""
    # Define a sample placeholders dictionary that the function would return
    sample_placeholders = {
        'id_concurso': '1',
        'expediente': 'TEST-123/2025',
        'tipo_concurso': 'Regular',
        'area': 'Área de Prueba',
        'orientacion': 'Orientación de Prueba',
        'categoria_codigo': 'PAD',
        'categoria_nombre': 'Profesor Adjunto',
        'dedicacion': 'Simple',
        'cant_cargos_numero': '1',
        'cant_cargos_texto': 'un (1) cargo regular',
        'descripcion_cargo': 'un (1) cargo regular de Profesor Adjunto con dedicación Simple',
        'departamento_nombre': 'Departamento de Prueba',
        'origen_vacante': 'RENUNCIA',
        'docente_que_genera_vacante': 'Dr. Ejemplo Anterior',
        'nro_res_llamado_regular': '123/2025',
        
        # Tribunal data
        'tribunal_presidente': 'Tribunal, Presidente (DNI 30111111)',
        'tribunal_titulares_lista': 'Tribunal, Presidente (DNI 30111111)\nTribunal, Vocal (DNI 30222222)',
        'tribunal_suplentes_lista': 'Tribunal, Suplente (DNI 30333333)',
        
        # Postulantes data
        'postulantes_lista_completa': 'Apellido1, Postulante1 (DNI 35111111)\nApellido2, Postulante2 (DNI 35222222)',
        'postulantes_activos_lista': 'Apellido1, Postulante1 (DNI 35111111)\nApellido2, Postulante2 (DNI 35222222)',
        
        # Sustanciacion data
        'constitucion_lugar': 'Sala de Reuniones',
        'sorteo_virtual_link': 'https://meet.example.com/sorteo',
        'exposicion_fecha': '01/01/2025',
        
        # Date placeholders
        'yyyy': '2025',
        
        # Notification placeholders
        'nombre_concurso_notificacion': 'Concurso #1 - Profesor Adjunto',
    }
    
    # For persona-specific testing
    sample_placeholders_with_persona = sample_placeholders.copy()
    sample_placeholders_with_persona['nombre_destinatario'] = 'Test Usuario'
    
    # Create the mock function
    def mock_function(concurso_id, persona_id=None):
        if persona_id:
            return sample_placeholders_with_persona
        return sample_placeholders
    
    # Create the patch
    with patch('app.services.placeholder_resolver.get_core_placeholders', side_effect=mock_function) as mock:
        yield mock
