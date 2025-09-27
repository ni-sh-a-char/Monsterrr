#!/usr/bin/env python3
"""
Test script to verify Monsterrr installation and functionality
"""

import subprocess
import sys
import time
import requests
import os

def test_all_mode():
    """Test the 'all' mode functionality"""
    print("🔧 Testing Monsterrr 'all' mode functionality...")
    
    try:
        # Start the process
        process = subprocess.Popen([
            sys.executable, "start_monsterrr.py", "all"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        print("⏳ Waiting for server to start (15 seconds)...")
        time.sleep(15)  # Wait for server to start
        
        # Check if process is still running
        if process.poll() is None:
            print("✅ Server process is running")
            
            # Test health endpoint
            print("🔍 Testing health endpoint...")
            try:
                response = requests.get("http://localhost:8000/health", timeout=5)
                if response.status_code == 200:
                    print("✅ Health endpoint is responding")
                    data = response.json()
                    print(f"   Status: {data.get('status')}")
                    print(f"   Memory Usage: {data.get('memory_usage_mb')} MB")
                    print(f"   Port: {data.get('port')}")
                    success = True
                else:
                    print(f"❌ Health endpoint returned status {response.status_code}")
                    success = False
            except Exception as e:
                print(f"❌ Health endpoint test failed: {e}")
                success = False
            
            # Terminate the process
            print("🛑 Terminating server process...")
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            print("✅ Server process terminated")
            
            return success
        else:
            stdout, stderr = process.communicate()
            print(f"❌ Server process exited with code {process.returncode}")
            if stdout:
                print(f"STDOUT: {stdout}")
            if stderr:
                print(f"STDERR: {stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

def main():
    """Main test function"""
    print("🧪 Monsterrr Installation Test")
    print("=" * 35)
    
    # Change to project directory
    os.chdir(".")
    
    # Run test
    success = test_all_mode()
    
    if success:
        print("\n🎉 All tests passed!")
        print("✅ Monsterrr is properly installed and functional")
        print("✅ All services can be started with 'all' mode")
        print("✅ Health endpoint is responding correctly")
    else:
        print("\n❌ Installation test failed")
        print("Please check the error messages above and verify your installation.")

if __name__ == "__main__":
    main()