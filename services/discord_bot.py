import discord
import datetime
import json
from discord.ext import commands, tasks
from utils.config import Settings
from services.notification_service import send_instant_email
from agents.maintainer_agent import MaintainerAgent
from agents.creator_agent import CreatorAgent
from agents.idea_agent import IdeaGeneratorAgent
from services.groq_service import GroqService
from services.conversation_memory import ConversationMemory
from services.task_manager import TaskManager
from services.poll_service import PollService
from services.doc_service import DocService
from agents.custom_agent import CustomAgent
from services.integration_service import IntegrationService
from services.qa_service import QAService
from services.analytics_service import AnalyticsService
from services.merge_service import MergeService
from services.onboarding_service import OnboardingService
from services.command_builder import CommandBuilder
from services.security_service import SecurityService
from services.code_review_service import CodeReviewService
from services.language_service import LanguageService
from services.voice_service import VoiceService

settings = Settings()
DISCORD_GUILD_ID = int(settings.DISCORD_GUILD_ID)
DISCORD_CHANNEL_ID = int(settings.DISCORD_CHANNEL_ID)
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Feature instances
poll_service = PollService()
doc_service = DocService()
custom_agent = CustomAgent("CustomAgent")
integration_service = IntegrationService()
qa_service = QAService()
analytics_service = AnalyticsService()
merge_service = MergeService()
onboarding_service = OnboardingService()
command_builder = CommandBuilder()
security_service = SecurityService()
code_review_service = CodeReviewService()
language_service = LanguageService()
voice_service = VoiceService()
# Poll command
@bot.command(name="poll")
async def poll_cmd(ctx, question: str, *options):
    if await is_authorized(ctx):
        poll = poll_service.create_poll(question, options)
        await send_monsterrr_message(ctx.channel, "Poll Created", str(poll))

# Documentation update command
@bot.command(name="docs")
async def docs_cmd(ctx, repo: str):
    if await is_authorized(ctx):
        result = doc_service.update_docs(repo)
        await send_monsterrr_message(ctx.channel, "Documentation Update", result)

# Custom agent command
@bot.command(name="custom")
async def custom_cmd(ctx, *, instruction: str):
    if await is_authorized(ctx):
        result = custom_agent.act(instruction)
        await send_monsterrr_message(ctx.channel, "Custom Agent", result)

# Integration command
@bot.command(name="integrate")
async def integrate_cmd(ctx, platform: str):
    if await is_authorized(ctx):
        result = integration_service.integrate(platform)
        await send_monsterrr_message(ctx.channel, "Integration", result)

# Q&A command
@bot.command(name="qa")
async def qa_cmd(ctx, time: str):
    if await is_authorized(ctx):
        result = qa_service.schedule_qa(time)
        await send_monsterrr_message(ctx.channel, "Q&A Scheduled", result)

# Analytics dashboard command
@bot.command(name="analytics")
async def analytics_cmd(ctx):
    if await is_authorized(ctx):
        dashboard = analytics_service.get_dashboard()
        await send_monsterrr_message(ctx.channel, "Analytics Dashboard", dashboard)

# Auto-merge/close command
@bot.command(name="merge")
async def merge_cmd(ctx, pr: str):
    if await is_authorized(ctx):
        result = merge_service.auto_merge(pr)
        await send_monsterrr_message(ctx.channel, "Auto-Merge", result)

@bot.command(name="close")
async def close_cmd(ctx, issue: str):
    if await is_authorized(ctx):
        result = merge_service.auto_close(issue)
        await send_monsterrr_message(ctx.channel, "Auto-Close", result)

# Onboarding command
@bot.command(name="onboard")
async def onboard_cmd(ctx, user: str):
    if await is_authorized(ctx):
        result = onboarding_service.onboard(user)
        await send_monsterrr_message(ctx.channel, "Onboarding", result)

# Custom command builder
@bot.command(name="command")
async def command_cmd(ctx, name: str, *, action: str):
    if await is_authorized(ctx):
        result = command_builder.create_command(name, action)
        await send_monsterrr_message(ctx.channel, "Custom Command", result)

# Security scan command
@bot.command(name="scan")
async def scan_cmd(ctx, repo: str):
    if await is_authorized(ctx):
        result = security_service.scan_repo(repo)
        await send_monsterrr_message(ctx.channel, "Security Scan", result)

# Code review command
@bot.command(name="review")
async def review_cmd(ctx, pr: str):
    if await is_authorized(ctx):
        result = code_review_service.review_pr(pr)
        await send_monsterrr_message(ctx.channel, "Code Review", result)

