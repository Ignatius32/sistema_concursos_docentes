"""
Test script for the programas API endpoint to verify it's working properly.
This script makes a request to the new programas API endpoints.
"""
import requests
import json

def test_programa_single_endpoint():
    """Test the single programa API endpoint"""
    # Test ID
    id_materia = 1234  # Replace with a valid ID for your environment
    
    print(f"Testing single programa endpoint with ID: {id_materia}")
    
    # Make the request
    response = requests.get(f"http://localhost:5000/api/programa/{id_materia}")
    
    # Check status code
    print(f"Status code: {response.status_code}")
    
    # Print response data
    try:
        data = response.json()
        print("Response data:")
        print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"Error parsing response: {str(e)}")
        print(f"Raw response: {response.text[:500]}")

def test_programas_bulk_endpoint():
    """Test the bulk programas API endpoint"""
    # Test IDs (replace with valid IDs for your environment)
    materia_ids = [1234, 1235, 1236]
    
    print(f"Testing bulk programas endpoint with IDs: {materia_ids}")
    
    # Make the request
    response = requests.post(
        "http://localhost:5000/api/programas-bulk",
        json={"materia_ids": materia_ids}
    )
    
    # Check status code
    print(f"Status code: {response.status_code}")
    
    # Print response data
    try:
        data = response.json()
        print("Response data:")
        print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"Error parsing response: {str(e)}")
        print(f"Raw response: {response.text[:500]}")

if __name__ == "__main__":
    print("-" * 40)
    print("Testing Programas API Endpoints")
    print("-" * 40)
    
    # Test single endpoint
    test_programa_single_endpoint()
    
    print("\n" + "-" * 40 + "\n")
    
    # Test bulk endpoint
    test_programas_bulk_endpoint()
