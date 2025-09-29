#!/usr/bin/env python3
"""
Test script to verify smart model switching functionality
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/..')

def test_model_switching():
    """Test the smart model switching functionality"""
    try:
        # Import the GroqService
        from services.groq_service import GroqService
        
        # Create a GroqService instance
        groq_service = GroqService(api_key="test_key")
        
        # Test model groups
        print("Model Groups:")
        print(f"  HIGH_PERFORMANCE_MODELS: {groq_service.HIGH_PERFORMANCE_MODELS}")
        print(f"  BALANCED_MODELS: {groq_service.BALANCED_MODELS}")
        print(f"  FAST_MODELS: {groq_service.FAST_MODELS}")
        print(f"  FALLBACK_MODELS: {groq_service.FALLBACK_MODELS}")
        
        # Test get_model_for_task method
        print("\nModel Selection for Tasks:")
        complex_model = groq_service.get_model_for_task("complex")
        balanced_model = groq_service.get_model_for_task("balanced")
        fast_model = groq_service.get_model_for_task("fast")
        default_model = groq_service.get_model_for_task("unknown")
        
        print(f"  Complex task: {complex_model}")
        print(f"  Balanced task: {balanced_model}")
        print(f"  Fast task: {fast_model}")
        print(f"  Default task: {default_model}")
        
        # Verify the models are correctly selected
        assert complex_model == groq_service.HIGH_PERFORMANCE_MODELS[0], "Complex task should use high performance model"
        assert balanced_model == groq_service.BALANCED_MODELS[0], "Balanced task should use balanced model"
        assert fast_model == groq_service.FAST_MODELS[0], "Fast task should use fast model"
        assert default_model == groq_service.model, "Default task should use default model"
        
        print("\n✅ Model switching test passed")
        return True
        
    except Exception as e:
        print(f"❌ Model switching test failed: {e}")
        return False

def test_rate_limit_handling():
    """Test rate limit handling functionality"""
    try:
        # Import the GroqService
        from services.groq_service import GroqService
        
        # Check if rate limit handling methods exist
        groq_service = GroqService(api_key="test_key")
        
        # Check for rate limit handling methods
        has_rate_limit_handling = hasattr(groq_service, '_make_request_with_backoff')
        
        print(f"Rate limit handling method exists: {has_rate_limit_handling}")
        
        if has_rate_limit_handling:
            print("✅ Rate limit handling test passed")
            return True
        else:
            print("❌ Rate limit handling test failed - missing method")
            return False
        
    except Exception as e:
        print(f"❌ Rate limit handling test failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing Monsterrr Smart Model Switching")
    print("=====================================")
    
    success1 = test_model_switching()
    success2 = test_rate_limit_handling()
    
    if success1 and success2:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n💥 Some tests failed!")
        sys.exit(1)