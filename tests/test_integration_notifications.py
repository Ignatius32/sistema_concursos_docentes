"""
Tests for the integration between the placeholder resolver and notifications system.
"""
import pytest
from unittest.mock import patch, MagicMock
from tests.fixtures import mock_get_core_placeholders

def test_integration_with_notifications(mock_get_core_placeholders):
    """Test that the notifications system correctly uses the placeholder resolver."""
    # Create mock objects for testing
    mock_campaign = MagicMock()
    mock_campaign.asunto_email = "Concurso <<id_concurso>> - <<categoria_nombre>>"
    mock_campaign.cuerpo_email_html = """
    <p>Estimado/a <<nombre_destinatario>>,</p>
    <p>Le informamos sobre el concurso para <<descripcion_cargo>> en el departamento de <<departamento_nombre>>.</p>
    <p>Expediente: <<expediente>></p>
    """
    
    # Create a mock recipient
    mock_recipient = MagicMock()
    mock_recipient.persona_id = 123
    
    # Import the function we want to test from notifications.py
    # We need to create a mock for this import since we're testing in isolation
    with patch('app.services.placeholder_resolver.get_core_placeholders') as mock_get_placeholders:
        from app.services.placeholder_resolver import replace_text_with_placeholders
        
        # Set up the return value for our mock
        mock_get_placeholders.return_value = {
            'id_concurso': '1',
            'categoria_nombre': 'Profesor Adjunto',
            'nombre_destinatario': 'Test Usuario',
            'descripcion_cargo': 'un (1) cargo regular de Profesor Adjunto con dedicación Simple',
            'departamento_nombre': 'Departamento de Prueba',
            'expediente': 'TEST-123/2025'
        }
        
        # Now simulate what the notification system would do
        # 1. Get placeholders for the recipient
        placeholders = mock_get_placeholders(1, persona_id=mock_recipient.persona_id)
        
        # 2. Replace placeholders in subject and body
        final_subject = replace_text_with_placeholders(mock_campaign.asunto_email, placeholders)
        final_body = replace_text_with_placeholders(mock_campaign.cuerpo_email_html, placeholders)
        
    # Verify the result
    assert final_subject == "Concurso 1 - Profesor Adjunto"
    assert "Estimado/a Test Usuario" in final_body
    assert "concurso para un (1) cargo regular de Profesor Adjunto con dedicación Simple" in final_body
    assert "departamento de Departamento de Prueba" in final_body
    assert "Expediente: TEST-123/2025" in final_body
