import requests
import json

# URL to fetch departamento heads data
DEPTO_HEADS_API_URL = "https://script.google.com/macros/s/AKfycbyWU4h92lRGefLzLRSS82JhytafKIZl0jey3DuuoiCUicQcVf_1u1vzZzx7mI-0HTOg4w/exec"

try:
    response = requests.get(DEPTO_HEADS_API_URL)
    if response.status_code != 200:
        print(f"Error {response.status_code}: Could not retrieve data")
    else:
        data = response.json()
        print("Raw API response structure:")
        print(json.dumps(data, indent=2))
        
        # Check if data has 'value' property
        if isinstance(data, dict) and 'value' in data:
            print("\nValue property contains:")
            print(json.dumps(data['value'], indent=2))
            heads_data = data['value']
        else:
            print("\nNo 'value' property, using data directly:")
            heads_data = data
        
        # Print department heads in a more readable format
        print("\nDepartment heads data:")
        for head in heads_data:
            print(f"Department: {head.get('departamento', 'N/A')}")
            print(f"  Responsable: {head.get('responsable', 'N/A')}")
            print(f"  Prefijo: {head.get('prefijo', 'N/A')}")
            print("---")
        
except Exception as e:
    print(f"Error: {str(e)}")
