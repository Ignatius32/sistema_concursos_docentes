"""
Test script to understand the data structure of external APIs before migrating to local storage.
This will help us understand what data we need to store locally.
"""

import requests
import json
import traceback
from datetime import datetime

# URLs from the current implementation
CONSIDERANDOS_API_URL = "https://script.google.com/macros/s/AKfycbz48ziHckZ-Ir6_gmXnUZF_S42AapQLnvpjktJXTnSbD1ps1lWimgkrxTzLXyiH_Eorlw/exec"
DEPTO_HEADS_API_URL = "https://script.google.com/macros/s/AKfycbyWU4h92lRGefLzLRSS82JhytafKIZl0jey3DuuoiCUicQcVf_1u1vzZzx7mI-0HTOg4w/exec"

def test_considerandos_api():
    """Test and analyze the considerandos API response structure."""
    print("=" * 60)
    print("TESTING CONSIDERANDOS API")
    print("=" * 60)
    
    try:
        print(f"Calling URL: {CONSIDERANDOS_API_URL}")
        response = requests.get(CONSIDERANDOS_API_URL, timeout=30)
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response Type: {type(data)}")
            print(f"Number of items: {len(data) if isinstance(data, list) else 'Not a list'}")
            
            # Save raw response to file
            with open('considerandos_response.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print("Raw response saved to considerandos_response.json")
            
            # Analyze structure
            if isinstance(data, list) and len(data) > 0:
                print("\nSample items:")
                for i, item in enumerate(data[:3]):  # Show first 3 items
                    print(f"\nItem {i+1}:")
                    print(f"Type: {type(item)}")
                    if isinstance(item, dict):
                        print(f"Keys: {list(item.keys())}")
                        for key, value in item.items():
                            print(f"  {key}: {value}")
                            
                # Analyze all unique keys across all items
                all_keys = set()
                document_types = set()
                for item in data:
                    if isinstance(item, dict):
                        all_keys.update(item.keys())
                        if 'document_type' in item:
                            document_types.add(item['document_type'])
                
                print(f"\nAll unique keys found: {sorted(all_keys)}")
                print(f"All document types found: {sorted(document_types)}")
                
        else:
            print(f"Error: HTTP {response.status_code}")
            print(f"Response text: {response.text[:500]}")
            
    except Exception as e:
        print(f"Error testing considerandos API: {str(e)}")
        traceback.print_exc()

def test_depto_heads_api():
    """Test and analyze the departamento heads API response structure."""
    print("\n" + "=" * 60)
    print("TESTING DEPARTAMENTO HEADS API")
    print("=" * 60)
    
    try:
        print(f"Calling URL: {DEPTO_HEADS_API_URL}")
        response = requests.get(DEPTO_HEADS_API_URL, timeout=30)
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response Type: {type(data)}")
            print(f"Number of items: {len(data) if isinstance(data, list) else 'Not a list'}")
            
            # Save raw response to file
            with open('depto_heads_response.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print("Raw response saved to depto_heads_response.json")
            
            # Analyze structure
            if isinstance(data, list) and len(data) > 0:
                print("\nSample items:")
                for i, item in enumerate(data[:3]):  # Show first 3 items
                    print(f"\nItem {i+1}:")
                    print(f"Type: {type(item)}")
                    if isinstance(item, dict):
                        print(f"Keys: {list(item.keys())}")
                        for key, value in item.items():
                            print(f"  {key}: {value}")
                            
                # Analyze all unique keys across all items
                all_keys = set()
                departamentos = set()
                for item in data:
                    if isinstance(item, dict):
                        all_keys.update(item.keys())
                        # Look for department-related fields
                        for key in ['departamento', 'depto', 'department', 'nombre_departamento']:
                            if key in item:
                                departamentos.add(item[key])
                
                print(f"\nAll unique keys found: {sorted(all_keys)}")
                print(f"All departamentos found: {sorted(departamentos)}")
                
        else:
            print(f"Error: HTTP {response.status_code}")
            print(f"Response text: {response.text[:500]}")
            
    except Exception as e:
        print(f"Error testing depto heads API: {str(e)}")
        traceback.print_exc()

def analyze_current_usage():
    """Analyze how these APIs are currently used in the codebase."""
    print("\n" + "=" * 60)
    print("ANALYZING CURRENT USAGE")
    print("=" * 60)
    
    print("Based on the code analysis:")
    print("\n1. CONSIDERANDOS API:")
    print("   - Used in: get_considerandos_data(document_type, tipo_concurso=None)")
    print("   - Function searches for items matching document_type")
    print("   - Returns dictionary with document information including considerandos")
    print("   - Has caching mechanism (30 minutes)")
    
    print("\n2. DEPARTAMENTO HEADS API:")
    print("   - Used in: get_departamento_heads_data()")
    print("   - Returns list of departamento heads")
    print("   - Has caching mechanism (20 minutes)")
    print("   - Used for getting department head information")
    
    print("\n3. Migration Requirements:")
    print("   - Need to store considerandos data with document_type as key")
    print("   - Need to store departamento heads data")
    print("   - Need to maintain same API interface for backward compatibility")
    print("   - Need admin interface to manage this data")

if __name__ == "__main__":
    print(f"API Data Structure Analysis - {datetime.now()}")
    print("This script will help us understand the external API data before migration.")
    
    test_considerandos_api()
    test_depto_heads_api()
    analyze_current_usage()
    
    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)
    print("Check the generated JSON files to understand the data structure.")
    print("Next steps:")
    print("1. Review the JSON files")
    print("2. Create database models based on the structure")
    print("3. Create admin interface for CRUD operations")
    print("4. Update api_services.py to use local data")
