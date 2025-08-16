import os
import discord
from discord import app_commands
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

if not DISCORD_TOKEN:
    raise ValueError("No DISCORD_BOT_TOKEN found in .env")

# Set up intents (no message_content needed for slash commands)
intents = discord.Intents.default()
intents.guilds = True

# Create bot client
class MonsterrrBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # Sync commands with Discord
        await self.tree.sync()
        print("✅ Slash commands synced!")

bot = MonsterrrBot()

# --- Example Commands ---

@bot.tree.command(name="ping", description="Check if the bot is alive")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong! Monsterrr is alive.", ephemeral=True)

@bot.tree.command(name="status", description="Get Monsterrr status")
async def status(interaction: discord.Interaction):
    await interaction.response.send_message("📊 Monsterrr is running and ready for automation!")

@bot.tree.command(name="plan", description="Show today’s AI-generated plan")
async def plan(interaction: discord.Interaction):
    # Later you can fetch the actual AI plan JSON
    await interaction.response.send_message("📝 Today’s plan: Create repo, add feature, update dependencies.")

# Run the bot
bot.run(DISCORD_TOKEN)
