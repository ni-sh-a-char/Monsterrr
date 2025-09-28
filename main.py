import sys
from fastapi import Request, FastAPI
import requests
import threading
import time
import gc
import psutil
import asyncio
import os
# All FastAPI endpoints must be defined after app initialization
"""
Monsterrr — Autonomous GitHub Organization Manager
Entry point for starting all services (Discord bot, GitHub agent, web server, scheduler).
"""

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

# Add startup event to log when server is ready
@app.on_event("startup")
async def startup_event():
    import os
    port = os.environ.get("PORT", "8000")
    logger.info("========================================")
    logger.info("🎉 MONSTERRR WEB SERVER STARTUP COMPLETE")
    logger.info("========================================")
    logger.info(f"✅ Server listening on port {port}")
    logger.info(f"✅ Health check: http://0.0.0.0:{port}/health")
    logger.info(f"✅ API docs: http://0.0.0.0:{port}/docs")
    logger.info(f"✅ Root endpoint: http://0.0.0.0:{port}/")
    logger.info("========================================")
    logger.info("🚀 MONSTERRR IS READY TO SERVE REQUESTS")
    logger.info("========================================")

# Add shutdown event for clean shutdown logging
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("========================================")
    logger.info("🛑 MONSTERRR WEB SERVER SHUTTING DOWN")
    logger.info("========================================")

# Keep-alive mechanism to prevent Render from shutting down idle services
def start_keep_alive():
    """Start a background thread that periodically pings the service to keep it alive"""
    def ping_self():
        while True:
            try:
                # Get the port from environment variable (Render sets this)
                port = os.environ.get("PORT", "8000")
                url = f"http://localhost:{port}/health"
                response = requests.get(url, timeout=5)
                logger.info(f"[Keep-Alive] Ping successful: {response.status_code}")
            except Exception as e:
                logger.warning(f"[Keep-Alive] Ping failed: {e}")
            # Wait 5 minutes before next ping
            time.sleep(300)
    
    # Start the keep-alive thread
    try:
        keep_alive_thread = threading.Thread(target=ping_self, daemon=True)
        keep_alive_thread.start()
        port = os.environ.get("PORT", "8000")
        logger.info(f"[Keep-Alive] Started keep-alive mechanism - will ping http://localhost:{port}/health every 5 minutes")
    except Exception as e:
        logger.error(f"[Keep-Alive] Failed to start keep-alive mechanism: {e}")

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
    import psutil
    import os
    process = psutil.Process(os.getpid())
    memory_mb = process.memory_info().rss / 1024 / 1024
    
    return {
        "status": "healthy", 
        "timestamp": datetime.now().isoformat(),
        "memory_usage_mb": round(memory_mb, 2),
        "port": os.environ.get("PORT", "8000")
    }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    import os
    port = os.environ.get("PORT", "8000")
    return {
        "message": "Monsterrr — Autonomous GitHub Organization Manager is running",
        "status": "operational",
        "port": port,
        "endpoints": {
            "health": f"http://0.0.0.0:{port}/health",
            "docs": f"http://0.0.0.0:{port}/docs"
        }
    }

def setup_memory_management():
    """Setup memory management to prevent exceeding Render limits."""
    # Check if we're on a Unix-like system (Linux/Mac) that supports resource module
    import platform
    system = platform.system().lower()
    
    if system not in ['linux', 'darwin']:
        logger.info(f"[Main] Memory management not available on {system}. Skipping.")
        return
    
    try:
        import resource
        # Set memory limit (512MB for Render free tier)
        # Get current memory usage
        memory_limit = 512 * 1024 * 1024  # 512 MB in bytes
        resource.setrlimit(resource.RLIMIT_AS, (memory_limit, memory_limit))
        logger.info(f"[Main] Set memory limit to {memory_limit / (1024*1024):.0f} MB")
    except ImportError:
        logger.warning("[Main] Resource module not available. Memory management disabled.")
    except Exception as e:
        logger.warning(f"[Main] Could not set memory limit: {e}")

def get_memory_usage():
    """Get current memory usage in MB."""
    try:
        import psutil
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024
    except ImportError:
        logger.warning("[Main] psutil not available. Memory monitoring disabled.")
        return 0
    except Exception:
        return 0

def log_memory_usage():
    """Log current memory usage."""
    try:
        memory_mb = get_memory_usage()
        if memory_mb > 0:
            logger.info(f"[Main] Current memory usage: {memory_mb:.1f} MB")
    except Exception as e:
        logger.warning(f"[Main] Could not log memory usage: {e}")

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
            try:
                memory_mb = get_memory_usage()
                if memory_mb > 0:
                    logger.info(f"[Main] Memory monitor check: {memory_mb:.1f} MB")
                    
                    # If memory usage exceeds 400MB, force cleanup
                    if memory_mb > 400:
                        logger.warning(f"[Main] High memory usage detected: {memory_mb:.1f} MB. Forcing cleanup.")
                        gc.collect()
                        log_memory_usage()
            except Exception as e:
                logger.warning(f"[Main] Memory monitor error: {e}")
    
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
    
    # Start Discord bot with better isolation
    try:
        def run_discord_bot_safe():
            try:
                from services.discord_bot_runner import run_bot_with_retry
                run_bot_with_retry()
            except Exception as e:
                logger.error(f"❌ Discord bot thread error: {e}")
                
        import threading
        discord_thread = threading.Thread(target=run_discord_bot_safe, daemon=True)
        discord_thread.start()
        logger.info("✅ Discord bot started in background thread")
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
        await asyncio.gather(*tasks, return_exceptions=True)
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down Monsterrr...")
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        sys.exit(1)

def run_server():
    """Run the FastAPI server."""
    import uvicorn
    import os
    port = int(os.environ.get("PORT", "8000"))
    logger.info("========================================")
    logger.info("🚀 STARTING MONSTERRR WEB SERVER")
    logger.info("========================================")
    logger.info(f"🌍 Binding to host 0.0.0.0 on port {port}")
    logger.info(f"🔍 Health check endpoint: http://0.0.0.0:{port}/health")
    logger.info(f"📚 API documentation: http://0.0.0.0:{port}/docs")
    logger.info("🔄 Starting uvicorn server...")
    logger.info("========================================")
    
    try:
        # Configure uvicorn to bind to the correct host and port
        uvicorn.run(
            "main:app", 
            host="0.0.0.0", 
            port=port, 
            log_level="info",
            workers=1  # Use single worker to avoid conflicts
        )
    except Exception as e:
        logger.error(f"❌ Failed to start server on port {port}: {e}")
        raise

def run_worker():
    """Run the worker process."""
    asyncio.run(main())

if __name__ == "__main__":
    import sys
    import os
    
    # Check if we're running on Render
    if "RENDER" in os.environ:
        # On Render, we need to determine if this is the web or worker process
        # Based on the process name or environment variables
        if len(sys.argv) > 1 and sys.argv[1] == "web":
            logger.info("🚀 Starting Monsterrr web server")
            run_server()
        else:
            logger.info("🤖 Starting Monsterrr worker process")
            run_worker()
    else:
        # Local development - check command line arguments
        if len(sys.argv) > 1 and sys.argv[1] == "server":
            logger.info("🚀 Starting Monsterrr web server (local)")
            run_server()
        elif len(sys.argv) > 1 and sys.argv[1] == "worker":
            logger.info("🤖 Starting Monsterrr worker process (local)")
            run_worker()
        else:
            # Default behavior - run worker
            logger.info("🤖 Starting Monsterrr worker process (default)")
            run_worker()