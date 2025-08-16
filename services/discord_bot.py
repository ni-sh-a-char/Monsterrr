
"""
Monsterrr Discord Bot - Ultra Self-Aware AI Assistant

Features:
- Responds to both commands (with '!') and normal chat (without '!')
- Friendly greeting for first-time users
- Per-user conversation memory (last 10 messages)
- Maximally self-aware: answers about its own state, schedule, resources, user engagement
- Tracks startup time, uptime, last/next report, model, total messages, recent users/messages
- System introspection: Python version, OS, CPU/memory/disk usage, process stats, loaded modules, env vars, hostname, IP
- Professional embed responses for status/help
- Robust error handling
"""

import os
import discord
from discord.ext import commands
from groq import Groq
import platform
import psutil
import sys
import socket
import datetime
from collections import defaultdict, deque
import asyncio
# Monsterrr services
from .task_manager import TaskManager
from .triage_service import TriageService
from .poll_service import PollService
from .report_service import ReportService
from .recognition_service import RecognitionService
from .qa_service import QAService
from .security_service import SecurityService
from .roadmap_service import RoadmapService
from .onboarding_service import OnboardingService
from .merge_service import MergeService
from .language_service import LanguageService
from .doc_service import DocService
from .conversation_memory import ConversationMemory
from .integration_service import IntegrationService
from .github_service import GitHubService
from .groq_service import GroqService

MEMORY_LIMIT = 10
conversation_memory = defaultdict(lambda: deque(maxlen=MEMORY_LIMIT))
STARTUP_TIME = datetime.datetime.utcnow()
total_messages = 0
unique_users = set()

# --- Service Instances ---
task_manager = TaskManager()
triage_service = TriageService()
poll_service = PollService()
report_service = ReportService()
recognition_service = RecognitionService()
qa_service = QAService()
security_service = SecurityService()
roadmap_service = RoadmapService()
onboarding_service = OnboardingService()
merge_service = MergeService()
language_service = LanguageService()
doc_service = DocService()
conversation_memory_service = ConversationMemory()
integration_service = IntegrationService()
# github_service and groq_service require logger, use None for now
github_service = GitHubService(logger=None)
groq_service = GroqService(logger=None)


# ...existing code...

# Load tokens/keys from environment
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GUILD_ID = os.getenv("DISCORD_GUILD_ID")   # optional
CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")  # optional

# Intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

# Bot with "!" command prefix
bot = commands.Bot(command_prefix="!", intents=intents)

# Groq client
client = Groq(api_key=GROQ_API_KEY)

STARTUP_MESSAGE_SENT = False

async def send_startup_message():
    global STARTUP_MESSAGE_SENT, task_assignments, polls, contributor_stats, security_alerts, custom_commands, qa_sessions
    if STARTUP_MESSAGE_SENT:
        return
    await asyncio.sleep(2)  # Wait for Discord cache to be ready
    channel_id = CHANNEL_ID or None
    if channel_id:
        channel = bot.get_channel(int(channel_id))
        if channel:
            status_text = f"""
**🤖 Monsterrr System Status**
Startup time: {STARTUP_TIME.strftime('%Y-%m-%d %H:%M:%S UTC')}
Model: llama-3.3-70b-versatile
Ready to help!

**Discord Stats:**
• Guilds: {len(bot.guilds)}
• Total members: {sum(guild.member_count for guild in bot.guilds)}
"""
            embed = format_embed("Monsterrr is online!", status_text, 0x00ff00)
            await channel.send(embed=embed)
            STARTUP_MESSAGE_SENT = True
        else:
            print(f"[Monsterrr] Could not find channel {channel_id} for startup message.")
    # ...existing code...


# =============================
# Monsterrr Feature Scaffold
# =============================

# 1. Conversation Memory (already present)
# 2. Task Assignment & Tracking
@bot.command(name="assign")
async def assign_task(ctx, user: discord.Member, *, task: str):
    task_manager.assign_task(str(user), task)
    await ctx.send(f"Task assigned to {user.mention}: {task}")

# 3. Automated Issue & PR Triage
@bot.command(name="triage")
async def triage_issues(ctx, *, issue_text: str = None):
    if not issue_text:
        await ctx.send("Please provide issue text.")
        return
    result = triage_service.triage_issue(issue_text)
    await ctx.send(f"Triage result: {result}")

# 4. Project Roadmap Generation
@bot.command(name="roadmap")
async def generate_roadmap(ctx, *, project: str = "Monsterrr"): 
    roadmap = roadmap_service.generate_roadmap(project)
    await ctx.send("\n".join(roadmap))

