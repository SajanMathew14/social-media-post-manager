#!/usr/bin/env python3
"""
Test script to verify the configuration changes
"""
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app.core.config import settings
    
    print("✅ Configuration loaded successfully!")
    print("\nCORS Origins:")
    for origin in settings.CORS_ORIGINS:
        print(f"  - {origin}")
    
    print("\nTrusted Hosts:")
    for host in settings.TRUSTED_HOSTS:
        print(f"  - {host}")
    
    # Test that the middleware can be initialized
    from fastapi.middleware.trustedhost import TrustedHostMiddleware
    from fastapi.middleware.cors import CORSMiddleware
    
    # This would fail if the configuration is invalid
    test_app = type('TestApp', (), {})()
    
    # Test TrustedHostMiddleware
    try:
        TrustedHostMiddleware(test_app, allowed_hosts=settings.TRUSTED_HOSTS)
        print("\n✅ TrustedHostMiddleware configuration is valid!")
    except Exception as e:
        print(f"\n❌ TrustedHostMiddleware error: {e}")
        sys.exit(1)
    
    print("\n✅ All configuration tests passed!")
    
except Exception as e:
    print(f"❌ Error loading configuration: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
