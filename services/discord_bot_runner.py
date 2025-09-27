import time
import logging
import os
from services.discord_bot import bot

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_bot_with_retry():
    """Run the Discord bot with retry logic"""
    max_retries = 5
    retry_delay = 30  # seconds
    
    # Get Discord token from environment variables
    discord_token = os.getenv("DISCORD_BOT_TOKEN")
    
    for attempt in range(max_retries):
        try:
            if not discord_token:
                logger.error("DISCORD_BOT_TOKEN not set! Exiting.")
                return
            
            logger.info(f"Starting Discord bot (attempt {attempt + 1}/{max_retries})...")
            bot.run(discord_token)
            break  # If bot runs successfully, exit the loop
        except Exception as e:
            logger.error(f"Discord bot failed (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error("Max retries reached. Discord bot failed to start.")
                raise

def run_bot():
    """Run the Discord bot (wrapper for compatibility)"""
    run_bot_with_retry()

if __name__ == "__main__":
    run_bot_with_retry()