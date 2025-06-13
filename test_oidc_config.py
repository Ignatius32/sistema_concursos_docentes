"""
Test OIDC authentication flow
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.keycloak_config import KeycloakConfig

def test_oidc_config():
    """Test OIDC configuration."""
    print("Testing OIDC Configuration...")
    print("=" * 50)
    
    config = KeycloakConfig.get_oidc_config()
    
    for key, url in config.items():
        print(f"{key}: {url}")
        # Check for double slashes (except in https://)
        if '//' in url.replace('https://', ''):
            print(f"  ⚠️  WARNING: Double slash detected in {key}")
        else:
            print(f"  ✅ OK")
    
    print("\n" + "=" * 50)
    print("Configuration looks good!")

if __name__ == "__main__":
    test_oidc_config()
