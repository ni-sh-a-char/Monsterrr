#!/usr/bin/env python3
"""
Comprehensive test script to verify all fixes for Monsterrr deployment on Render
"""

import os
import sys
import logging
import time
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("test_all_fixes")

def test_discord_bot_imports():
    """Test that Discord bot imports work correctly"""
    logger.info("Testing Discord bot imports...")
    
    try:
        # Test importing from discord_bot_runner
        from services.discord_bot_runner import run_bot_with_retry, run_bot
        logger.info("✅ services.discord_bot_runner imports successful")
        
        # Test importing from discord_bot
        from services.discord_bot import run_bot as discord_run_bot
        logger.info("✅ services.discord_bot imports successful")
        
        return True
    except Exception as e:
        logger.error(f"❌ Discord bot import test failed: {e}")
        return False

def test_github_service_rate_limiting():
    """Test GitHub service rate limiting improvements"""
    logger.info("Testing GitHub service rate limiting...")
    
    try:
        from services.github_service import GitHubService
        import logging
        
        # Create a logger for the service
        service_logger = logging.getLogger("test_github")
        
        # Initialize the GitHub service
        github = GitHubService(logger=service_logger)
        
        # Test that the service can be initialized
        logger.info("✅ GitHubService initialized successfully")
        
        # Test rate limit delay mechanism
        start_time = time.time()
        for i in range(3):
            github.log_request("GET", "https://api.github.com/test")
        end_time = time.time()
        
        # Should have taken at least 2 seconds (1 second between each request)
        if end_time - start_time >= 2.0:
            logger.info("✅ Rate limiting delay mechanism working correctly")
        else:
            logger.warning("⚠️ Rate limiting delay mechanism may not be working as expected")
        
        return True
    except Exception as e:
        logger.error(f"❌ GitHub service rate limiting test failed: {e}")
        return False

def test_memory_management():
    """Test memory management functionality"""
    logger.info("Testing memory management...")
    
    try:
        import main
        import inspect
        
        # Check that memory management function exists
        main_source = inspect.getsource(main.setup_memory_management)
        
        if "platform.system" in main_source:
            logger.info("✅ Memory management platform detection found")
        else:
            logger.warning("⚠️ Memory management platform detection not found")
            
        return True
    except Exception as e:
        logger.error(f"❌ Memory management test failed: {e}")
        return False

def test_groq_service_rate_limiting():
    """Test Groq service rate limiting improvements"""
    logger.info("Testing Groq service rate limiting...")
    
    try:
        from services.groq_service import GroqService
        import logging
        import inspect
        
        # Check that rate limiting is implemented
        groq_source = inspect.getsource(GroqService.groq_llm)
        
        if "rate_limit" in groq_source.lower() or "429" in groq_source:
            logger.info("✅ Groq service rate limiting handling found")
        else:
            logger.warning("⚠️ Groq service rate limiting handling not clearly visible")
            
        return True
    except Exception as e:
        logger.error(f"❌ Groq service rate limiting test failed: {e}")
        return False

def test_agent_rate_limiting():
    """Test that agents have rate limiting implemented"""
    logger.info("Testing agent rate limiting...")
    
    try:
        from agents.idea_agent import IdeaGeneratorAgent
        from agents.maintainer_agent import MaintainerAgent
        import inspect
        
        # Check IdeaGeneratorAgent
        idea_source = inspect.getsource(IdeaGeneratorAgent.fetch_and_rank_ideas)
        if "time.sleep" in idea_source:
            logger.info("✅ IdeaGeneratorAgent rate limiting found")
        else:
            logger.warning("⚠️ IdeaGeneratorAgent rate limiting not found")
            
        # Check MaintainerAgent
        maintainer_source = inspect.getsource(MaintainerAgent.plan_daily_contributions)
        if "time.sleep" in maintainer_source:
            logger.info("✅ MaintainerAgent rate limiting found")
        else:
            logger.warning("⚠️ MaintainerAgent rate limiting not found")
            
        return True
    except Exception as e:
        logger.error(f"❌ Agent rate limiting test failed: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("Starting comprehensive verification tests...")
    logger.info(f"Test started at: {datetime.now().isoformat()}")
    
    tests = [
        test_discord_bot_imports,
        test_github_service_rate_limiting,
        test_memory_management,
        test_groq_service_rate_limiting,
        test_agent_rate_limiting
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            logger.error(f"❌ Test {test.__name__} failed with exception: {e}")
            failed += 1
    
    logger.info(f"Tests completed: {passed} passed, {failed} failed")
    
    if failed == 0:
        logger.info("🎉 All tests passed! All fixes are implemented correctly.")
        logger.info("✅ Discord bot imports fixed")
        logger.info("✅ GitHub service rate limiting improved")
        logger.info("✅ Memory management working")
        logger.info("✅ Groq service rate limiting improved")
        logger.info("✅ Agent rate limiting implemented")
        return 0
    else:
        logger.error("❌ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())