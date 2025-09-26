import sys
from fastapi import Request, FastAPI
import requests
import threading
import time
import gc
import psutil
import asyncio
# All FastAPI endpoints must be defined after app initialization
"""
Monsterrr — Autonomous GitHub Organization Manager
Entry point for starting all services (Discord bot, GitHub agent, web server, scheduler).
"""

import os
import logging
from datetime import datetime, timezone, timedelta
IST = timezone(timedelta(hours=5, minutes=30))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("monsterrr")

# Initialize FastAPI app
app = FastAPI()

# Keep-alive mechanism to prevent Render from shutting down idle services
def start_keep_alive():
    """Start a background thread that periodically pings the service to keep it alive"""
    def ping_self():
        while True:
            try:
                # Get the port from environment variable (Render sets this)
                port = os.environ.get("PORT", "8000")
                url = f"http://localhost:{port}"
                response = requests.get(url, timeout=5)
                logger.info(f"[Keep-Alive] Ping successful: {response.status_code}")
            except Exception as e:
                logger.warning(f"[Keep-Alive] Ping failed: {e}")
            # Wait 5 minutes before next ping
            time.sleep(300)
    
    # Start the keep-alive thread
    keep_alive_thread = threading.Thread(target=ping_self, daemon=True)
    keep_alive_thread.start()
    logger.info("[Keep-Alive] Started keep-alive mechanism")

# Import services
from services.discord_bot import run_bot as run_discord_bot
from services.github_service import GitHubService
from services.groq_service import GroqService
from utils.config import Settings

# Import agents
from agents.idea_agent import IdeaGeneratorAgent
from agents.creator_agent import CreatorAgent
from agents.maintainer_agent import MaintainerAgent

# Import autonomous orchestrator
import autonomous_orchestrator

# Health check endpoint for Render
@app.get("/health")
async def health_check():
    """Health check endpoint for Render"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Monsterrr — Autonomous GitHub Organization Manager is running"}

def setup_memory_management():
    """Setup memory management to prevent exceeding Render limits."""
    import resource
    
    # Set memory limit (512MB for Render free tier)
    try:
        # Get current memory usage
        memory_limit = 512 * 1024 * 1024  # 512 MB in bytes
        resource.setrlimit(resource.RLIMIT_AS, (memory_limit, memory_limit))
        logger.info(f"[Main] Set memory limit to {memory_limit / (1024*1024):.0f} MB")
    except Exception as e:
        logger.warning(f"[Main] Could not set memory limit: {e}")

def get_memory_usage():
    """Get current memory usage in MB."""
    try:
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024
    except Exception:
        return 0

def log_memory_usage():
    """Log current memory usage."""
    memory_mb = get_memory_usage()
    logger.info(f"[Main] Current memory usage: {memory_mb:.1f} MB")

def periodic_memory_cleanup():
    """Periodically clean up memory to prevent leaks."""
    def cleanup():
        # Force garbage collection
        collected = gc.collect()
        logger.info(f"[Main] Garbage collected {collected} objects")
        
        # Log current memory usage
        log_memory_usage()
            
    # Schedule cleanup every 15 minutes (reduced from 30 for better memory management)
    async def cleanup_task():
        while True:
            await asyncio.sleep(900)  # 15 minutes
            cleanup()
    
    return cleanup_task()

async def memory_monitor():
    """Monitor memory usage and force cleanup if approaching limits."""
    async def monitor_task():
        while True:
            await asyncio.sleep(300)  # Check every 5 minutes
            memory_mb = get_memory_usage()
            logger.info(f"[Main] Memory monitor check: {memory_mb:.1f} MB")
            
            # If memory usage exceeds 400MB, force cleanup
            if memory_mb > 400:
                logger.warning(f"[Main] High memory usage detected: {memory_mb:.1f} MB. Forcing cleanup.")
                gc.collect()
                log_memory_usage()
    
    return monitor_task()

async def main():
    """Main entry point."""
    logger.info("🚀 Starting Monsterrr — Autonomous GitHub Organization Manager")
    
    # Start keep-alive mechanism
    start_keep_alive()
    
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
        github_service.groq_client = groq_service  # Pass Groq client to GitHub service
        
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
    
    # Start all services
    tasks = []
    
    # Start Discord bot
    try:
        from services.discord_bot_runner import run_discord_bot
        discord_task = asyncio.create_task(run_discord_bot())
        tasks.append(discord_task)
        logger.info("✅ Discord bot started")
    except Exception as e:
        logger.error(f"❌ Failed to start Discord bot: {e}")
    
    # Start autonomous orchestrator
    try:
        import autonomous_orchestrator
        orchestrator_task = asyncio.create_task(autonomous_orchestrator.daily_orchestration())
        tasks.append(orchestrator_task)
        logger.info("✅ Autonomous orchestrator started")
    except Exception as e:
        logger.error(f"❌ Failed to start autonomous orchestrator: {e}")
    
    # Start periodic memory cleanup
    try:
        cleanup_task = asyncio.create_task(periodic_memory_cleanup())
        tasks.append(cleanup_task)
        logger.info("✅ Memory cleanup task started")
    except Exception as e:
        logger.error(f"❌ Failed to start memory cleanup task: {e}")
    
    # Start memory monitor
    try:
        monitor_task = asyncio.create_task(memory_monitor())
        tasks.append(monitor_task)
        logger.info("✅ Memory monitor task started")
    except Exception as e:
        logger.error(f"❌ Failed to start memory monitor task: {e}")
    
    # Run all tasks
    try:
        logger.info("✅ All services started successfully")
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down Monsterrr...")
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())