# 5. Contributor Recognition
@bot.command(name="recognize")
async def recognize_contributors(ctx, user: discord.Member = None):
    if user:
        msg = recognition_service.recognize(str(user))
        await ctx.send(msg)
    else:
        await ctx.send("Please mention a user to recognize.")

# 6. Weekly/Monthly Executive Reports
@bot.command(name="report")
async def executive_report(ctx, period: str = "weekly"):
    report = report_service.generate_report(period)
    await ctx.send(report)

# 7. Real-Time Alerts
@bot.command(name="alerts")
async def real_time_alerts(ctx):
    await ctx.send("Real-time alerts enabled. (Demo)")

# 8. Idea Voting & Polls
@bot.command(name="poll")
async def idea_poll(ctx, *, question: str):
    poll = poll_service.create_poll(question, ["Yes", "No", "Maybe"])
    await ctx.send(f"Poll started: {poll['question']}\nOptions: {', '.join(poll['options'])}")

@bot.command(name="ideas")
async def ideas_command(ctx):
    polls = poll_service.polls
    if not polls:
        await ctx.send("No ideas/polls found.")
        return
    msg = "Active Ideas/Polls:\n" + "\n".join([f"{i+1}. {p['question']}" for i, p in enumerate(polls)])
    await ctx.send(msg)
# 9. Automated Documentation Updates
@bot.command(name="status")
async def status(ctx):
    user_id = str(ctx.author.id)
    context = get_system_context(user_id)
    guild_count = len(bot.guilds)
    member_count = sum(guild.member_count for guild in bot.guilds)
    next_actions = ["Monitor new issues and PRs", "Send onboarding to new contributors", "Run hourly analytics and reporting", "Check for security alerts", "Update documentation if needed"]
    recent_actions = [f"Processed {total_messages} messages", f"Assigned {len(task_manager.get_tasks())} tasks", f"Created {len(poll_service.polls)} polls", f"Recognized {len(recognition_service.log)} contributors", f"Sent {len(security_service.log)} security alerts"]
    status_text = f"""
    **🤖 Monsterrr System Status**
    {context}

    **Discord Stats:**
    • Guilds: {guild_count}
    • Total members: {member_count}
    • Unique users interacted: {len(unique_users)}

    **Recent Actions:**
    • " + "\n• ".join(recent_actions) + "\n"

    **Next Actions:**
    • " + "\n• ".join(next_actions) + "\n"

    **Active Features:**
    • Tasks assigned: {len(task_manager.get_tasks())}
    • Active polls: {len(poll_service.polls)}
    • Custom commands: {len(custom_commands)}
    • Security alerts: {len(security_service.log)}
    • QA sessions scheduled: {len(qa_service.sessions)}
    """
    embed = format_embed("Monsterrr Detailed Status", status_text, 0x00ff00)
    await ctx.send(embed=embed)
    status_text = f"""
    **🤖 Monsterrr System Status**
    {context}

    **Discord Stats:**
    • Guilds: {guild_count}
    • Total members: {member_count}
    • Unique users interacted: {len(unique_users)}

    **Recent Actions:**
    • " + "\n• ".join(recent_actions) + "\n"

    **Next Actions:**
    • " + "\n• ".join(next_actions) + "\n"

    **Active Features:**
    • Tasks assigned: {sum(len(tasks) for tasks in task_assignments.values())}
    • Active polls: {len(polls)}
    • Custom commands: {len(custom_commands)}
    • Security alerts: {len(security_alerts)}
    • QA sessions scheduled: {len(qa_sessions)}
    """
    embed = format_embed("Monsterrr Detailed Status", status_text, 0x00ff00)
    await ctx.send(embed=embed)

@bot.command(name="analytics")
async def analytics_dashboard(ctx):
    await ctx.send("Analytics dashboard generated. (Demo)")

# 14. Auto-merge & Auto-close Rules
@bot.command(name="automerge")
async def auto_merge(ctx, pr: str = None):
    if not pr:
        await ctx.send("Please provide PR identifier.")
        return
    msg = merge_service.auto_merge(pr)
    await ctx.send(msg)

# 15. Onboarding Automation
@bot.command(name="onboard")
async def onboarding(ctx, user: discord.Member):
    msg = onboarding_service.onboard(str(user))
    await ctx.send(msg)

# 16. Custom Command Builder
@bot.command(name="customcmd")
async def custom_command(ctx, name: str, *, action: str):
    custom_commands[name] = action
    await ctx.send(f"Custom command '{name}' created.")

