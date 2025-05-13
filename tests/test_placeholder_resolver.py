"""
Tests for the placeholder_resolver service.
"""
import pytest
from app.services.placeholder_resolver import get_core_placeholders, replace_text_with_placeholders

def test_get_core_placeholders(test_concurso, test_departamento, test_tribunal_miembros, test_postulantes, test_sustanciacion):
    """Test that the core placeholders are correctly resolved."""
    # Get placeholders for the test concurso
    placeholders = get_core_placeholders(test_concurso.id)
    
    # Test basic concurso information
    assert placeholders['id_concurso'] == str(test_concurso.id)
    assert placeholders['expediente'] == test_concurso.expediente
    assert placeholders['tipo_concurso'] == test_concurso.tipo
    assert placeholders['area'] == test_concurso.area
    assert placeholders['orientacion'] == test_concurso.orientacion
    assert placeholders['categoria_codigo'] == test_concurso.categoria
    assert placeholders['categoria_nombre'] == test_concurso.categoria_nombre
    assert placeholders['dedicacion'] == test_concurso.dedicacion
    assert placeholders['cant_cargos_numero'] == str(test_concurso.cant_cargos)
    assert placeholders['departamento_nombre'] == test_departamento.nombre
    assert placeholders['origen_vacante'] == test_concurso.origen_vacante
    assert placeholders['docente_que_genera_vacante'] == test_concurso.docente_vacante
    
    # Test complex formatted placeholders
    assert 'un (1) cargo regular de Profesor Adjunto' in placeholders['descripcion_cargo']
    assert 'un (1) cargo regular' in placeholders['cant_cargos_texto']
    
    # Test tribunal placeholders
    assert 'Tribunal, Presidente' in placeholders['tribunal_presidente']
    assert len(placeholders['tribunal_titulares_lista'].split('\n')) == 2  # Presidente + 1 vocal
    assert len(placeholders['tribunal_suplentes_lista'].split('\n')) == 1
    
    # Test postulantes placeholders
    assert len(placeholders['postulantes_lista_completa'].split('\n')) == 2
    assert len(placeholders['postulantes_activos_lista'].split('\n')) == 2
    
    # Test sustanciacion placeholders
    assert placeholders['constitucion_lugar'] == test_sustanciacion.lugar_constitucion
    assert placeholders['sorteo_virtual_link'] == test_sustanciacion.link_virtual_sorteo
    assert placeholders['exposicion_fecha'] == test_sustanciacion.fecha_clase.strftime('%d/%m/%Y')
    
    # Test date placeholders
    import datetime
    current_year = str(datetime.datetime.now().year)
    assert placeholders['yyyy'] == current_year
    
    # Test notification-specific placeholders
    assert "Concurso #" in placeholders['nombre_concurso_notificacion']
    assert "Profesor Adjunto" in placeholders['nombre_concurso_notificacion']

def test_get_core_placeholders_with_persona(test_concurso, test_persona):
    """Test that persona-specific placeholders are correctly included."""
    # Get placeholders for a specific persona
    placeholders = get_core_placeholders(test_concurso.id, persona_id=test_persona.id)
    
    # Test persona-specific placeholders
    assert placeholders['nombre_destinatario'] == f"{test_persona.nombre} {test_persona.apellido}"

def test_replace_text_with_placeholders():
    """Test that placeholders are correctly replaced in text."""
    # Create a sample dictionary of placeholders
    placeholders = {
        'name': 'John',
        'position': 'Developer',
        'company': 'ACME',
        'empty_value': None,
        'zero_value': 0
    }
    
    # Test text with single placeholders
    template1 = "Hello, <<name>>!"
    result1 = replace_text_with_placeholders(template1, placeholders)
    assert result1 == "Hello, John!"
    
    # Test text with multiple placeholders
    template2 = "<<name>> works as a <<position>> at <<company>>."
    result2 = replace_text_with_placeholders(template2, placeholders)
    assert result2 == "John works as a Developer at ACME."
    
    # Test with non-existent placeholder
    template3 = "Hello, <<name>>! Your role is <<non_existent>>."
    result3 = replace_text_with_placeholders(template3, placeholders)
    assert result3 == "Hello, John! Your role is <<non_existent>>."
    
    # Test with None value
    template4 = "Empty value: <<empty_value>>"
    result4 = replace_text_with_placeholders(template4, placeholders)
    assert result4 == "Empty value: "
    
    # Test with zero value
    template5 = "Zero value: <<zero_value>>"
    result5 = replace_text_with_placeholders(template5, placeholders)
    assert result5 == "Zero value: 0"
    
    # Test with empty text
    template6 = ""
    result6 = replace_text_with_placeholders(template6, placeholders)
    assert result6 == ""
    
    # Test with None text
    result7 = replace_text_with_placeholders(None, placeholders)
    assert result7 is None

def test_integration_with_document_generator(monkeypatch, test_concurso):
    """Test integration with document_generator."""
    from app.document_generation.document_generator import prepare_data_for_document
    
    # Mock the template config retrieval
    class MockTemplateConfig:
        def __init__(self):
            self.requires_tribunal_info = True
            self.uses_considerandos_builder = False
    
    def mock_query_filter_by(**kwargs):
        class MockQuery:
            def first(self):
                return MockTemplateConfig()
        return MockQuery()
    
    monkeypatch.setattr('app.models.models.DocumentTemplateConfig.query.filter_by', mock_query_filter_by)
    
    # Call the prepare_data_for_document function with our test concurso
    data, error = prepare_data_for_document(test_concurso.id, 'TEST_DOCUMENT_TYPE')
    
    # Verify that we got a proper data dictionary back
    assert error is None
    assert data is not None
    assert isinstance(data, dict)
    
    # Check that key placeholders are present
    assert 'expediente' in data
    assert 'departamento_nombre' in data
    assert 'descripcion_cargo' in data
    assert 'cant_cargos_texto' in data
    
    # Check backward compatibility mappings
    assert 'Expediente' in data
    assert 'departamento' in data
    assert 'cantCargos' in data
    assert 'codigo' in data
    assert 'nombre' in data