# Multi-language support command
@bot.command(name="translate")
async def translate_cmd(ctx, lang: str, *, text: str):
    if await is_authorized(ctx):
        result = language_service.translate(text, lang)
        await send_monsterrr_message(ctx.channel, f"Translation ({lang})", result)

# Voice command integration
@bot.command(name="voice")
async def voice_cmd(ctx, audio: str):
    if await is_authorized(ctx):
        result = voice_service.process_voice(audio)
        await send_monsterrr_message(ctx.channel, "Voice Command", result)
from services.triage_service import TriageService
from services.roadmap_service import RoadmapService
from services.recognition_service import RecognitionService
from services.report_service import ReportService
from services.alert_service import AlertService
# Feature instances
triage_service = TriageService()
roadmap_service = RoadmapService()
recognition_service = RecognitionService()
report_service = ReportService()
alert_service = AlertService()
# Triage command
@bot.command(name="triage")
async def triage_cmd(ctx, item_type: str, *, item: str):
    if await is_authorized(ctx):
        if item_type == "issue":
            result = triage_service.triage_issue(item)
        elif item_type == "pr":
            result = triage_service.triage_pr(item)
        else:
            result = "Unknown item type. Use 'issue' or 'pr'."
        await send_monsterrr_message(ctx.channel, f"Triage result for {item_type}:", str(result))

# Roadmap command
@bot.command(name="roadmap")
async def roadmap_cmd(ctx, project: str):
    if await is_authorized(ctx):
        roadmap = roadmap_service.generate_roadmap(project)
        await send_monsterrr_message(ctx.channel, f"Roadmap for {project}:", '\n'.join(roadmap))

# Recognition command
@bot.command(name="recognize")
async def recognize_cmd(ctx, user: str):
    if await is_authorized(ctx):
        msg = recognition_service.recognize(user)
        await send_monsterrr_message(ctx.channel, "Recognition", msg)

# Executive report command
@bot.command(name="report")
async def report_cmd(ctx, period: str = "daily"):
    if await is_authorized(ctx):
        report = report_service.generate_report(period)
        await send_monsterrr_message(ctx.channel, f"{period.capitalize()} Report", report)

# Alert command
@bot.command(name="alert")
async def alert_cmd(ctx, *, event: str):
    if await is_authorized(ctx):
        alert = alert_service.send_alert(event)
        await send_monsterrr_message(ctx.channel, "Alert", alert)
# --- Natural language conversation handler ---
@bot.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return
    # Only respond in the configured guild/channel
    if message.guild and message.guild.id == DISCORD_GUILD_ID and message.channel.id == DISCORD_CHANNEL_ID:
        # If message starts with command prefix, let commands handle it
        if message.content.startswith(bot.command_prefix):
            await bot.process_commands(message)
        else:
            # Treat as natural language conversation, with self-awareness
            import datetime, json
            now = datetime.datetime.utcnow()
            # Load state info
            state = {}
            if os.path.exists("monsterrr_state.json"):
                with open("monsterrr_state.json", "r", encoding="utf-8") as f:
                    try:
                        state = json.load(f)
                    except Exception:
                        state = {}
            # Compose context
            next_report_time = now.replace(hour=23, minute=59, second=0, microsecond=0)
            ideas = state.get('ideas', {}).get('top_ideas', [])
            repos = state.get('repos', [])
            startup_email_sent = state.get('startup_email_sent', False)
            context = (
                f"Current UTC time: {now.strftime('%Y-%m-%d %H:%M:%S')}. "
                f"Next daily report will be sent at {next_report_time.strftime('%H:%M UTC')}. "
                f"Startup email sent: {startup_email_sent}. "
                f"Top ideas: {[i['name'] for i in ideas]}. "
                f"Repos created today: {[r['name'] for r in repos]}. "
                "You are Monsterrr, a self-aware autonomous GitHub org manager. Answer questions about your schedule, status, and actions."
            )
            groq = GroqService(api_key=settings.GROQ_API_KEY)
            prompt = f"User: {message.content}\n\nSystem: {context}"
            response = groq.groq_llm(prompt)
            await send_monsterrr_message(message.channel, "Monsterrr AI", response)
    else:
        # Allow commands in other channels/guilds
        await bot.process_commands(message)

import os
import asyncio
import discord
import datetime
import json
from discord.ext import commands, tasks
from utils.config import Settings
from services.notification_service import send_instant_email
from agents.maintainer_agent import MaintainerAgent
from agents.creator_agent import CreatorAgent
from agents.idea_agent import IdeaGeneratorAgent
from services.groq_service import GroqService
from services.conversation_memory import ConversationMemory
from services.task_manager import TaskManager

settings = Settings()
DISCORD_GUILD_ID = int(settings.DISCORD_GUILD_ID)
DISCORD_CHANNEL_ID = int(settings.DISCORD_CHANNEL_ID)
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Store last hourly status
last_hourly_status = ""

