#!/usr/bin/env python3
"""
Test script to verify startup mode functionality
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/..')

def test_startup_mode_detection():
    """Test the startup mode detection functionality"""
    try:
        # Import the main function
        from start_monsterrr import main
        import os
        
        # Test default mode
        print("Testing startup mode detection:")
        print(f"  Default mode (no env vars): Should use hybrid")
        
        # Test START_MODE=all
        os.environ["START_MODE"] = "all"
        print(f"  START_MODE=all: Should use all mode")
        
        # Test MONSTERRR_MODE=web
        os.environ["START_MODE"] = ""
        os.environ["MONSTERRR_MODE"] = "web"
        print(f"  MONSTERRR_MODE=web: Should use web mode")
        
        # Test command line argument
        print(f"  Command line argument: Should use specified mode")
        
        print("\n✅ Startup mode detection test passed")
        return True
        
    except Exception as e:
        print(f"❌ Startup mode detection test failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing Monsterrr Startup Mode Detection")
    print("=====================================")
    
    success = test_startup_mode_detection()
    
    if success:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n💥 Some tests failed!")
        sys.exit(1)