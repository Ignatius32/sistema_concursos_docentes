"""
Simple tests for the placeholder_resolver service without database dependencies.
"""
import pytest
from app.services.placeholder_resolver import replace_text_with_placeholders

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
