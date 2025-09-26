#!/usr/bin/env python3
"""
Test script to verify Monsterrr components can be imported and initialized correctly.
"""

import os
import sys
import logging

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("test_run")

def test_imports():
    """Test that all modules can be imported."""
    logger.info("Testing module imports...")
    
    try:
        import main
        logger.info("✅ main module imported successfully")
    except Exception as e:
        logger.error(f"❌ Failed to import main module: {e}")
        return False
    
    try:
        import autonomous_orchestrator
        logger.info("✅ autonomous_orchestrator module imported successfully")
    except Exception as e:
        logger.error(f"❌ Failed to import autonomous_orchestrator module: {e}")
        return False
    
    try:
        from services.discord_bot import run_bot
        logger.info("✅ Discord bot module imported successfully")
    except Exception as e:
        logger.error(f"❌ Failed to import Discord bot module: {e}")
        return False
    
    try:
        from services.github_service import GitHubService
        logger.info("✅ GitHub service module imported successfully")
    except Exception as e:
        logger.error(f"❌ Failed to import GitHub service module: {e}")
        return False
    
    try:
        from services.groq_service import GroqService
        logger.info("✅ Groq service module imported successfully")
    except Exception as e:
        logger.error(f"❌ Failed to import Groq service module: {e}")
        return False
    
    try:
        from agents.idea_agent import IdeaGeneratorAgent
        logger.info("✅ Idea agent module imported successfully")
    except Exception as e:
        logger.error(f"❌ Failed to import Idea agent module: {e}")
        return False
    
    try:
        from agents.creator_agent import CreatorAgent
        logger.info("✅ Creator agent module imported successfully")
    except Exception as e:
        logger.error(f"❌ Failed to import Creator agent module: {e}")
        return False
    
    try:
        from agents.maintainer_agent import MaintainerAgent
        logger.info("✅ Maintainer agent module imported successfully")
    except Exception as e:
        logger.error(f"❌ Failed to import Maintainer agent module: {e}")
        return False
    
    return True

def test_initialization():
    """Test that services can be initialized."""
    logger.info("Testing service initialization...")
    
    try:
        from utils.config import Settings
        settings = Settings()
        logger.info("✅ Settings loaded successfully")
        
        # Validate settings
        try:
            settings.validate()
            logger.info("✅ Settings validated successfully")
        except Exception as e:
            logger.error(f"❌ Settings validation failed: {e}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Failed to load settings: {e}")
        return False
    
    try:
        from services.groq_service import GroqService
        groq_service = GroqService(api_key=settings.GROQ_API_KEY, logger=logger)
        logger.info("✅ Groq service initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Groq service: {e}")
        return False
    
    try:
        from services.github_service import GitHubService
        github_service = GitHubService(logger=logger)
        logger.info("✅ GitHub service initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize GitHub service: {e}")
        return False
    
    return True

def main():
    """Main test function."""
    logger.info("🚀 Starting Monsterrr component test")
    
    if not test_imports():
        logger.error("❌ Import tests failed")
        return 1
    
    if not test_initialization():
        logger.error("❌ Initialization tests failed")
        return 1
    
    logger.info("✅ All tests passed! Monsterrr components are working correctly.")
    return 0

if __name__ == "__main__":
    sys.exit(main())