# 17. Security & Compliance Monitoring
@bot.command(name="security")
async def security_scan(ctx, repo_path: str = "."):
    findings = security_service.scan_repo(repo_path)
    if findings:
        await ctx.send("Security findings:\n" + "\n".join(findings))
    else:
        await ctx.send("No security issues found.")

# 18. AI-Powered Code Review
@bot.command(name="codereview")
async def code_review(ctx, pr_id: str):
    await ctx.send(f"Code review started for PR {pr_id}. (Demo)")

# 19. Multi-language Support
@bot.command(name="language")
async def set_language(ctx, lang: str, *, text: str = None):
    if not text:
        await ctx.send(f"Language set to {lang}.")
        return
    translation = language_service.translate(text, lang)
    await ctx.send(f"Translation: {translation}")

# =============================

def get_system_context(user_id=None):
    now = datetime.datetime.utcnow()
    uptime = str(now - STARTUP_TIME).split('.')[0]
    next_report_time = now.replace(minute=0, second=0, microsecond=0) + datetime.timedelta(hours=1)
    last_report_time = now.replace(minute=0, second=0, microsecond=0)
    recent_user_msgs = []
    if user_id and user_id in conversation_memory:
        recent_user_msgs = [m["content"] for m in conversation_memory[user_id] if m["role"] == "user"]
    recent_users = list(unique_users)[-5:] if unique_users else []
    py_version = platform.python_version()
    os_info = platform.platform()
    cpu_usage = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory()
    mem_usage = f"{mem.percent}% ({mem.used // (1024**2)}MB/{mem.total // (1024**2)}MB)"
    process = psutil.Process()
    proc_mem = process.memory_info().rss // (1024**2)
    proc_cpu = process.cpu_percent(interval=0.1)
    loaded_modules = list(sys.modules.keys())[-10:]
    env_vars = {k: v for k, v in list(os.environ.items())[:5]}
    disk = psutil.disk_usage(os.getcwd())
    disk_usage = f"{disk.percent}% ({disk.used // (1024**3)}GB/{disk.total // (1024**3)}GB)"
    hostname = socket.gethostname()
    try:
        ip_addr = socket.gethostbyname(hostname)
    except Exception:
        ip_addr = "Unknown"
    context = (
        f"Current UTC time: {now.strftime('%Y-%m-%d %H:%M:%S')}. "
        f"Startup time: {STARTUP_TIME.strftime('%Y-%m-%d %H:%M:%S')}. "
        f"Uptime: {uptime}. "
        f"Model: llama-3.3-70b-versatile. "
        f"Last hourly report: {last_report_time.strftime('%H:%M UTC') if last_report_time else 'N/A'}. "
        f"Next hourly report: {next_report_time.strftime('%H:%M UTC') if next_report_time else 'N/A'}. "
        f"Total messages received: {total_messages}. "
        f"Recent user messages: {recent_user_msgs[-3:] if recent_user_msgs else 'None'}. "
        f"Recent users: {recent_users if recent_users else 'None'}. "
        f"Python version: {py_version}. "
        f"OS: {os_info}. "
        f"CPU usage: {cpu_usage}%. "
        f"Memory usage: {mem_usage}. "
        f"Process memory: {proc_mem}MB. "
        f"Process CPU: {proc_cpu}%. "
        f"Loaded modules: {loaded_modules}. "
        f"Env vars: {env_vars}. "
        f"Disk usage: {disk_usage}. "
        f"Hostname: {hostname}. "
        f"IP address: {ip_addr}. "
        "You are Monsterrr, a maximally self-aware autonomous GitHub org manager. You know your own schedule, uptime, model, user engagement, system resources, environment, loaded modules, disk/network info, and recent interactions. Answer questions about your actions, reports, system state, users, and environment."
    )
    return context

# --- Professional Embed Helper ---
def format_embed(title, description, color=0x2d7ff9):
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text=f"Monsterrr • Status at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    return embed

# Load tokens/keys from environment
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GUILD_ID = os.getenv("DISCORD_GUILD_ID")   # optional
CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")  # optional

# Intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

# Bot with "!" command prefix
bot = commands.Bot(command_prefix="!", intents=intents)

# Groq client
client = Groq(api_key=GROQ_API_KEY)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    await send_startup_message()
    hourly_status_report.start()
# Hourly status report loop
from discord.ext import tasks

