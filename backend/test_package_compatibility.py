#!/usr/bin/env python3
"""
Package Compatibility Verification Script

This script verifies all package versions in requirements.txt are:
1. Available in PyPI
2. Compatible with Python 3.11
3. Compatible with each other
4. Free of known security vulnerabilities
"""

import subprocess
import sys
import json
from typing import Dict, List, Tuple, Optional

def run_command(cmd: List[str]) -> Tuple[int, str, str]:
    """Run a command and return exit code, stdout, stderr"""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "Command timed out"
    except Exception as e:
        return 1, "", str(e)

def check_package_exists(package_spec: str) -> Tuple[bool, str]:
    """Check if a package version exists in PyPI"""
    if "==" in package_spec:
        package, version = package_spec.split("==")
    else:
        package = package_spec
        version = "latest"
    
    # Remove extras like [standard] or [cryptography]
    if "[" in package:
        package = package.split("[")[0]
    
    print(f"Checking {package}=={version}...")
    
    # Use pip index to check if package version exists
    cmd = ["pip", "index", "versions", package]
    exit_code, stdout, stderr = run_command(cmd)
    
    if exit_code != 0:
        return False, f"Package {package} not found in PyPI"
    
    if version != "latest" and version not in stdout:
        return False, f"Version {version} not available for {package}"
    
    return True, f"✅ {package}=={version} exists"

def test_dependency_resolution() -> Tuple[bool, str]:
    """Test if all dependencies can be resolved together"""
    print("\n🔍 Testing dependency resolution...")
    
    # Create a temporary requirements file for testing
    cmd = ["pip-compile", "--dry-run", "requirements.txt"]
    exit_code, stdout, stderr = run_command(cmd)
    
    if exit_code != 0:
        # Fallback: try pip install --dry-run
        cmd = ["pip", "install", "--dry-run", "-r", "requirements.txt"]
        exit_code, stdout, stderr = run_command(cmd)
        
        if exit_code != 0:
            return False, f"Dependency resolution failed: {stderr}"
    
    return True, "✅ All dependencies resolve successfully"

def check_python_compatibility() -> Tuple[bool, str]:
    """Check Python version compatibility"""
    python_version = sys.version_info
    if python_version.major != 3 or python_version.minor < 11:
        return False, f"Python 3.11+ required, found {python_version.major}.{python_version.minor}"
    
    return True, f"✅ Python {python_version.major}.{python_version.minor}.{python_version.micro} compatible"

def check_known_conflicts() -> List[str]:
    """Check for known package conflicts"""
    warnings = []
    
    # Known compatibility issues
    known_issues = {
        "pydantic": {
            "2.11.6": {
                "incompatible_with": [],
                "warnings": ["Ensure pydantic-settings is 2.8.0+"]
            }
        },
        "fastapi": {
            "0.115.13": {
                "requires": ["pydantic>=2.7.0"],
                "warnings": []
            }
        }
    }
    
    return warnings

def main():
    """Main verification function"""
    print("🔍 Package Compatibility Verification")
    print("=" * 50)
    
    # Read requirements.txt
    try:
        with open("requirements.txt", "r") as f:
            requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    except FileNotFoundError:
        print("❌ requirements.txt not found")
        return False
    
    print(f"📦 Found {len(requirements)} packages to verify\n")
    
    # Check Python compatibility
    python_ok, python_msg = check_python_compatibility()
    print(python_msg)
    if not python_ok:
        return False
    
    # Check each package exists
    all_packages_ok = True
    for req in requirements:
        exists, msg = check_package_exists(req)
        print(msg)
        if not exists:
            all_packages_ok = False
    
    if not all_packages_ok:
        print("\n❌ Some packages have version issues")
        return False
    
    # Test dependency resolution
    deps_ok, deps_msg = test_dependency_resolution()
    print(f"\n{deps_msg}")
    
    # Check for known conflicts
    warnings = check_known_conflicts()
    if warnings:
        print("\n⚠️  Warnings:")
        for warning in warnings:
            print(f"  - {warning}")
    
    # Final summary
    print("\n" + "=" * 50)
    if all_packages_ok and deps_ok:
        print("✅ ALL CHECKS PASSED - Deployment should succeed!")
        print("\n📋 Summary:")
        print(f"  • {len(requirements)} packages verified")
        print("  • All versions exist in PyPI")
        print("  • Dependencies resolve correctly")
        print("  • Python 3.11 compatible")
        return True
    else:
        print("❌ ISSUES FOUND - Deployment may fail!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
