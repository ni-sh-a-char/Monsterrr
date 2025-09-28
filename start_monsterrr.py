#!/usr/bin/env python3
"""
Unified startup script for Monsterrr that can run both web server and worker processes.
This script determines the mode based on environment variables and starts the appropriate services.
"""

import os
import sys
import asyncio
import logging
import signal
import threading
from typing import List

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("monsterrr-runner")

def run_web_server():
    """Run the FastAPI web server."""
    logger.info("🚀 Starting Monsterrr Web Server")
    try:
        # Import and run the web server
        from main import run_server
        run_server()
    except Exception as e:
        logger.error(f"❌ Failed to start web server: {e}")
        sys.exit(1)

def run_worker():
    """Run the worker process."""
    logger.info("🤖 Starting Monsterrr Worker Process")
    try:
        # Import and run the worker
        from main import run_worker
        run_worker()
    except Exception as e:
        logger.error(f"❌ Failed to start worker: {e}")
        sys.exit(1)

def run_hybrid():
    """Run both web server and worker in a single process."""
    logger.info("🔄 Starting Monsterrr Hybrid Mode (Web + Worker)")
    
    try:
        # Import required modules
        from main import app, setup_memory_management, log_memory_usage, Settings
        from services.groq_service import GroqService
        from services.github_service import GitHubService
        from agents.idea_agent import IdeaGeneratorAgent
        from agents.creator_agent import CreatorAgent
        from agents.maintainer_agent import MaintainerAgent
        import uvicorn
        import threading
        import asyncio
        import time
        
        # Setup memory management
        setup_memory_management()
        log_memory_usage()
        
        # Validate configuration
        settings = Settings()
        try:
            settings.validate()
            logger.info("✅ Configuration validated")
        except Exception as e:
            logger.error(f"❌ Configuration validation failed: {e}")
            sys.exit(1)
        
        # Initialize services
        try:
            groq_service = GroqService(api_key=settings.GROQ_API_KEY, logger=logger)
            github_service = GitHubService(logger=logger)
            github_service.groq_client = groq_service
            
            # Test GitHub credentials
            github_service.validate_credentials()
            logger.info("✅ GitHub service initialized")
            
            # Initialize agents
            idea_agent = IdeaGeneratorAgent(groq_service, logger)
            creator_agent = CreatorAgent(github_service, logger)
            maintainer_agent = MaintainerAgent(github_service, groq_service, logger)
            logger.info("✅ Agents initialized")
            
        except Exception as e:
            logger.error(f"❌ Service initialization failed: {e}")
            sys.exit(1)
        
        # Start background services with better error handling
        def start_background_services():
            try:
                # Import and start Discord bot with better error handling
                def run_discord_safe():
                    try:
                        from services.discord_bot_runner import run_bot_with_retry
                        run_bot_with_retry()
                    except Exception as e:
                        logger.error(f"❌ Discord bot error: {e}")
                
                discord_thread = threading.Thread(target=run_discord_safe, daemon=True)
                discord_thread.start()
                logger.info("✅ Discord bot started in background with isolated event loop")
                
                # Import and start autonomous orchestrator
                try:
                    import autonomous_orchestrator
                    def run_orchestrator_safe():
                        try:
                            # Create a new event loop for the orchestrator
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            loop.run_until_complete(autonomous_orchestrator.daily_orchestration())
                        except Exception as e:
                            logger.error(f"❌ Orchestrator error: {e}")
                    
                    orchestrator_thread = threading.Thread(target=run_orchestrator_safe, daemon=True)
                    orchestrator_thread.start()
                    logger.info("✅ Autonomous orchestrator started in background with isolated event loop")
                except Exception as e:
                    logger.error(f"❌ Failed to start orchestrator: {e}")
                
            except Exception as e:
                logger.error(f"❌ Failed to start background services: {e}")
        
        # Start background services
        start_background_services()
        
        # Give background services a moment to start
        time.sleep(3)
        
        # Start web server in main thread
        port = int(os.environ.get("PORT", "8000"))
        logger.info(f"🚀 Starting web server on port {port}")
        
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=port,
            log_level="info",
            workers=1
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to start hybrid mode: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)

