#!/usr/bin/env python3
"""
Verification script for Monsterrr installation
"""

import subprocess
import sys
import time
import requests
import os

def verify_installation():
    """Verify Monsterrr installation step by step"""
    print("🔍 Verifying Monsterrr Installation")
    print("=" * 35)
    
    # Test 1: Check if required files exist
    print("📋 Test 1: Checking required files...")
    required_files = [
        "start_monsterrr.py",
        "main.py",
        "requirements.txt",
        "Dockerfile",
        "render.yaml"
    ]
    
    missing_files = []
    for file in required_files:
        if os.path.exists(file):
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file}")
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing files: {', '.join(missing_files)}")
        return False
    else:
        print("✅ All required files present")
    
    # Test 2: Check if dependencies can be imported
    print("\n📦 Test 2: Checking Python dependencies...")
    try:
        import fastapi
        import uvicorn
        import requests
        import psutil
        print("  ✅ Core dependencies imported successfully")
    except ImportError as e:
        print(f"  ❌ Failed to import dependencies: {e}")
        return False
    
    # Test 3: Check if services can be imported
    print("\n⚙️ Test 3: Checking service modules...")
    try:
        from services.groq_service import GroqService
        from services.github_service import GitHubService
        print("  ✅ Service modules imported successfully")
    except Exception as e:
        print(f"  ❌ Failed to import service modules: {e}")
        return False
    
    # Test 4: Check if agents can be imported
    print("\n🤖 Test 4: Checking agent modules...")
    try:
        from agents.idea_agent import IdeaGeneratorAgent
        from agents.creator_agent import CreatorAgent
        from agents.maintainer_agent import MaintainerAgent
        print("  ✅ Agent modules imported successfully")
    except Exception as e:
        print(f"  ❌ Failed to import agent modules: {e}")
        return False
    
    print("\n🎉 All verification tests passed!")
    print("✅ Monsterrr is properly installed and all modules can be imported")
    print("💡 To test full functionality, run: python start_monsterrr.py all")
    print("💡 Then check http://localhost:8000/health for health status")
    
    return True

def main():
    """Main verification function"""
    success = verify_installation()
    
    if success:
        print("\n🚀 Monsterrr is ready for use!")
        print("Use one of these commands to start:")
        print("  python start_monsterrr.py all     # All services with clean output")
        print("  python start_monsterrr.py web     # Web server only")
        print("  python start_monsterrr.py worker  # Worker processes only")
        print("  python start_monsterrr.py hybrid  # Both web and worker")
    else:
        print("\n❌ Installation verification failed")
        print("Please check the error messages and fix the issues before proceeding.")

if __name__ == "__main__":
    main()