# Feature instances
memory = ConversationMemory()
task_manager = TaskManager()

@bot.event
async def on_ready():
    print(f"Monsterrr Discord Bot is online as {bot.user}")
    hourly_status_report.start()

# --- Natural language conversation handler ---
@bot.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return
    # Only respond in the configured guild/channel
    if message.guild and message.guild.id == DISCORD_GUILD_ID and message.channel.id == DISCORD_CHANNEL_ID:
        # If message starts with command prefix, let commands handle it
        if message.content.startswith(bot.command_prefix):
            await bot.process_commands(message)
        else:
            # Treat as natural language conversation, with self-awareness and memory
            now = datetime.datetime.utcnow()
            state = {}
            if os.path.exists("monsterrr_state.json"):
                with open("monsterrr_state.json", "r", encoding="utf-8") as f:
                    try:
                        state = json.load(f)
                    except Exception:
                        state = {}
            next_report_time = now.replace(hour=23, minute=59, second=0, microsecond=0)
            ideas = state.get('ideas', {}).get('top_ideas', [])
            repos = state.get('repos', [])
            startup_email_sent = state.get('startup_email_sent', False)
            # Remember conversation
            memory.remember(str(message.author.id), message.content)
            context = (
                f"Current UTC time: {now.strftime('%Y-%m-%d %H:%M:%S')}. "
                f"Next daily report will be sent at {next_report_time.strftime('%H:%M UTC')}. "
                f"Startup email sent: {startup_email_sent}. "
                f"Top ideas: {[i['name'] for i in ideas]}. "
                f"Repos created today: {[r['name'] for r in repos]}. "
                f"Conversation history: {memory.get_context(str(message.author.id))}. "
                "You are Monsterrr, a self-aware autonomous GitHub org manager. Answer questions about your schedule, status, actions, and remember user context."
            )
            groq = GroqService(api_key=settings.GROQ_API_KEY)
            prompt = f"User: {message.content}\n\nSystem: {context}"
            response = groq.groq_llm(prompt)
            await send_monsterrr_message(message.channel, "Monsterrr AI", response)
    else:
        # Allow commands in other channels/guilds
        await bot.process_commands(message)


# Task assignment command
@bot.command(name="assign")
async def assign_cmd(ctx, user: str, *, task: str):
    if await is_authorized(ctx):
        task_manager.assign_task(user, task)
        await send_monsterrr_message(ctx.channel, f"Task assigned to {user}: {task}")

@bot.command(name="tasks")
async def tasks_cmd(ctx, user: str = None):
    if await is_authorized(ctx):
        tasks = task_manager.get_tasks(user)
        if tasks:
            msg = '\n'.join([f"{t['user']}: {t['task']} [{t['status']}]" for t in tasks])
        else:
            msg = "No tasks found."
        await send_monsterrr_message(ctx.channel, f"Tasks for {user or 'all'}:", msg)
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

# --- Monsterrr professional responses ---
MONSTERRR_PREFIX = "[Monsterrr] "

