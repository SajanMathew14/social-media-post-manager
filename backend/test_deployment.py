#!/usr/bin/env python3
"""
Quick test script to verify the FastAPI backend is working properly
Run this before deploying to Render to catch any issues early
"""

import sys
import subprocess
import importlib.util
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8+ required")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    return True

def check_requirements():
    """Check if all required packages are installed"""
    requirements_file = Path(__file__).parent / "requirements.txt"
    
    if not requirements_file.exists():
        print("❌ requirements.txt not found")
        return False
    
    print("📦 Checking requirements...")
    
    # Read requirements
    with open(requirements_file) as f:
        requirements = [line.strip().split('==')[0] for line in f if line.strip() and not line.startswith('#')]
    
    missing = []
    for package in requirements:
        if importlib.util.find_spec(package.replace('-', '_')) is None:
            missing.append(package)
    
    if missing:
        print(f"❌ Missing packages: {', '.join(missing)}")
        print("Run: pip install -r requirements.txt")
        return False
    
    print("✅ All requirements installed")
    return True

def check_app_imports():
    """Check if the FastAPI app can be imported"""
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from app.main import app
        print("✅ FastAPI app imports successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to import app: {e}")
        return False

def check_health_endpoint():
    """Test the health endpoint"""
    try:
        from app.main import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        response = client.get("/health")
        
        if response.status_code == 200:
            print("✅ Health endpoint working")
            print(f"   Response: {response.json()}")
            return True
        else:
            print(f"❌ Health endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health endpoint test failed: {e}")
        return False

def main():
    """Run all checks"""
    print("🔍 Testing FastAPI Backend for Render Deployment")
    print("=" * 50)
    
    checks = [
        ("Python Version", check_python_version),
        ("Requirements", check_requirements),
        ("App Import", check_app_imports),
        ("Health Endpoint", check_health_endpoint),
    ]
    
    all_passed = True
    for name, check_func in checks:
        print(f"\n{name}:")
        if not check_func():
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All checks passed! Ready for Render deployment")
        print("\nNext steps:")
        print("1. Follow RENDER_DEPLOYMENT_FIX.md")
        print("2. Create new Python service with Root Directory = backend")
        print("3. Use: uvicorn app.main:app --host 0.0.0.0 --port $PORT")
    else:
        print("❌ Some checks failed. Fix issues before deploying")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