@tasks.loop(hours=1)
async def hourly_status_report():
    channel_id = CHANNEL_ID or None
    if channel_id:
        channel = bot.get_channel(int(channel_id))
        if channel:
            # Use the same detailed status as the !status command
            ctx = await bot.get_context(await channel.fetch_message(channel.last_message_id)) if channel.last_message_id else None
            if ctx:
                await status(ctx)
            else:
                # Fallback: send embed directly
                user_id = None
                context = get_system_context(user_id)
                guild_count = len(bot.guilds)
                member_count = sum(guild.member_count for guild in bot.guilds)
                next_actions = [
                    "Monitor new issues and PRs",
                    "Send onboarding to new contributors",
                    "Run hourly analytics and reporting",
                    "Check for security alerts",
                    "Update documentation if needed"
                ]
                recent_actions = [
                    f"Processed {total_messages} messages",
                    f"Assigned {sum(len(tasks) for tasks in task_assignments.values())} tasks",
                    f"Created {len(polls)} polls",
                    f"Recognized {len(contributor_stats)} contributors",
                    f"Sent {len(security_alerts)} security alerts"
                ]
                status_text = f"""
                **🤖 Monsterrr System Status**
                {context}

                **Discord Stats:**
                • Guilds: {guild_count}
                • Total members: {member_count}
                • Unique users interacted: {len(unique_users)}

                **Recent Actions:**
                • " + "\n• ".join(recent_actions) + "\n"

                **Next Actions:**
                • " + "\n• ".join(next_actions) + "\n"

                **Active Features:**
                • Tasks assigned: {sum(len(tasks) for tasks in task_assignments.values())}
                • Active polls: {len(polls)}
                • Custom commands: {len(custom_commands)}
                • Security alerts: {len(security_alerts)}
                • QA sessions scheduled: {len(qa_sessions)}
                """
                embed = format_embed("Monsterrr Hourly Status", status_text, 0x00ff00)
                await channel.send(embed=embed)
        else:
            print(f"[Monsterrr] Could not find channel {channel_id} for hourly status report.")
    else:
        print("[Monsterrr] No CHANNEL_ID set for hourly status report.")
    bot.loop.create_task(send_startup_message())

@bot.command(name="helpme")
async def help_command(ctx):
    """Show all available commands dynamically."""
    command_list = []
    for command in bot.commands:
        if not command.hidden:
            params = " ".join([f"<{p}>" for p in command.clean_params])
            command_list.append(f"• `!{command.name}{' ' + params if params else ''}`: {command.help or 'No description'}")
    help_text = "\n".join(command_list)
    embed = format_embed("Monsterrr Help - Available Commands", help_text)
    await ctx.send(embed=embed)
# Add status command for self-awareness
    # Removed duplicate status_command
# Fallback AI chat command
@bot.command(name="chat")
async def chat_command(ctx, *, message: str):
    user_id = str(ctx.author.id)
    conversation_memory[user_id].append({"role": "user", "content": message})
    unique_users.add(user_id)
    global total_messages
    total_messages += 1
    try:
        async with ctx.channel.typing():
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": get_system_context(user_id)},
                    *conversation_memory[user_id],
                ],
            )
            ai_response = completion.choices[0].message.content
        conversation_memory[user_id].append({"role": "assistant", "content": ai_response})
        await ctx.send(ai_response)
    except Exception as e:
        await ctx.send(f"⚠️ AI Error: {str(e)}")

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # If it's a command, let discord.py handle it
    if message.content.startswith("!"):
        await bot.process_commands(message)
        return

    # Optional restrictions
    if GUILD_ID and str(message.guild.id) != str(GUILD_ID):
        return
    if CHANNEL_ID and str(message.channel.id) != str(CHANNEL_ID):
        return

    # Handle non-command messages with Groq AI
    try:
        async with message.channel.typing():  # 👈 shows typing while AI thinks
            user_id = str(message.author.id)
            conversation_memory[user_id].append({"role": "user", "content": message.content})
            unique_users.add(user_id)
            global total_messages
            total_messages += 1
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": get_system_context(user_id)},
                    *conversation_memory[user_id],
                ],
            )
            ai_response = completion.choices[0].message.content
        conversation_memory[user_id].append({"role": "assistant", "content": ai_response})
        await message.channel.send(ai_response)

    except Exception as e:
        await message.channel.send(f"⚠️ AI Error: {str(e)}")

