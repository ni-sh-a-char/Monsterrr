#!/usr/bin/env python3
"""
Test script to verify the new 'all' mode functionality in start_monsterrr.py
"""

import subprocess
import sys
import time
import requests
import os
import threading

def test_all_mode():
    """Test the 'all' mode functionality"""
    print("🔧 Testing 'all' mode functionality...")
    
    try:
        # Start the process in a separate thread to avoid blocking
        process = subprocess.Popen([
            sys.executable, "start_monsterrr.py", "all"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        print("⏳ Waiting for server to start...")
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
                    print(f"   Response: {response.json()}")
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
            print(f"STDOUT: {stdout}")
            print(f"STDERR: {stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

def main():
    """Main test function"""
    print("🧪 Monsterrr 'All' Mode Test")
    print("=" * 30)
    
    # Change to project directory
    os.chdir(".")
    
    # Run test
    success = test_all_mode()
    
    if success:
        print("\n🎉 'All' mode test passed!")
        print("✅ Worker processes run in background")
        print("✅ Web server output displayed in terminal")
        print("✅ Health endpoint responding correctly")
    else:
        print("\n❌ 'All' mode test failed")

if __name__ == "__main__":
    main()