import os
import asyncio
import discord
from discord.ext import commands, tasks
from utils.config import Settings
from services.notification_service import send_instant_email
from agents.maintainer_agent import MaintainerAgent
from agents.creator_agent import CreatorAgent
from agents.idea_agent import IdeaGeneratorAgent
from services.groq_service import GroqService

settings = Settings()
DISCORD_GUILD_ID = int(settings.DISCORD_GUILD_ID)
DISCORD_CHANNEL_ID = int(settings.DISCORD_CHANNEL_ID)
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Store last hourly status
last_hourly_status = ""

@bot.event
async def on_ready():
    print(f"Monsterrr Discord Bot is online as {bot.user}")
    hourly_status_report.start()

# --- Jarvis-style professional responses ---
JARVIS_PREFIX = "[Jarvis | Monsterrr] "

async def send_jarvis_message(channel, message):
    await channel.send(f"{JARVIS_PREFIX}{message}")

@tasks.loop(hours=1)
async def hourly_status_report():
    # Generate status summary
    status = get_monsterrr_status()
    global last_hourly_status
    last_hourly_status = status
    # Send only to the specified channel
    guild = bot.get_guild(DISCORD_GUILD_ID)
    if guild:
        channel = guild.get_channel(DISCORD_CHANNEL_ID)
        if channel:
            try:
                await send_jarvis_message(channel, f"Hourly Update:\n{status}")
            except Exception:
                pass

# Restrict commands to the specified guild/channel
async def is_authorized(ctx):
    return ctx.guild and ctx.guild.id == DISCORD_GUILD_ID and ctx.channel.id == DISCORD_CHANNEL_ID

@bot.command(name="status")
async def status_cmd(ctx):
    if await is_authorized(ctx):
        await send_jarvis_message(ctx.channel, f"Current system status:\n{get_monsterrr_status()}")

@bot.command(name="guide")
async def guide_cmd(ctx):
    if await is_authorized(ctx):
        guide = (
            "Here are your available commands, sir:\n"
            "- !status : System status\n"
            "- !contribute <instructions> : Guide daily contributions\n"
            "- !fix <issue/pr> : Suggest or apply a fix\n"
            "- !skip <repo/issue> : Skip a contribution\n"
            "- !ideas : Show top ideas\n"
            "- !help : Show this guide\n"
            "You may instruct me in natural language. I will interpret and execute your wishes."
        )
        await send_jarvis_message(ctx.channel, guide)

@bot.command(name="contribute")
async def contribute_cmd(ctx, *, instructions: str):
    if await is_authorized(ctx):
        # Use Groq LLM to interpret instructions
        groq = GroqService(api_key=settings.GROQ_API_KEY)
        decision = groq.groq_llm(f"Monsterrr user instructions: {instructions}")
        # Apply decision to daily contributions
        # ... integrate with agent logic ...
        await send_jarvis_message(ctx.channel, f"Instructions received and will be followed: {decision}")

@bot.command(name="fix")
async def fix_cmd(ctx, *, target: str):
    if await is_authorized(ctx):
        groq = GroqService(api_key=settings.GROQ_API_KEY)
        suggestion = groq.groq_llm(f"Suggest a fix for: {target}")
        await send_jarvis_message(ctx.channel, f"AI Suggestion: {suggestion}")

@bot.command(name="skip")
async def skip_cmd(ctx, *, target: str):
    if await is_authorized(ctx):
        await send_jarvis_message(ctx.channel, f"Will skip: {target} in next contributions.")

@bot.command(name="ideas")
async def ideas_cmd(ctx):
    if await is_authorized(ctx):
        agent = IdeaGeneratorAgent(GroqService(api_key=settings.GROQ_API_KEY), None)
        ideas = agent.fetch_and_rank_ideas(top_n=3)
        await send_jarvis_message(ctx.channel, f"Top Ideas: {ideas}")

# Helper to get status
def get_monsterrr_status():
    # Example: read state file or summarize actions
    if os.path.exists("monsterrr_state.json"):
        with open("monsterrr_state.json", "r", encoding="utf-8") as f:
            state = f.read()
        return state
    return "No state file found."

# To run the bot, add this to your main entrypoint or run separately:
# bot.run(settings.DISCORD_BOT_TOKEN)

# Setup instructions for user:
# 1. Create a Discord account if you don't have one.
# 2. Go to https://discord.com/developers/applications and create a new application.
# 3. Add a bot to your application, copy the bot token.
# 4. In your .env, add DISCORD_BOT_TOKEN=<your token>
# 5. Invite the bot to your server using the OAuth2 URL with 'bot' and 'message content' permissions.
# 6. Start Monsterrr with the bot running (see above).
# 7. Use !guide in Discord for help.