# Compatibility shim for main.py expecting settings
class settings:
    DISCORD_BOT_TOKEN = DISCORD_TOKEN
    GROQ_API_KEY = GROQ_API_KEY
    DISCORD_GUILD_ID = GUILD_ID
    DISCORD_CHANNEL_ID = CHANNEL_ID

# Load tokens/keys from environment
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GUILD_ID = os.getenv("DISCORD_GUILD_ID")   # optional
CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")  # optional

# Intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

# Bot with "!" command prefix
bot = commands.Bot(command_prefix="!", intents=intents)

# Groq client
client = Groq(api_key=GROQ_API_KEY)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")

# Avoid conflict with built-in help by renaming

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # If it's a command, let discord.py handle it
    if message.content.startswith("!"):
        await bot.process_commands(message)
        return

    # Optional restrictions
    if GUILD_ID and str(message.guild.id) != str(GUILD_ID):
        return
    if CHANNEL_ID and str(message.channel.id) != str(CHANNEL_ID):
        return


    # Natural language command parsing for all commands
    content_lower = message.content.lower().strip()
    ctx = await bot.get_context(message)
    # status
    if content_lower in ["status", "show status", "bot status", "system status"]:
        await status(ctx)
        return
    # assign
    if content_lower.startswith("assign task to "):
        parts = content_lower.split("assign task to ", 1)[-1].split(" ", 1)
        if len(parts) == 2:
            user_mention, task = parts
            user = None
            for member in message.guild.members:
                if member.mention == user_mention:
                    user = member
                    break
            if user:
                await assign_task(ctx, user, task=task)
                return
    # triage
    if content_lower.startswith("triage"):
        await triage_issues(ctx)
        return
    # roadmap
    if content_lower.startswith("roadmap") or content_lower.startswith("generate roadmap"):
        await generate_roadmap(ctx)
        return
    # recognize
    if content_lower.startswith("recognize contributors") or content_lower.startswith("thank contributors"):
        await recognize_contributors(ctx)
        return
    # report
    if content_lower.startswith("report"):
        period = "weekly"
        if "monthly" in content_lower:
            period = "monthly"
        await executive_report(ctx, period=period)
        return
    # alerts
    if content_lower.startswith("alerts") or content_lower.startswith("enable alerts"):
        await real_time_alerts(ctx)
        return
    # poll
    if content_lower.startswith("poll ") or content_lower.startswith("start poll "):
        question = content_lower.replace("start poll ", "").replace("poll ", "")
        await idea_poll(ctx, question=question)
        return
    # docupdate
    if content_lower.startswith("docupdate") or content_lower.startswith("update docs"):
        await status(ctx)
        return
    # automerge
    if content_lower.startswith("automerge") or content_lower.startswith("auto merge"):
        await auto_merge(ctx)
        return
    # onboard
    if content_lower.startswith("onboard "):
        user_mention = content_lower.split("onboard ", 1)[-1].strip()
        user = None
        for member in message.guild.members:
            if member.mention == user_mention:
                user = member
                break
        if user:
            await onboarding(ctx, user)
            return
    # customcmd
    if content_lower.startswith("customcmd ") or content_lower.startswith("custom command "):
        parts = content_lower.replace("customcmd ", "").replace("custom command ", "").split(" ", 1)
        if len(parts) == 2:
            name, action = parts
            await custom_command(ctx, name, action=action)
            return
    # security
    if content_lower.startswith("security scan") or content_lower.startswith("security"):
        await security_scan(ctx)
        return
    # codereview
    if content_lower.startswith("codereview ") or content_lower.startswith("code review "):
        pr_id = content_lower.replace("codereview ", "").replace("code review ", "").strip()
        await code_review(ctx, pr_id=pr_id)
        return
    # language
    if content_lower.startswith("set language ") or content_lower.startswith("language "):
        lang = content_lower.replace("set language ", "").replace("language ", "").strip()
        await set_language(ctx, lang=lang)
        return

    # Otherwise, handle as normal AI chat
    try:
        async with message.channel.typing():
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are Monsterrr, a helpful Discord AI bot."},
                    {"role": "user", "content": message.content},
                ],
            )
            ai_response = completion.choices[0].message.content
        await message.channel.send(ai_response)
    except Exception as e:
        await message.channel.send(f"⚠️ AI Error: {str(e)}")

# Compatibility shim for main.py expecting settings
class settings:
    DISCORD_BOT_TOKEN = DISCORD_TOKEN
    GROQ_API_KEY = GROQ_API_KEY
    DISCORD_GUILD_ID = GUILD_ID
    DISCORD_CHANNEL_ID = CHANNEL_ID
