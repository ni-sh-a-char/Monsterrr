import os
import discord
from discord.ext import commands
from groq import Groq
from dotenv import load_dotenv

# Load .env file
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DISCORD_GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", "0"))
DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", "0"))
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# Init Groq client
groq_client = Groq(api_key=GROQ_API_KEY)

# Bot setup
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ----------------- Commands -----------------
@bot.command(name="about")
async def about(ctx):
    """Simple command to verify bot is alive"""
    await ctx.send("🤖 Monsterrr Bot is alive and ready with AI chat!")

# ----------------- AI Chat Handler -----------------
@bot.event
async def on_message(message):
    # Prevent bot from replying to itself
    if message.author == bot.user:
        return

    # Let command-based messages go through
    if message.content.startswith("!"):
        await bot.process_commands(message)
        return

    # Only respond in the configured channel
    if message.channel.id != DISCORD_CHANNEL_ID:
        return

    # Show typing indicator
    async with message.channel.typing():
        try:
            response = groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": "You are Monsterrr, a helpful and fun AI assistant."},
                    {"role": "user", "content": message.content},
                ],
                temperature=0.7,
                max_tokens=200,
            )

            ai_reply = response.choices[0].message.content.strip()
            await message.channel.send(ai_reply)

        except Exception as e:
            await message.channel.send(f"⚠️ AI Error: {str(e)}")

# ----------------- Run Bot -----------------
if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise ValueError("❌ DISCORD_BOT_TOKEN missing in .env")
    bot.run(DISCORD_TOKEN)
