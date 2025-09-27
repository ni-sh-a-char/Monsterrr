#!/usr/bin/env python3
"""
Test script to verify Docker build and run for Monsterrr all-in-one mode
"""

import subprocess
import sys
import time
import requests
import os

def test_docker_build():
    """Test Docker image build"""
    print("🔧 Testing Docker image build...")
    try:
        result = subprocess.run(
            ["docker", "build", "-t", "monsterrr-test", "."],
            capture_output=True,
            text=True,
            cwd=".",
            timeout=300  # 5 minutes timeout
        )
        if result.returncode == 0:
            print("✅ Docker image built successfully")
            return True
        else:
            print(f"❌ Docker build failed: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("❌ Docker build timed out")
        return False
    except Exception as e:
        print(f"❌ Docker build error: {e}")
        return False

def test_docker_run():
    """Test Docker container run"""
    print("🔧 Testing Docker container run...")
    try:
        # Start container in background
        process = subprocess.Popen([
            "docker", "run", "--rm", "-p", "8000:8000", "-e", "START_MODE=all", 
            "monsterrr-test"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        print("⏳ Waiting for container to start...")
        time.sleep(10)  # Wait for container to start
        
        # Check if container is running
        result = subprocess.run(
            ["docker", "ps", "--filter", "ancestor=monsterrr-test", "--format", "{{.ID}}"],
            capture_output=True,
            text=True
        )
        
        if result.stdout.strip():
            print("✅ Docker container is running")
            container_id = result.stdout.strip()
            
            # Test health endpoint
            print("🔍 Testing health endpoint...")
            try:
                response = requests.get("http://localhost:8000/health", timeout=5)
                if response.status_code == 200:
                    print("✅ Health endpoint is responding")
                    print(f"   Response: {response.json()}")
                else:
                    print(f"❌ Health endpoint returned status {response.status_code}")
            except Exception as e:
                print(f"❌ Health endpoint test failed: {e}")
            
            # Stop container
            subprocess.run(["docker", "stop", container_id], capture_output=True)
            print("🛑 Container stopped")
            return True
        else:
            print("❌ Docker container failed to start")
            return False
            
    except Exception as e:
        print(f"❌ Docker run error: {e}")
        return False

def main():
    """Main test function"""
    print("🧪 Monsterrr Docker Test Suite")
    print("=" * 40)
    
    # Change to project directory
    os.chdir(".")
    
    # Run tests
    build_success = test_docker_build()
    if build_success:
        run_success = test_docker_run()
        if run_success:
            print("\n🎉 All Docker tests passed!")
        else:
            print("\n❌ Docker run test failed")
    else:
        print("\n❌ Docker build test failed")

if __name__ == "__main__":
    main()