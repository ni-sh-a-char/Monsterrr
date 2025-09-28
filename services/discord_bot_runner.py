import time
import logging
import os
import asyncio
import traceback
from services.discord_bot import bot

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_bot_with_retry():
    """Run the Discord bot with retry logic and better error handling"""
    max_retries = 3
    retry_delay = 30  # seconds
    
    # Get Discord token from environment variables
    discord_token = os.getenv("DISCORD_BOT_TOKEN")
    
    if not discord_token:
        logger.error("DISCORD_BOT_TOKEN not set! Discord bot will not start.")
        return
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Starting Discord bot (attempt {attempt + 1}/{max_retries})...")
            # Run the bot in a separate event loop to avoid conflicts
            import asyncio
            import threading
            
            def run_bot_loop():
                try:
                    # Create a new event loop for the bot
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    bot.run(discord_token)
                except Exception as e:
                    logger.error(f"Discord bot loop error: {e}")
                    
            bot_thread = threading.Thread(target=run_bot_loop, daemon=True)
            bot_thread.start()
            logger.info("Discord bot started in separate thread with isolated event loop")
            
            # Keep the main thread alive but don't block
            while bot_thread.is_alive():
                time.sleep(1)
                
            break  # If bot runs successfully, exit the loop
        except KeyboardInterrupt:
            logger.info("Discord bot shutdown requested.")
            break
        except Exception as e:
            logger.error(f"Discord bot failed (attempt {attempt + 1}): {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error("Max retries reached. Discord bot failed to start.")

def run_bot():
    """Run the Discord bot (wrapper for compatibility)"""
    run_bot_with_retry()

if __name__ == "__main__":
    run_bot_with_retry()