def format_professional_embed(title, description, fields=None, thumbnail_url=None):
    embed = discord.Embed(title=title, description=description, color=0x2d7ff9)
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)
    if fields:
        for name, value in fields:
            embed.add_field(name=name, value=value, inline=False)
    embed.set_footer(text="Monsterrr • Autonomous GitHub Org Manager | Status at: {}".format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M')))
    return embed

async def send_monsterrr_message(channel, title, description, fields=None, thumbnail_url=None):
    embed = format_professional_embed(title, description, fields, thumbnail_url)
    await channel.send(embed=embed)

@tasks.loop(hours=1)
async def hourly_status_report():
    status = get_monsterrr_status()
    guild = bot.get_guild(DISCORD_GUILD_ID)
    if guild:
        channel = guild.get_channel(DISCORD_CHANNEL_ID)
        if channel:
            try:
                import json
                try:
                    status_data = json.loads(status)
                except Exception:
                    status_data = {}
                title = " Hourly Status Report "
                description = "**Monsterrr Autonomous Org Update**\n\nHere's a complete summary of all actions, ideas, and metrics in the last hour."
                fields = []
                thumbnail_url = "https://raw.githubusercontent.com/ni-sh-a-char/Monsterrr/main/Monsterrr.png"
                # Ideas
                if 'ideas' in status_data:
                    for i in status_data['ideas'].get('top_ideas', []):
                        roadmap = '\n'.join([f"   {step}" for step in i.get('roadmap', [])])
                        tech = ', '.join(i.get('techStack', []))
                        fields.append((f"Idea: {i['name']}", f"{i['description']}\n**Tech Stack:** {tech}\n**Difficulty:** {i.get('difficulty','')}\n**Est. Dev Time:** {i.get('estimatedDevTime','')} hrs\n**Roadmap:**\n{roadmap}"))
                # Repos
                if 'repos' in status_data:
                    for r in status_data['repos']:
                        roadmap = '\n'.join([f"   {step}" for step in r.get('roadmap', [])])
                        tech = ', '.join(r.get('tech_stack', []))
                        repo_url = r.get('url', '')
                        fields.append((f"Repo: {r['name']}", f"{r['description']}\n**Tech Stack:** {tech}\n**Roadmap:**\n{roadmap}\n[View Repo]({repo_url})"))
                # Metrics
                if 'startup_email_sent' in status_data:
                    fields.append(("Startup Email", "Sent" if status_data['startup_email_sent'] else "Not Sent"))
                # Add more metrics as needed
                await send_monsterrr_message(channel, title, description, fields, thumbnail_url)
            except Exception as e:
                await channel.send(f"Error generating hourly report: {e}")

# Restrict commands to the specified guild/channel
async def is_authorized(ctx):
    return ctx.guild and ctx.guild.id == DISCORD_GUILD_ID and ctx.channel.id == DISCORD_CHANNEL_ID

@bot.command(name="status")
async def status_cmd(ctx):
    if await is_authorized(ctx):
        status = get_monsterrr_status()
        import json
        try:
            status_data = json.loads(status)
        except Exception:
            status_data = {}
        title = " Daily Status Report "
        description = "**Monsterrr Autonomous Org Status**\n\nHere's a complete summary of all actions, ideas, and metrics for today."
        fields = []
        thumbnail_url = "https://raw.githubusercontent.com/ni-sh-a-char/Monsterrr/main/Monsterrr.png"
        # Ideas
        if 'ideas' in status_data:
            for i in status_data['ideas'].get('top_ideas', []):
                roadmap = '\n'.join([f"   {step}" for step in i.get('roadmap', [])])
                tech = ', '.join(i.get('techStack', []))
                fields.append((f"Idea: {i['name']}", f"{i['description']}\n**Tech Stack:** {tech}\n**Difficulty:** {i.get('difficulty','')}\n**Est. Dev Time:** {i.get('estimatedDevTime','')} hrs\n**Roadmap:**\n{roadmap}"))
        # Repos
        if 'repos' in status_data:
            for r in status_data['repos']:
                roadmap = '\n'.join([f"   {step}" for step in r.get('roadmap', [])])
                tech = ', '.join(r.get('tech_stack', []))
                repo_url = r.get('url', '')
                fields.append((f"Repo: {r['name']}", f"{r['description']}\n**Tech Stack:** {tech}\n**Roadmap:**\n{roadmap}\n[View Repo]({repo_url})"))
        # Metrics
        if 'startup_email_sent' in status_data:
            fields.append(("Startup Email", "Sent" if status_data['startup_email_sent'] else "Not Sent"))
        # Add more metrics as needed
        await send_monsterrr_message(ctx.channel, title, description, fields, thumbnail_url)

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
        await send_monsterrr_message(
            ctx.channel,
            "Monsterrr Guide",
            guide
        )

@bot.command(name="contribute")
async def contribute_cmd(ctx, *, instructions: str):
    if await is_authorized(ctx):
        # Use Groq LLM to interpret instructions
        groq = GroqService(api_key=settings.GROQ_API_KEY)
        decision = groq.groq_llm(f"Monsterrr user instructions: {instructions}")
        # Apply decision to daily contributions
        # ... integrate with agent logic ...
        await send_monsterrr_message(ctx.channel, f"Instructions received and will be followed: {decision}")

@bot.command(name="fix")
async def fix_cmd(ctx, *, target: str):
    if await is_authorized(ctx):
        groq = GroqService(api_key=settings.GROQ_API_KEY)
        suggestion = groq.groq_llm(f"Suggest a fix for: {target}")
        await send_monsterrr_message(ctx.channel, f"AI Suggestion: {suggestion}")

@bot.command(name="skip")
async def skip_cmd(ctx, *, target: str):
    if await is_authorized(ctx):
        await send_monsterrr_message(ctx.channel, f"Will skip: {target} in next contributions.")

@bot.command(name="ideas")
async def ideas_cmd(ctx):
    if await is_authorized(ctx):
        agent = IdeaGeneratorAgent(GroqService(api_key=settings.GROQ_API_KEY), None)
        ideas = agent.fetch_and_rank_ideas(top_n=3)
        await send_monsterrr_message(ctx.channel, f"Top Ideas: {ideas}")

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
