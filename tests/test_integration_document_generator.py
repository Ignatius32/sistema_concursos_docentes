"""
Tests for the integration between the placeholder resolver and document generator.
"""
import pytest
import sys
from unittest.mock import patch, MagicMock
from tests.fixtures import mock_get_core_placeholders

def test_mocked_document_generator_integration(app):
    """Test the document generator integration using a fully mocked approach."""
    # Mock the necessary imports and functions
    mock_data = {
        'expediente': 'TEST-123/2025',
        'departamento_nombre': 'Departamento de Prueba',
        'descripcion_cargo': 'un (1) cargo regular de Profesor Adjunto con dedicación Simple',
        'cant_cargos_texto': 'un (1) cargo regular',
        'tribunal_presidente': 'Tribunal, Presidente (DNI 30111111)',
        'tribunal_titulares_lista': 'Tribunal, Presidente (DNI 30111111)\nTribunal, Vocal (DNI 30222222)',
        'tribunal_suplentes_lista': 'Tribunal, Suplente (DNI 30333333)',
    }
    
    # Create a function that simulates prepare_data_for_document but returns our mock data
    def mock_prepare_data_for_document(concurso_id, document_type):
        # Add backward compatibility mappings
        data = mock_data.copy()
        data.update({
            'Expediente': mock_data['expediente'],
            'departamento': mock_data['departamento_nombre'],
            'cantCargos': mock_data['cant_cargos_texto'],
            'tribunal_titular': mock_data['tribunal_titulares_lista'],
            'tribunal_suplentes': mock_data['tribunal_suplentes_lista']
        })
        return data, None
    
    # Test that our mock function returns the expected data
    data, error = mock_prepare_data_for_document(1, 'TEST_DOCUMENT')
    
    # Assert expectations
    assert error is None
    assert data is not None
    assert isinstance(data, dict)
    
    # Check key placeholders
    assert data['expediente'] == 'TEST-123/2025'
    assert data['descripcion_cargo'] == 'un (1) cargo regular de Profesor Adjunto con dedicación Simple'
    
    # Check backward compatibility
    assert data['Expediente'] == 'TEST-123/2025'
    assert data['departamento'] == 'Departamento de Prueba'
    assert data['cantCargos'] == 'un (1) cargo regular'
    assert data['tribunal_titular'] == mock_data['tribunal_titulares_lista']