def run_all_background():
    """Run the entire project with workers in background and show only web results in terminal."""
    logger.info("🌟 Starting Monsterrr All-in-One Mode")
    logger.info("🤖 Running worker processes in background")
    logger.info("🌐 Web server output will be displayed in terminal")
    
    try:
        # Import required modules
        from main import app, setup_memory_management, log_memory_usage, Settings
        from services.groq_service import GroqService
        from services.github_service import GitHubService
        from agents.idea_agent import IdeaGeneratorAgent
        from agents.creator_agent import CreatorAgent
        from agents.maintainer_agent import MaintainerAgent
        import uvicorn
        import threading
        import asyncio
        import subprocess
        import sys
        
        # Setup memory management for web server
        setup_memory_management()
        log_memory_usage()
        
        # Validate configuration
        settings = Settings()
        try:
            settings.validate()
            logger.info("✅ Configuration validated")
        except Exception as e:
            logger.error(f"❌ Configuration validation failed: {e}")
            sys.exit(1)
        
        # Start background services in separate threads for better control
        def start_background_services():
            try:
                # Import and start Discord bot
                from services.discord_bot_runner import run_bot_with_retry
                def run_discord():
                    try:
                        run_bot_with_retry()
                    except Exception as e:
                        logger.error(f"❌ Discord bot error: {e}")
                
                discord_thread = threading.Thread(target=run_discord, daemon=True)
                discord_thread.start()
                logger.info("✅ Discord bot started in background")
                
                # Import and start autonomous orchestrator
                import autonomous_orchestrator
                def run_orchestrator():
                    try:
                        asyncio.run(autonomous_orchestrator.daily_orchestration())
                    except Exception as e:
                        logger.error(f"❌ Orchestrator error: {e}")
                
                orchestrator_thread = threading.Thread(target=run_orchestrator, daemon=True)
                orchestrator_thread.start()
                logger.info("✅ Autonomous orchestrator started in background")
                
            except Exception as e:
                logger.error(f"❌ Failed to start background services: {e}")
        
        # Start background services
        start_background_services()
        
        # Give background services a moment to start
        import time
        time.sleep(2)
        
        # Start web server in main thread with full output
        port = int(os.environ.get("PORT", "8000"))
        logger.info("========================================")
        logger.info("🚀 STARTING MONSTERRR WEB SERVER")
        logger.info("========================================")
        logger.info(f"🌍 Binding to host 0.0.0.0 on port {port}")
        logger.info(f"🔍 Health check endpoint: http://0.0.0.0:{port}/health")
        logger.info(f"📚 API documentation: http://0.0.0.0:{port}/docs")
        logger.info("🔄 Starting uvicorn server...")
        logger.info("========================================")
        
        # Run the web server in the main thread (output will be visible)
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=port,
            log_level="info",
            workers=1
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to start all-in-one mode: {e}")
        sys.exit(1)

def main():
    """Main entry point."""
    logger.info("🚀 Starting Monsterrr - Autonomous GitHub Organization Manager")
    
    # Determine mode based on environment variables
    mode = os.environ.get("MONSTERRR_MODE", "hybrid").lower()
    start_mode = os.environ.get("START_MODE", "").lower()
    
    # Priority order for mode determination:
    # 1. START_MODE environment variable (for Docker/Render compatibility)
    # 2. MONSTERRR_MODE environment variable (new approach)
    # 3. Command line argument
    # 4. Default to hybrid
    
    if start_mode == "web":
        mode = "web"
    elif start_mode == "worker":
        mode = "worker"
    elif start_mode == "all":
        mode = "all"
    elif len(sys.argv) > 1:
        mode = sys.argv[1].lower()
    
    logger.info(f"🔧 Starting in {mode} mode")
    
    if mode == "web":
        run_web_server()
    elif mode == "worker":
        run_worker()
    elif mode == "hybrid":
        run_hybrid()
    elif mode == "all":
        run_all_background()
    else:
        logger.error(f"❌ Unknown mode: {mode}. Use 'web', 'worker', 'hybrid', or 'all'")
        sys.exit(1)

if __name__ == "__main__":
    main()