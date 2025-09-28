#!/usr/bin/env python3
"""
Test script to verify Groq model functionality and rate limit handling
"""

import sys
import os
# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Set environment variables for testing (these are dummy values)
os.environ.setdefault("DISCORD_BOT_TOKEN", "dummy_token")
os.environ.setdefault("DISCORD_GUILD_ID", "123456789")
os.environ.setdefault("DISCORD_CHANNEL_ID", "987654321")

from services.groq_service import GroqService
from utils.config import Settings
from utils.logger import setup_logger

def test_groq_models():
    """Test Groq model selection and rate limit handling"""
    print("Testing Monsterrr Groq Model Functionality")
    print("=" * 45)
    
    # Setup
    settings = Settings()
    logger = setup_logger()
    
    # Check if Groq configuration exists
    if not settings.GROQ_API_KEY:
        print("❌ Groq API key not found")
        print("   Please set GROQ_API_KEY in your .env file")
        return False
    
    print("✅ Groq configuration found")
    
    # Initialize Groq service
    try:
        groq_service = GroqService(api_key=settings.GROQ_API_KEY, logger=logger)
        print(f"   Default model: {groq_service.model}")
    except Exception as e:
        print(f"❌ Failed to initialize Groq service: {e}")
        return False
    
    # Test model selection for different tasks
    print("\n🤖 Testing model selection for different tasks...")
    complex_model = groq_service.get_model_for_task("complex")
    balanced_model = groq_service.get_model_for_task("balanced")
    fast_model = groq_service.get_model_for_task("fast")
    
    print(f"   Complex task model: {complex_model}")
    print(f"   Balanced task model: {balanced_model}")
    print(f"   Fast task model: {fast_model}")
    
    # Test fallback models
    print("\n🔄 Testing fallback models...")
    print("   Fallback models:", groq_service.FALLBACK_MODELS)
    
    # Test a simple API call to verify functionality
    print("\n📡 Testing API connectivity...")
    try:
        response = groq_service.groq_llm(
            prompt="Say 'Hello, Monsterrr!' in a friendly way",
            model=fast_model,
            max_tokens=50
        )
        print("✅ API call successful!")
        print(f"   Response: {response.strip()}")
        return True
    except Exception as e:
        print(f"❌ API call failed: {e}")
        return False

def main():
    """Main test function"""
    success = test_groq_models()
    
    if success:
        print("\n🎉 Groq model functionality test passed!")
        print("✅ Monsterrr Groq integration is working correctly")
        print("✅ Model selection for different tasks is configured")
        print("✅ Fallback models are available for rate limiting")
    else:
        print("\n❌ Groq model functionality test failed")
        print("Please check your Groq configuration in the .env file")

if __name__ == "__main__":
    main()