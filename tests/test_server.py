#!/usr/bin/env python3
"""
Test script to verify server startup and port binding
"""

import os
import sys
import time
import requests
from threading import Thread

def test_server_startup():
    """Test if server starts and binds to port correctly"""
    port = os.environ.get("PORT", "8000")
    print(f"Testing server startup on port {port}")
    
    # Give the server a moment to start
    time.sleep(2)
    
    try:
        # Test health endpoint
        response = requests.get(f"http://localhost:{port}/health", timeout=5)
        print(f"Health check response: {response.status_code}")
        print(f"Health check data: {response.json()}")
        
        # Test root endpoint
        response = requests.get(f"http://localhost:{port}/", timeout=5)
        print(f"Root endpoint response: {response.status_code}")
        print(f"Root endpoint data: {response.json()}")
        
        print("✅ Server test completed successfully")
        return True
    except Exception as e:
        print(f"❌ Server test failed: {e}")
        return False

if __name__ == "__main__":
    test_server_startup()