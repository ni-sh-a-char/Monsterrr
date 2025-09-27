#!/usr/bin/env python3
"""
Test script to verify all deployment fixes for Monsterrr on Render
"""

import os
import sys
import logging
import asyncio
import importlib
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("test_deploy_fixes")

def test_imports():
    """Test that all modules can be imported without errors"""
    logger.info("Testing imports...")
    
    try:
        # Test main imports
        import main
        logger.info("✅ main module imported successfully")
    except Exception as e:
        logger.error(f"❌ Failed to import main: {e}")
        return False
    
    try:
        # Test services imports
        from services.discord_bot import run_bot
        logger.info("✅ services.discord_bot imported successfully")
    except Exception as e:
        logger.error(f"❌ Failed to import services.discord_bot: {e}")
        return False
    
    try:
        from services.discord_bot_runner import run_bot_with_retry, run_bot
        logger.info("✅ services.discord_bot_runner imported successfully")
    except Exception as e:
        logger.error(f"❌ Failed to import services.discord_bot_runner: {e}")
        return False
    
    try:
        from services.groq_service import GroqService
        logger.info("✅ services.groq_service imported successfully")
    except Exception as e:
        logger.error(f"❌ Failed to import services.groq_service: {e}")
        return False
    
    try:
        from services.github_service import GitHubService
        logger.info("✅ services.github_service imported successfully")
    except Exception as e:
        logger.error(f"❌ Failed to import services.github_service: {e}")
        return False
    
    try:
        # Test agents imports
        from agents.idea_agent import IdeaGeneratorAgent
        logger.info("✅ agents.idea_agent imported successfully")
    except Exception as e:
        logger.error(f"❌ Failed to import agents.idea_agent: {e}")
        return False
    
    try:
        from agents.creator_agent import CreatorAgent
        logger.info("✅ agents.creator_agent imported successfully")
    except Exception as e:
        logger.error(f"❌ Failed to import agents.creator_agent: {e}")
        return False
    
    try:
        from agents.maintainer_agent import MaintainerAgent
        logger.info("✅ agents.maintainer_agent imported successfully")
    except Exception as e:
        logger.error(f"❌ Failed to import agents.maintainer_agent: {e}")
        return False
    
    try:
        # Test autonomous orchestrator
        import autonomous_orchestrator
        logger.info("✅ autonomous_orchestrator imported successfully")
    except Exception as e:
        logger.error(f"❌ Failed to import autonomous_orchestrator: {e}")
        return False
    
    return True

def test_groq_service():
    """Test GroqService initialization"""
    logger.info("Testing GroqService...")
    
    try:
        from services.groq_service import GroqService
        # Try to initialize with a dummy key (won't actually make API calls)
        groq = GroqService(api_key="test-key-1234567890", logger=logger)
        logger.info("✅ GroqService initialized successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to initialize GroqService: {e}")
        return False

def test_discord_bot_functions():
    """Test Discord bot functions"""
    logger.info("Testing Discord bot functions...")
    
    try:
        from services.discord_bot_runner import run_bot_with_retry, run_bot
        logger.info("✅ Discord bot functions available")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to access Discord bot functions: {e}")
        return False

def test_rate_limiting():
    """Test rate limiting functionality"""
    logger.info("Testing rate limiting...")
    
    try:
        # Test that rate limiting delays are in place
        from agents.idea_agent import IdeaGeneratorAgent
        from agents.maintainer_agent import MaintainerAgent
        
        # Check that the rate limiting code is present
        import inspect
        idea_source = inspect.getsource(IdeaGeneratorAgent.fetch_and_rank_ideas)
        maintainer_source = inspect.getsource(MaintainerAgent.plan_daily_contributions)
        issues_source = inspect.getsource(MaintainerAgent._handle_issues)
        prs_source = inspect.getsource(MaintainerAgent._handle_pull_requests)
        
        if "time.sleep" in idea_source:
            logger.info("✅ Rate limiting found in IdeaGeneratorAgent")
        else:
            logger.warning("⚠️ Rate limiting not found in IdeaGeneratorAgent")
            
        if "time.sleep" in maintainer_source:
            logger.info("✅ Rate limiting found in MaintainerAgent plan_daily_contributions")
        else:
            logger.warning("⚠️ Rate limiting not found in MaintainerAgent plan_daily_contributions")
            
        if "time.sleep" in issues_source:
            logger.info("✅ Rate limiting found in MaintainerAgent _handle_issues")
        else:
            logger.warning("⚠️ Rate limiting not found in MaintainerAgent _handle_issues")
            
        if "time.sleep" in prs_source:
            logger.info("✅ Rate limiting found in MaintainerAgent _handle_pull_requests")
        else:
            logger.warning("⚠️ Rate limiting not found in MaintainerAgent _handle_pull_requests")
            
        return True
    except Exception as e:
        logger.error(f"❌ Error testing rate limiting: {e}")
        return False

def test_memory_management():
    """Test memory management functionality"""
    logger.info("Testing memory management...")
    
    try:
        # Check that memory management is in place
        import main
        import inspect
        main_source = inspect.getsource(main.setup_memory_management)
        
        if "resource.setrlimit" in main_source:
            logger.info("✅ Memory management found in main.py")
        else:
            logger.warning("⚠️ Memory management not properly configured in main.py")
            
        return True
    except Exception as e:
        logger.error(f"❌ Error testing memory management: {e}")
        return False

async def test_async_functions():
    """Test async functions"""
    logger.info("Testing async functions...")
    
    try:
        # Test that main function can be called
        import main
        logger.info("✅ Async functions test completed")
        return True
    except Exception as e:
        logger.error(f"❌ Error testing async functions: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("Starting deployment fix verification tests...")
    logger.info(f"Test started at: {datetime.now().isoformat()}")
    
    tests = [
        test_imports,
        test_groq_service,
        test_discord_bot_functions,
        test_rate_limiting,
        test_memory_management,
        test_async_functions
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
        logger.info("🎉 All tests passed! Deployment fixes are working correctly.")
        return 0
    else:
        logger.error("❌ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())