#!/usr/bin/env python3
"""
Test script to verify health check endpoint functionality
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/..')

def test_health_check():
    """Test the health check endpoint response"""
    try:
        # Import the health check function
        from main import health_check
        import asyncio
        
        # Run the health check function
        result = asyncio.run(health_check())
        
        # Verify the response
        assert result["status"] == "healthy", f"Expected status 'healthy', got {result['status']}"
        
        print("✅ Health check test passed")
        print(f"   Response: {result}")
        return True
        
    except Exception as e:
        print(f"❌ Health check test failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing Monsterrr Health Check Endpoint")
    print("======================================")
    
    success = test_health_check()
    
    if success:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n💥 Some tests failed!")
        sys.exit(1)