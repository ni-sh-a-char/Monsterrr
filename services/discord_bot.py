import discord

# --- Additional Service Commands: Full Coverage (after all other @bot.command) ---
# (Moved to end of file for correct bot registration)


# --- Additional Service Commands (after all other @bot.command functions) ---

# Place this block after the last @bot.command (search_cmd)
# ---------------------------
# Helper: extract_argument
# ---------------------------
def extract_argument(text, key):
    # Simple extraction: look for '<key>: <value>' or '<key> <value>'
    import re
    pattern = re.compile(rf"{key}[:=]?\s*([^,;\n]+)", re.IGNORECASE)
    match = pattern.search(text)
    if match:
        return match.group(1).strip()
    # fallback: just return the first word after the key
    tokens = text.split()
    if key in tokens:
        idx = tokens.index(key)
        if idx + 1 < len(tokens):
            return tokens[idx + 1]
    return None

# ---------------------------
# Helper: extract_user_and_task
# ---------------------------
def extract_user_and_task(text):
    # Look for '@user' or 'user: <user> task: <task>'
    import re
    user = None
    task = None
    user_match = re.search(r"@([\w\d_]+)", text)
    if user_match:
        user = user_match.group(1)
    else:
        user = extract_argument(text, "user")
    task = extract_argument(text, "task")
    # fallback: try to split on ' to '
    if not task and ' to ' in text:
        parts = text.split(' to ', 1)
        if len(parts) == 2:
            task = parts[0].strip()
            user = parts[1].strip()
    return user, task

# ---------------------------
# Helper: extract_message_and_delay
# ---------------------------
def extract_message_and_delay(text):
    # Look for 'in <seconds>' or 'after <seconds>'
    import re
    msg = text
    delay = None
    match = re.search(r"in (\d+) ?s(ec(onds)?)?|after (\d+) ?s(ec(onds)?)?", text)
    if match:
        delay = int(match.group(1) or match.group(4))
        msg = text[:match.start()].strip()
    return msg, delay

# ---------------------------
# Helper: schedule_discord_message
# ---------------------------
async def schedule_discord_message(msg, delay):
    await asyncio.sleep(delay)
    # This function should be called with a channel context in real use
    # For now, just log
    logger.info(f"[Scheduled Message] {msg}")
# ---------------------------
# Helper: create_professional_embed
# ---------------------------
def create_professional_embed(title: str, description: str, color: int = 0x2d7ff9) -> discord.Embed:
    # Truncate description to 4096 chars (Discord embed limit)
    description = description[:4096]
    embed = discord.Embed(title=title, description=description, color=color)
    now_ist = datetime.now(IST)
    embed.set_footer(text=f"Monsterrr • {now_ist.strftime('%Y-%m-%d %H:%M IST')}")
    return embed

# ---------------------------
# Helper: send_long_message
# ---------------------------
async def send_long_message(channel, text, prefix=None):
    # Discord message limit is 2000 chars
    max_len = 2000
    if prefix:
        text = prefix + text
    for i in range(0, len(text), max_len):
        await channel.send(text[i:i+max_len])
# services/discord_bot.py
"""
Monsterrr Discord bot — single file, single on_message flow, fixes:
- Avoids duplicate/triple replies (single code path for commands vs chat)
- Robust Groq wrapper for different service APIs
- All commands defined once (no duplicated decorators)
- Compatibility shim `settings` for discord_bot_runner
- Use datetime.utcnow() (avoids datetime.datetime.datetime mistakes)
Replace your existing services/discord_bot.py with this file.
"""

import os
import asyncio
import logging
import socket
import platform
from collections import defaultdict, deque
from typing import Optional, Dict

import psutil
from discord.ext import commands
from datetime import datetime, timedelta

# Import your project services (adjust if any import path differs)
from .roadmap_service import RoadmapService
from .onboarding_service import OnboardingService
from .merge_service import MergeService
from .language_service import LanguageService
from .doc_service import DocService
from .conversation_memory import ConversationMemory
from .integration_service import IntegrationService
# SearchService for web search
from .search_service import SearchService
from .github_service import GitHubService
# Try to import GroqService; fallback gracefully if different symbol present
try:
    from .groq_service import GroqService
except Exception:
    # If groq_service exposes a different name, try generic import
    try:
        from .groq_service import Groq as GroqService  # fallback alias
    except Exception:
        GroqService = None  # will handle later

from .task_manager import TaskManager
from .triage_service import TriageService
from .poll_service import PollService
from .report_service import ReportService
from .recognition_service import RecognitionService
from .qa_service import QAService
from .security_service import SecurityService

# ---------------------------
# Basic configuration / globals
# ---------------------------
MEMORY_LIMIT = 10
conversation_memory: Dict[str, deque] = defaultdict(lambda: deque(maxlen=MEMORY_LIMIT))
from datetime import datetime, timedelta, timezone
IST = timezone(timedelta(hours=5, minutes=30))
STARTUP_TIME = datetime.now(IST)
total_messages = 0
unique_users = set()
custom_commands: Dict[str, str] = {}

# Environment
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GUILD_ID = os.getenv("DISCORD_GUILD_ID")    # optional
CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")  # optional
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

# ---------------------------
# Logger
# ---------------------------
logger = logging.getLogger("monsterrr")
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(h)
logger.setLevel(logging.INFO)
logger.propagate = False

# ---------------------------
# Instantiate service objects
# ---------------------------


# Instantiate all service objects before bot and SearchService
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

# Additional services for restored commands
try:
    from .analytics_service import AnalyticsService
    analytics_service = AnalyticsService()
except Exception:
    analytics_service = None
try:
    from .alert_service import AlertService
    alert_service = AlertService()
except Exception:
    alert_service = None
try:
    from .notification_service import NotificationService
    notification_service = NotificationService()
except Exception:
    notification_service = None
try:
    from .command_builder import CommandBuilder
    command_builder = CommandBuilder()
except Exception:
    command_builder = None

# Discord bot setup
groq_service = None
if GroqService:
    try:
        groq_service = GroqService(api_key=GROQ_API_KEY, logger=logger)
    except TypeError:
        try:
            groq_service = GroqService(api_key=GROQ_API_KEY)
        except Exception:
            try:
                groq_service = GroqService()
            except Exception:
                groq_service = None

if groq_service is None:
    logger.warning("GroqService could not be initialized. AI features will raise errors until this is fixed.")


# Initialize SearchService after groq_service is available
search_service = None
try:
    search_service = SearchService(llm_client=groq_service, logger=logger)
except Exception as e:
    logger.error(f"SearchService could not be initialized: {e}")

# Expose `client` as alias used in older code
client = groq_service


# --- Autonomous Orchestrator Integration ---
import threading
import asyncio
import importlib.util
import time

orchestrator_status = {
    "last_run": None,
    "last_success": None,
    "last_error": None,
    "last_log": "Not started"
}

def run_orchestrator_background():
    import autonomous_orchestrator
    async def orchestrator_wrapper():
        while True:
            try:
                orchestrator_status["last_log"] = f"Started at {datetime.now(IST)}"
                await autonomous_orchestrator.daily_orchestration()
                orchestrator_status["last_run"] = datetime.now(IST).isoformat()
                orchestrator_status["last_success"] = orchestrator_status["last_run"]
                orchestrator_status["last_error"] = None
            except Exception as e:
                orchestrator_status["last_error"] = str(e)
                orchestrator_status["last_log"] = f"Error: {e}"
                time.sleep(60)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(orchestrator_wrapper())
    loop.run_forever()

orchestrator_thread = threading.Thread(target=run_orchestrator_background, daemon=True)
orchestrator_thread.start()

intents = discord.Intents.default()
intents.guilds = True
intents.members = True           # enable if you need member info
intents.message_content = True   # privileged intent must be enabled in dev portal
intents.messages = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)  # remove default help to use custom

# Small in-process dedupe to avoid processing the same message multiple times in the same process
_PROCESSED_MSG_IDS = deque(maxlen=20000)

def _is_processed(msg_id: int) -> bool:
    return msg_id in _PROCESSED_MSG_IDS

def _mark_processed(msg_id: int):
    _PROCESSED_MSG_IDS.append(msg_id)

# ---------------------------
# Helpers
# ---------------------------
def format_embed(title: str, description: str, color: int = 0x2d7ff9) -> discord.Embed:
    embed = discord.Embed(title=title, description=description, color=color)
    now_ist = datetime.now(IST)
    embed.set_footer(text=f"Monsterrr • Status at: {now_ist.strftime('%Y-%m-%d %H:%M IST')}")
    return embed

def get_system_context(user_id: Optional[str] = None) -> str:
    now = datetime.now(IST)
    uptime = str(now - STARTUP_TIME).split(".")[0]
    recent_user_msgs = []
    if user_id and user_id in conversation_memory:
        recent_user_msgs = [m["content"] for m in conversation_memory[user_id] if m.get("role") == "user"]
    recent_users = list(unique_users)[-5:] if unique_users else []
    try:
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        mem_usage = f"{mem.percent}% ({mem.used // (1024**2)}MB/{mem.total // (1024**2)}MB)"
    except Exception:
        cpu = "N/A"
        mem_usage = "N/A"
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
    except Exception:
        hostname = "Unknown"
        ip = "Unknown"
    orchestrator_info = (
        f"Orchestrator last run: {orchestrator_status.get('last_run', 'Never')}\n"
        f"Orchestrator last success: {orchestrator_status.get('last_success', 'Never')}\n"
        f"Orchestrator last error: {orchestrator_status.get('last_error', 'None')}\n"
        f"Orchestrator log: {orchestrator_status.get('last_log', 'Not started')}\n"
    )
    ctx = (
    f"Current IST time: {now.strftime('%Y-%m-%d %H:%M:%S IST')}. "
    f"Startup: {STARTUP_TIME.strftime('%Y-%m-%d %H:%M:%S IST')}. "
        f"Uptime: {uptime}. "
        f"Model: {GROQ_MODEL}. "
        f"Total messages received: {total_messages}. "
        f"Recent user messages: {recent_user_msgs[-3:] if recent_user_msgs else 'None'}. "
        f"Recent users: {recent_users if recent_users else 'None'}. "
        f"CPU: {cpu}. Memory: {mem_usage}. "
        f"Hostname: {hostname}. IP: {ip}. "
        f"\n[Autonomous Orchestrator]\n{orchestrator_info}"
        "You are Monsterrr, a maximally self-aware autonomous GitHub org manager. Answer questions about your state, actions, and metrics."
    )
    return ctx

def _call_groq(prompt: str, model: Optional[str] = None) -> str:
    """
    Best-effort adapter that supports multiple GroqService wrapper implementations.
    Returns a plain text response or raises an exception on fatal error.
    """
    model = model or GROQ_MODEL
    if groq_service is None:
        raise RuntimeError("GroqService not initialized (check services/groq_service.py and GROQ_API_KEY).")
    # 1) preferred: groq_llm(prompt, model=...)
    if hasattr(groq_service, "groq_llm"):
        try:
            return groq_service.groq_llm(prompt, model=model)
        except TypeError:
            return groq_service.groq_llm(prompt)
    # 2) chat completions shape
    if hasattr(groq_service, "chat") and hasattr(groq_service.chat, "completions"):
        resp = groq_service.chat.completions.create(model=model, messages=[{"role":"user","content":prompt}])
        try:
            return resp.choices[0].message.content.strip()
        except Exception:
            return str(resp)
    # 3) generic create/complete function
    for name in ("create", "complete", "create_completion"):
        if hasattr(groq_service, name):
            fn = getattr(groq_service, name)
            resp = fn(prompt, model=model) if callable(fn) else fn
            if hasattr(resp, "choices"):
                try:
                    return resp.choices[0].message.content.strip()
                except Exception:
                    return str(resp)
            return str(resp)
    # unsupported wrapper
    raise RuntimeError("Unrecognized GroqService interface; update services/groq_service.py or adapt _call_groq.")

# ---------------------------
# Startup message (once)
# ---------------------------
async def send_startup_message_once():
    # Use a dedicated file for startup message tracking
    startup_flag_path = "discord_startup_sent.json"
    flag = False
    # Only send startup message if flag is not set
    try:
        if os.path.exists(startup_flag_path):
            with open(startup_flag_path, "r", encoding="utf-8") as f:
                flag = __import__("json").load(f).get("sent", False)
    except Exception:
        flag = False
    if flag:
        logger.info("Startup message already sent, skipping.")
        return
    await asyncio.sleep(2)
    if CHANNEL_ID:
        try:
            ch = bot.get_channel(int(CHANNEL_ID))
            if ch:
                status_text = (
                    f"**🤖 Monsterrr System Status**\n"
                    f"Startup time: {STARTUP_TIME.strftime('%Y-%m-%d %H:%M:%S IST')}\n"
                    f"Model: {GROQ_MODEL}\n\n"
                    f"**Discord Stats:**\n• Guilds: {len(bot.guilds)}\n• Members: {sum(g.member_count for g in bot.guilds)}\n"
                )
                await ch.send(embed=format_embed("Monsterrr is online!", status_text, 0x00ff00))
                # Write flag only after successful send
                try:
                    with open(startup_flag_path, "w", encoding="utf-8") as f:
                        __import__("json").dump({"sent": True}, f, indent=2)
                except Exception:
                    logger.error("Failed to update discord_startup_sent.json")
        except Exception:
            logger.exception("startup message failed")

# ---------------------------
# Events (single on_message flow)
# ---------------------------

async def send_hourly_status_report():
    while True:
        await asyncio.sleep(3600)  # 1 hour
        try:
            if CHANNEL_ID:
                ch = bot.get_channel(int(CHANNEL_ID))
                if ch:
                    import json
                    import psutil
                    import socket
                    from datetime import datetime
                    try:
                        with open("monsterrr_state.json", "r", encoding="utf-8") as f:
                            state = json.load(f)
                    except Exception:
                        state = {}
                    now_ist = datetime.now(IST)
                    uptime = str(now_ist - STARTUP_TIME).split(".")[0]
                    try:
                        cpu = psutil.cpu_percent(interval=0.1)
                        mem = psutil.virtual_memory()
                        mem_usage = f"{mem.percent:.1f}% (≈ {mem.used // (1024**2)} MB of {mem.total // (1024**2)} MB allocated)"
                    except Exception:
                        cpu = "N/A"
                        mem_usage = "N/A"
                    try:
                        hostname = socket.gethostname()
                        ip = socket.gethostbyname(hostname)
                    except Exception:
                        hostname = "Unknown"
                        ip = "Unknown"
                    github_org = os.getenv("GITHUB_ORG", "unknown")
                    pr_count = state.get("pull_requests", {}).get("count", 0)
                    pr_age = state.get("pull_requests", {}).get("avg_age_days", "N/A")
                    issue_count = state.get("issues", {}).get("count", 0)
                    issue_crit = state.get("issues", {}).get("critical", 0)
                    issue_high = state.get("issues", {}).get("high", 0)
                    issue_med = state.get("issues", {}).get("medium", 0)
                    issue_low = state.get("issues", {}).get("low", 0)
                    ci_status = state.get("ci", {}).get("status", "N/A")
                    ci_duration = state.get("ci", {}).get("avg_duration", "N/A")
                    sec_crit = state.get("security", {}).get("critical_alerts", 0)
                    sec_warn = state.get("security", {}).get("warnings", 0)
                    bots = state.get("automation_bots", {})
                    bots_status = []
                    for bot_name, bot_info in bots.items():
                        bots_status.append(f"• {bot_name} – {bot_info}")
                    queue = state.get("queue", [])
                    queue_lines = [f"• {task}" for task in queue] if queue else ["• No active tasks in the queue."]
                    next_actions = state.get("next_actions", [
                        "Deploy any of the ideas you liked from the previous list.",
                        "Provide a deeper dive into any metric (CPU spikes, memory trends, PR throughput).",
                        "Execute a specific automation (run the dependency scanner now, create a new repo, etc.)."
                    ])
                    # New: analytics, tasks, top ideas, recent user activity
                    analytics = state.get("analytics", {})
                    tasks = state.get("tasks", {})
                    ideas = state.get("ideas", {}).get("top_ideas", [])
                    # Recent user activity (last 3 messages)
                    recent_msgs = []
                    try:
                        recent_users = list(unique_users)[-3:] if unique_users else []
                        for uid in recent_users:
                            if uid in conversation_memory:
                                recent_msgs.extend([m["content"] for m in conversation_memory[uid] if m.get("role") == "user"])
                        recent_msgs = recent_msgs[-3:] if recent_msgs else []
                    except Exception:
                        recent_msgs = []
                    status_lines = [
                        f"**Current operational snapshot**",
                        f"- Uptime: {uptime} (started at {STARTUP_TIME.strftime('%Y-%m-%d %H:%M:%S IST')})",
                        f"- CPU load: {cpu} %",
                        f"- Memory usage: {mem_usage}",
                        f"- Hostname / IP: {hostname} / {ip}",
                        f"- Model in use: {GROQ_MODEL}",
                        f"- Managing GitHub organization: {github_org}",
                        f"- Org-wide health indicators:",
                        f"    • Repository count: {len(state.get('repos', []))} active repos under the organization '{github_org}'",
                        f"    • Pending pull-requests: {pr_count} (average age {pr_age} days)",
                        f"    • Open issues: {issue_count} (critical {issue_crit}, high {issue_high}, medium {issue_med}, low {issue_low})",
                        f"    • CI pipeline health: {ci_status}; average duration {ci_duration}",
                        f"    • Security alerts: {sec_crit} critical, {sec_warn} warnings pending triage",
                        f"- Automation bots:",
                    ]
                    if bots_status:
                        status_lines.extend(bots_status)
                    else:
                        status_lines.append("    • No automation bots configured.")
                    status_lines.append("- Current tasks in the queue:")
                    status_lines.extend(queue_lines)
                    # Add analytics
                    if analytics:
                        status_lines.append("- Analytics:")
                        for k, v in analytics.items():
                            status_lines.append(f"    • {k}: {v}")
                    # Add tasks
                    if tasks:
                        status_lines.append("- Tasks:")
                        for user, tlist in tasks.items():
                            status_lines.append(f"    • {user}: {', '.join(tlist)}")
                    # Add top ideas
                    if ideas:
                        status_lines.append("- Top Ideas:")
                        for i in ideas:
                            status_lines.append(f"    • {i.get('name','')}: {i.get('description','')}")
                    # Add recent user activity
                    status_lines.append("- Recent user activity:")
                    if recent_msgs:
                        for msg in recent_msgs:
                            status_lines.append(f"    • {msg}")
                    else:
                        status_lines.append("    • No recent user activity.")
                    status_lines.append("- What I can do next:")
                    for action in next_actions:
                        status_lines.append(f"    • {action}")
                    embed = discord.Embed(
                        title="🤖 Monsterrr Hourly Status",
                        description="\n".join(status_lines),
                        color=discord.Color.blue()
                    )
                    embed.set_footer(text=f"Monsterrr • {now_ist.strftime('%Y-%m-%d %H:%M IST')}")
                    await ch.send(embed=embed)
                    logger.info("Hourly status report sent to Discord.")
                else:
                    logger.error(f"Hourly report: Channel ID {CHANNEL_ID} not found.")
            else:
                logger.error("Hourly report: DISCORD_CHANNEL_ID not set.")
        except Exception as e:
            logger.error(f"Hourly report: Failed to send: {e}")


import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def build_daily_report():
    try:
        with open("monsterrr_state.json", "r", encoding="utf-8") as f:
            state = __import__("json").load(f)
    except Exception:
        state = {}
    now = datetime.now(IST)
    startup = STARTUP_TIME.strftime('%Y-%m-%d %H:%M:%S IST')
    uptime = str(now - STARTUP_TIME).split(".")[0]
    ideas = state.get("ideas", {}).get("top_ideas", [])
    repos = state.get("repos", [])
    analytics = state.get("analytics", {})
    tasks = state.get("tasks", {})
    # Compose professional HTML report
    html = f"""
    <div style='font-family:Segoe UI,Arial,sans-serif;max-width:600px;margin:0 auto;background:#f9f9fb;padding:32px 24px;border-radius:12px;border:1px solid #e3e7ee;'>
        <h1 style='color:#2d7ff9;margin-bottom:0.2em;'>Monsterrr Daily Report</h1>
        <p style='font-size:1.1em;color:#333;margin-top:0;'>
            <b>System Status:</b><br>
            Startup: {startup}<br>
            Uptime: {uptime}<br>
            Model: {GROQ_MODEL}<br>
            Guilds: {len(bot.guilds)}<br>
            Members: {sum(g.member_count for g in bot.guilds)}<br>
            Total messages: {total_messages}<br>
        </p>
        <hr style='border:0;border-top:1px solid #e3e7ee;margin:18px 0;'>
        <h2 style='color:#222;font-size:1.15em;margin-bottom:0.5em;'>Top Ideas</h2>
        <ul style='line-height:1.7;font-size:1.05em;'>"""
    for idea in ideas:
        html += f"<li><b>{idea.get('name','')}</b>: {idea.get('description','')}</li>"
    html += "</ul>"
    html += "<h2 style='color:#222;font-size:1.15em;margin-bottom:0.5em;'>Active Repositories</h2><ul>"
    for repo in repos:
        html += f"<li><b>{repo.get('name','')}</b>: {repo.get('description','')} (<a href='{repo.get('url','')}'>{repo.get('url','')}</a>)</li>"
    html += "</ul>"
    if analytics:
        html += "<h2 style='color:#222;font-size:1.15em;margin-bottom:0.5em;'>Analytics</h2><ul>"
        for k, v in analytics.items():
            html += f"<li><b>{k.replace('_',' ').title()}</b>: {v}</li>"
        html += "</ul>"
    if tasks:
        html += "<h2 style='color:#222;font-size:1.15em;margin-bottom:0.5em;'>Tasks</h2><ul>"
        for user, tlist in tasks.items():
            html += f"<li><b>{user}</b>: {', '.join(tlist)}</li>"
        html += "</ul>"
    html += f"<hr style='border:0;border-top:1px solid #e3e7ee;margin:18px 0;'>"
    html += f"<p style='font-size:0.95em;color:#888;'>Report generated at {now.strftime('%Y-%m-%d %H:%M IST')}</p>"
    html += "</div>"
    subject = f"Monsterrr Daily Report | {now.strftime('%Y-%m-%d')}"
    return subject, html

async def send_daily_email_report():
    while True:
        await asyncio.sleep(86400)  # 24 hours
        try:
            subject, html = build_daily_report()
            recipients = os.getenv("STATUS_REPORT_RECIPIENTS", "").split(",")
            smtp_host = os.getenv("SMTP_HOST")
            smtp_port = int(os.getenv("SMTP_PORT", "587"))
            smtp_user = os.getenv("SMTP_USER")
            smtp_pass = os.getenv("SMTP_PASS")
            if not recipients or not smtp_host or not smtp_user or not smtp_pass:
                logger.error("Daily email report: Missing SMTP or recipient config.")
                continue
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = smtp_user
            msg["To"] = ", ".join(recipients)
            msg.attach(MIMEText(html, "html"))
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_user, recipients, msg.as_string())
            logger.info(f"Daily email report sent to: {recipients}")
        except Exception as e:
            logger.error(f"Daily report: Failed to send: {e}")

@bot.event
async def on_ready():
    logger.info("Logged in as %s (id=%s)", bot.user, bot.user.id)
    bot.loop.create_task(send_startup_message_once())
    bot.loop.create_task(send_hourly_status_report())
    bot.loop.create_task(send_daily_email_report())

# --- Ensure all services are available via Discord commands and natural language ---
# --- Ensure all GitHub-related commands are routed to the GitHub agent ---
# --- Ensure ChatGPT-like web search is present and works for both !search and natural language ---

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    try:
        global _processed_message_ids
        if '_processed_message_ids' not in globals():
            _processed_message_ids = set()
        if message.id in _processed_message_ids:
            logger.info(f"Duplicate message detected: {message.id}")
            return
        _processed_message_ids.add(message.id)
        if len(_processed_message_ids) > 10000:
            _processed_message_ids = set(list(_processed_message_ids)[-5000:])
    except Exception as e:
        logger.error(f"Deduplication error: {e}")

    # Let discord.py handle explicit commands
    if message.content and message.content.lstrip().startswith(bot.command_prefix):
        await bot.process_commands(message)
        return

    content = (message.content or "").strip()
    if not content:
        return

    user_id = str(message.author.id)
    conversation_memory[user_id].append({"role": "user", "content": content})
    unique_users.add(user_id)
    global total_messages
    total_messages += 1

    # --- Command and intent detection ---
    system_ctx = get_system_context(user_id)
    classify_prompt = (
        f"SYSTEM: You are an AI assistant for a GitHub org. "
        f"NEVER use tables, pipes (|), or any table-like formatting in your answers. "
        f"For all lists or structured data, ALWAYS use bullet points, sub-points, and numbering for clarity. "
        f"Classify the following user message as either a 'command' (if it requests an action, e.g. create repo, assign task, merge PR, etc.) "
        f"or a 'query' (if it is a general question or conversation). "
        f"If it is a command, also extract the intent (e.g. create_repository, assign_task, show_ideas, etc.). "
        f"Return a JSON object: {{'type': 'command'|'query', 'intent': <intent or null>}}.\n\nUser message: {content}"
    )
    try:
        classification = await asyncio.to_thread(_call_groq, classify_prompt, GROQ_MODEL)
        import json as _json
        parsed = _json.loads(classification)
        intent_type = parsed.get('type')
        intent = parsed.get('intent')
    except Exception:
        # Fallback to keyword matching if LLM fails
        command_intents = [
            ("status", "show_status"),
            ("system status", "show_status"),
            ("current status", "show_status"),
            ("guide", "guide_cmd"),
            ("help", "guide_cmd"),
            ("ideas", "show_ideas"),
            ("repos", "show_repos"),
            ("roadmap", "roadmap"),
            ("tasks", "show_tasks"),
            ("analytics", "show_analytics"),
            ("scan", "scan_repo"),
            ("review", "review_pr"),
            ("docs", "show_docs"),
            ("integrate", "integrate_platform"),
            ("qa", "run_qa"),
            ("close", "close_issue"),
            ("assign", "assign_task"),
            ("search", "search_cmd"),
            ("alerts", "alerts_cmd"),
            ("notify", "notify_cmd"),
            ("codereview", "codereview_cmd"),
            ("buildcmd", "buildcmd_cmd"),
            ("onboard", "onboard_cmd"),
            ("merge", "merge_cmd"),
            ("language", "language_cmd"),
            ("triage", "triage_cmd"),
            ("poll", "poll_cmd"),
            ("report", "report_cmd"),
            ("recognize", "recognize_cmd"),
            ("create", "create_repo"),
            ("delete", "delete_repo"),
            ("add", "add_repo"),
            ("show", "show_repos"),
            ("list", "show_repos"),
            ("assign task", "assign_task"),
            ("add task", "add_task"),
            ("delete task", "delete_task"),
            ("show tasks", "show_tasks"),
            ("show ideas", "show_ideas"),
            ("add idea", "add_idea"),
            ("delete idea", "delete_idea"),
            ("merge pull request", "merge_pull_request"),
            ("merge", "merge_cmd"),
            ("close issue", "close_issue"),
            ("analytics dashboard", "show_analytics"),
            ("add analytics", "add_analytics"),
            ("delete analytics", "delete_analytics"),
            ("integrate platform", "integrate_platform"),
            ("run qa", "run_qa"),
            ("scan repo", "scan_repo"),
            ("review pr", "review_pr"),
            ("show docs", "show_docs"),
            ("update docs", "show_docs"),
            ("roadmap", "roadmap"),
            ("start working on", "assign_task"),
            ("work on", "assign_task"),
            ("complete repo", "assign_task"),
            ("send notification", "notify_cmd"),
            ("send alert", "alerts_cmd"),
            ("code review", "codereview_cmd"),
            ("build command", "buildcmd_cmd"),
            ("onboard user", "onboard_cmd"),
            ("translate", "language_cmd"),
            ("triage issue", "triage_cmd"),
            ("create poll", "poll_cmd"),
            ("generate report", "report_cmd"),
            ("recognize user", "recognize_cmd"),
        ]
        for kw, cmd in list(command_intents):
            if not kw.startswith("!"):
                command_intents.append((f"!{kw}", cmd))
        for kw, cmd in command_intents:
            if kw in content.lower():
                intent = cmd
                intent_type = 'command'
                break
        normalized = content.strip().lower()
        for kw, cmd in command_intents:
            if normalized == kw:
                intent = cmd
                intent_type = "command"
                break

    # --- Unified command and web search handling ---
    import re
    url_pattern = re.compile(r"https?://\S+", re.IGNORECASE)
    found_urls = url_pattern.findall(content)
    try:
        async with message.channel.typing():
            # 1. If message is a command, handle via handler (routes to GitHub agent/service as needed)
            if intent_type == 'command' and intent:
                reply = await handle_natural_command(intent, content, user_id)
                conversation_memory[user_id].append({"role": "assistant", "content": reply})
                try:
                    embed = create_professional_embed("Monsterrr Command Result", reply)
                    await message.channel.send(embed=embed)
                except Exception:
                    await send_long_message(message.channel, reply)
            # 2. If message contains a URL, summarize it using SearchService (web search)
            elif found_urls and search_service:
                url = found_urls[0]
                try:
                    summary = await asyncio.to_thread(search_service.summarize_url, url)
                except Exception as e:
                    summary = f"Sorry, I couldn't summarize the URL: {e}"
                conversation_memory[user_id].append({"role": "assistant", "content": summary})
                try:
                    embed = create_professional_embed("Monsterrr Web Summary", summary)
                    await message.channel.send(embed=embed)
                except Exception:
                    await send_long_message(message.channel, summary)
            # 3. If message is a general query, always use SearchService (ChatGPT-like web search)
            elif search_service:
                try:
                    result = None
                    references = None
                    import inspect
                    if hasattr(search_service, "search_and_summarize"):
                        if inspect.iscoroutinefunction(getattr(search_service, "search_and_summarize", None)):
                            result = await search_service.search_and_summarize(content)
                        else:
                            result = await asyncio.to_thread(search_service.search_and_summarize, content)
                    elif hasattr(search_service, "search"):
                        result = await asyncio.to_thread(search_service.search, content)
                    if isinstance(result, dict):
                        summary = result.get("summary") or result.get("answer") or ""
                        references = result.get("references") or result.get("sources") or result.get("urls")
                    elif isinstance(result, tuple) and len(result) == 2:
                        summary, references = result
                    else:
                        summary = result
                    ref_text = ""
                    if references:
                        if isinstance(references, (list, tuple)):
                            ref_lines = [f"[{i+1}] {url}" for i, url in enumerate(references)]
                            ref_text = "\n\n**References:**\n" + "\n".join(ref_lines)
                        elif isinstance(references, str):
                            ref_text = f"\n\n**References:**\n{references}"
                    full_text = (summary or "") + (ref_text or "")
                    if not full_text.strip():
                        await send_long_message(message.channel, "Sorry, I couldn't generate a response.")
                        return
                    conversation_memory[user_id].append({"role": "assistant", "content": full_text})
                    try:
                        embed = create_professional_embed("Monsterrr Web Search", full_text)
                        await message.channel.send(embed=embed)
                    except Exception:
                        await send_long_message(message.channel, full_text)
                except Exception as e:
                    logger.exception("Web search failed: %s", e)
                    await send_long_message(message.channel, f"⚠️ Web Search Error: {e}")
            else:
                # fallback to LLM if web search is not available
                ai_reply = await asyncio.to_thread(_call_groq, content, GROQ_MODEL)
                if not ai_reply:
                    await send_long_message(message.channel, "Sorry, I couldn't generate a response.")
                    return
                org = os.getenv("GITHUB_ORG", "unknown")
                answer = re.sub(r"(?i)the GitHub organization I manage( is called| is|:)? [^\n.]+", f"the GitHub organization I manage is called {org}", ai_reply)
                conversation_memory[user_id].append({"role": "assistant", "content": answer})
                try:
                    embed = create_professional_embed("Monsterrr", answer)
                    await message.channel.send(embed=embed)
                except Exception:
                    await send_long_message(message.channel, answer)
    except Exception as e:
        logger.exception("AI reply failed: %s", e)
        try:
            await send_long_message(message.channel, f"⚠️ AI Error: {e}")
        except Exception:
            pass

# --- Handler for natural language commands ---
async def handle_natural_command(intent, content, user_id):
    # Fully autonomous Jarvis-like implementation
    # All GitHub-related commands call the actual agent/service for real actions
    import re
    if intent == "create_repository":
        repo_name = extract_argument(content, "repo")
        if not repo_name:
            match = re.search(r"(?:repo(?:sitory)?|project) ([\w\- ]+)", content, re.IGNORECASE)
            if match:
                repo_name = match.group(1).strip()
        if repo_name:
            try:
                from services.github_service import GitHubService
                github = GitHubService(logger=logger)
                result = github.create_repository(repo_name) if hasattr(github, "create_repository") else None
                url = result.get('html_url') if isinstance(result, dict) and 'html_url' in result else None
                return f"GitHub agent created repository '{repo_name}'.{' URL: ' + url if url else ''}"
            except Exception as e:
                return f"Failed to create repository: {e}"
        return "Please specify the repository name."
    elif intent == "delete_repository":
        repo_name = extract_argument(content, "repo")
        if not repo_name:
            match = re.search(r"(?:repo(?:sitory)?|project) ([\w\- ]+)", content, re.IGNORECASE)
            if match:
                repo_name = match.group(1).strip()
        if repo_name:
            try:
                from services.github_service import GitHubService
                github = GitHubService(logger=logger)
                github.delete_repository(repo_name)
                return f"GitHub agent deleted repository '{repo_name}'."
            except Exception as e:
                return f"Failed to delete repository: {e}"
        return "Please specify the repository name."
    elif intent == "assign_task":
        repo_match = re.search(r"(?:on|for|to|of) the ([\w\- ]+?) repo(sitory)?", content, re.IGNORECASE)
        repo_name = repo_match.group(1).strip() if repo_match else None
        if repo_name:
            try:
                from services.github_service import GitHubService
                github = GitHubService(logger=logger)
                issue_title = f"Start working on {repo_name}"
                issue_body = f"Automated: Begin work on repository '{repo_name}' as requested via Discord."
                issue = github.create_issue(repo_name, issue_title, issue_body) if hasattr(github, "create_issue") else None
                url = issue.get('html_url') if isinstance(issue, dict) and 'html_url' in issue else None
                return f"GitHub agent started work on repository '{repo_name}'.{' Issue created: ' + url if issue else ''}"
            except Exception as e:
                return f"Failed to start work on repository '{repo_name}': {e}"
        user, task = extract_user_and_task(content)
        if not user:
            user = f"<@{user_id}>"
        if not task:
            task = content.strip()
        if user and task:
            return f"Task '{task}' assigned to {user}."
        return "Please specify both user and task."
    elif intent == "merge_pull_request":
        repo_name = extract_argument(content, "repo")
        pr_id = extract_argument(content, "pr")
        if not pr_id:
            match = re.search(r"pr(?:\s*#)?(\d+)", content, re.IGNORECASE)
            if match:
                pr_id = match.group(1)
        if not repo_name:
            match = re.search(r"(?:repo(?:sitory)?|project) ([\w\- ]+)", content, re.IGNORECASE)
            if match:
                repo_name = match.group(1).strip()
        if repo_name and pr_id:
            try:
                from services.github_service import GitHubService
                github = GitHubService(logger=logger)
                result = github.merge_pull_request(repo_name, int(pr_id)) if hasattr(github, "merge_pull_request") else None
                return f"GitHub agent merged pull request #{pr_id} in '{repo_name}'.{' Result: ' + str(result) if result else ''}"
            except Exception as e:
                return f"Failed to merge pull request: {e}"
        return "Please specify the repository and pull request ID."
    elif intent == "close_issue":
        repo_name = extract_argument(content, "repo")
        issue_id = extract_argument(content, "issue")
        if not issue_id:
            match = re.search(r"issue(?:\s*#)?(\d+)", content, re.IGNORECASE)
            if match:
                issue_id = match.group(1)
        if not repo_name:
            match = re.search(r"(?:repo(?:sitory)?|project) ([\w\- ]+)", content, re.IGNORECASE)
            if match:
                repo_name = match.group(1).strip()
        if repo_name and issue_id:
            try:
                from services.github_service import GitHubService
                github = GitHubService(logger=logger)
                result = github.close_issue(repo_name, int(issue_id)) if hasattr(github, "close_issue") else None
                return f"GitHub agent closed issue #{issue_id} in '{repo_name}'.{' Result: ' + str(result) if result else ''}"
            except Exception as e:
                return f"Failed to close issue: {e}"
        return "Please specify the repository and issue ID."
    elif intent == "review_pr":
        repo_name = extract_argument(content, "repo")
        pr_id = extract_argument(content, "pr")
        if not pr_id:
            match = re.search(r"pr(?:\s*#)?(\d+)", content, re.IGNORECASE)
            if match:
                pr_id = match.group(1)
        if not repo_name:
            match = re.search(r"(?:repo(?:sitory)?|project) ([\w\- ]+)", content, re.IGNORECASE)
            if match:
                repo_name = match.group(1).strip()
        if repo_name and pr_id:
            try:
                from services.code_review_service import CodeReviewService
                code_review_service = CodeReviewService()
                result = code_review_service.review_pr(f"{repo_name}/pull/{pr_id}") if hasattr(code_review_service, "review_pr") else None
                return f"GitHub agent reviewed pull request #{pr_id} in '{repo_name}'.{' Result: ' + str(result) if result else ''}"
            except Exception as e:
                return f"Failed to review pull request: {e}"
        return "Please specify the repository and pull request ID."
    elif intent == "scan_repo":
        repo_name = extract_argument(content, "repo")
        if not repo_name:
            match = re.search(r"(?:repo(?:sitory)?|project) ([\w\- ]+)", content, re.IGNORECASE)
            if match:
                repo_name = match.group(1).strip()
        if repo_name:
            try:
                from services.github_service import GitHubService
                github = GitHubService(logger=logger)
                if hasattr(github, "scan_repository"):
                    result = github.scan_repository(repo_name)
                    return f"GitHub agent scanned repository '{repo_name}'. Result: {result}"
                else:
                    return f"Scan not implemented for repository '{repo_name}'."
            except Exception as e:
                return f"Failed to scan repository: {e}"
    return "Command not recognized or not implemented."

# --- Restored Discord Commands: All features, GitHub actions routed to agent ---
from discord.ext import commands

@bot.command(name="repos")
async def repos_cmd(ctx: commands.Context):
    """List all managed repositories (GitHub agent)."""
    from services.github_service import GitHubService
    github = GitHubService(logger=logger)
    repos = github.list_repositories() if hasattr(github, "list_repositories") else []
    if repos:
        repo_list = "\n".join(f"- {r['name']}" if isinstance(r, dict) and 'name' in r else f"- {r}" for r in repos)
        embed = create_professional_embed("Repositories", repo_list)
        await ctx.send(embed=embed)
    else:
        await ctx.send("No repositories found.")

@bot.command(name="roadmap")
async def roadmap_cmd(ctx: commands.Context, *, project: str = None):
    """Generate a roadmap for a project."""
    if not project:
        await ctx.send("Please specify a project name.")
        return
    roadmap = roadmap_service.generate_roadmap(project) if hasattr(roadmap_service, "generate_roadmap") else None
    if roadmap:
        embed = create_professional_embed(f"Roadmap for {project}", roadmap)
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"No roadmap found for {project}.")

@bot.command(name="assign")
async def assign_cmd(ctx: commands.Context, user: str, *, task: str):
    """Assign a task to a contributor (GitHub agent)."""
    from services.github_service import GitHubService
    github = GitHubService(logger=logger)
    result = github.assign_task(user, task) if hasattr(github, "assign_task") else None
    await ctx.send(f"Task '{task}' assigned to {user}.{' Result: ' + str(result) if result else ''}")

@bot.command(name="tasks")
async def tasks_cmd(ctx: commands.Context, user: str = None):
    """View tasks for a user or all users."""
    tasks = task_manager.get_tasks(user) if hasattr(task_manager, "get_tasks") else None
    if tasks:
        task_list = "\n".join(f"- {t}" for t in tasks)
        embed = create_professional_embed(f"Tasks for {user or 'all users'}", task_list)
        await ctx.send(embed=embed)
    else:
        await ctx.send("No tasks found.")

@bot.command(name="triage")
async def triage_cmd(ctx: commands.Context, *, item: str):
    """AI-powered triage for issues/PRs (GitHub agent)."""
    result = triage_service.triage(item) if hasattr(triage_service, "triage") else None
    await ctx.send(f"Triage result: {result}")

@bot.command(name="onboard")
async def onboard_cmd(ctx: commands.Context, user: str):
    """Onboard a new contributor."""
    result = onboarding_service.onboard(user) if hasattr(onboarding_service, "onboard") else None
    await ctx.send(f"Onboarding result: {result}")

@bot.command(name="merge")
async def merge_cmd(ctx: commands.Context, pr: str):
    """Auto-merge a PR (GitHub agent)."""
    from services.github_service import GitHubService
    github = GitHubService(logger=logger)
    result = github.merge_pull_request(pr) if hasattr(github, "merge_pull_request") else None
    await ctx.send(f"Merge result: {result}")

@bot.command(name="close")
async def close_cmd(ctx: commands.Context, issue: str):
    """Auto-close an issue (GitHub agent)."""
    from services.github_service import GitHubService
    github = GitHubService(logger=logger)
    result = github.close_issue(issue) if hasattr(github, "close_issue") else None
    await ctx.send(f"Close result: {result}")

@bot.command(name="recognize")
async def recognize_cmd(ctx: commands.Context, user: str):
    """Send contributor recognition."""
    result = recognition_service.recognize(user) if hasattr(recognition_service, "recognize") else None
    await ctx.send(f"Recognition result: {result}")

@bot.command(name="report")
async def report_cmd(ctx: commands.Context, period: str = "daily"):
    """Executive reports."""
    result = report_service.generate_report(period) if hasattr(report_service, "generate_report") else None
    await ctx.send(f"Report ({period}): {result}")

@bot.command(name="analytics")
async def analytics_cmd(ctx: commands.Context):
    """View analytics dashboard."""
    result = analytics_service.get_dashboard() if 'analytics_service' in globals() and hasattr(analytics_service, "get_dashboard") else None
    await ctx.send(f"Analytics: {result}")

@bot.command(name="docs")
async def docs_cmd(ctx: commands.Context, repo: str):
    """Update documentation for a repo (GitHub agent)."""
    from services.doc_service import DocService
    doc = DocService()
    result = doc.update_docs(repo) if hasattr(doc, "update_docs") else None
    await ctx.send(f"Docs update: {result}")

@bot.command(name="scan")
async def scan_cmd(ctx: commands.Context, repo: str):
    """Security scan for a repo (GitHub agent)."""
    from services.github_service import GitHubService
    github = GitHubService(logger=logger)
    result = github.scan_repository(repo) if hasattr(github, "scan_repository") else None
    await ctx.send(f"Scan result: {result}")

@bot.command(name="review")
async def review_cmd(ctx: commands.Context, pr: str):
    """AI-powered code review (GitHub agent)."""
    from services.code_review_service import CodeReviewService
    code_review = CodeReviewService()
    result = code_review.review_pr(pr) if hasattr(code_review, "review_pr") else None
    await ctx.send(f"Review result: {result}")

@bot.command(name="alert")
async def alert_cmd(ctx: commands.Context, *, event: str):
    """Send a real-time alert."""
    result = alert_service.send_alert(event) if 'alert_service' in globals() and hasattr(alert_service, "send_alert") else None
    await ctx.send(f"Alert: {result}")

@bot.command(name="poll")
async def poll_cmd(ctx: commands.Context, *, question: str):
    """Create a poll."""
    result = poll_service.create_poll(question) if hasattr(poll_service, "create_poll") else None
    await ctx.send(f"Poll: {result}")

@bot.command(name="notify")
async def notify_cmd(ctx: commands.Context, *, message: str):
    """Send a notification."""
    result = notification_service.notify(message) if 'notification_service' in globals() and hasattr(notification_service, "notify") else None
    await ctx.send(f"Notification: {result}")

@bot.command(name="language")
async def language_cmd(ctx: commands.Context, lang: str, *, text: str):
    """Translate text to another language."""
    result = language_service.translate(lang, text) if hasattr(language_service, "translate") else None
    await ctx.send(f"Translation: {result}")

@bot.command(name="integrate")
async def integrate_cmd(ctx: commands.Context, platform: str):
    """Integrate with other platforms."""
    result = integration_service.integrate(platform) if hasattr(integration_service, "integrate") else None
    await ctx.send(f"Integration: {result}")

@bot.command(name="qa")
async def qa_cmd(ctx: commands.Context, time: str):
    """Schedule a Q&A session."""
    result = qa_service.schedule_qa(time) if hasattr(qa_service, "schedule_qa") else None
    await ctx.send(f"Q&A scheduled: {result}")

@bot.command(name="buildcmd")
async def buildcmd_cmd(ctx: commands.Context, *, spec: str):
    """Build a command from a specification."""
    result = command_builder.build_command(spec) if 'command_builder' in globals() and hasattr(command_builder, "build_command") else None
    await ctx.send(f"Command built: {result}")

@bot.command(name="codereview")
async def codereview_cmd(ctx: commands.Context, *, code: str):
    """AI-powered code review."""
    from services.code_review_service import CodeReviewService
    code_review = CodeReviewService()
    result = code_review.review_code(code) if hasattr(code_review, "review_code") else None
    await ctx.send(f"Code review: {result}")

@bot.command(name="customcmd")
async def customcmd_cmd(ctx: commands.Context, name: str, *, action: str):
    """Create a custom command."""
    custom_commands[name] = action
    await ctx.send(f"Custom command '{name}' created.")

@bot.command(name="guide", aliases=["help"])
async def guide_cmd(ctx: commands.Context):
    embed = discord.Embed(
        title="📘 Monsterrr Discord Interface — Command Guide",
        description="Here’s a full list of available commands and their usage:",
        color=discord.Color.blue()
    )
    commands_list = {
        "🧭 General": [
            "`!guide` — Show all available commands and usage instructions.",
            "`!help` — Show all available commands and usage instructions.",
            "`!status` — Get current Monsterrr system status.",
            "`!ideas` — View top AI-generated ideas.",
            "`!search <query or url>` — Search the web and summarize results.",
            "`!alerts` — Show real-time alerts.",
            "`!notify <message>` — Send a notification.",
            "`!poll <question>` — Create a poll.",
            "`!language <lang> <text>` — Translate text.",
            "`!customcmd <name> <action>` — Create a custom command."
        ],
        "📂 Project Management": [
            "`!repos` — List all managed repositories.",
            "`!roadmap <project>` — Generate a roadmap for a project.",
            "`!assign <user> <task>` — Assign a task to a contributor.",
            "`!tasks [user]` — View tasks for a user or all users.",
            "`!triage <issue|pr> <item>` — AI-powered triage for issues/PRs.",
            "`!onboard <user>` — Onboard a new contributor.",
            "`!merge <pr>` — Auto-merge a PR.",
            "`!close <issue>` — Auto-close an issue."
        ],
        "🏆 Contributor Tools": [
            "`!recognize <user>` — Send contributor recognition.",
            "`!report [daily|weekly|monthly]` — Executive reports.",
            "`!analytics` — View analytics dashboard."
        ],
        "💻 Code & Automation": [
            "`!docs <repo>` — Update documentation for a repo.",
            "`!scan <repo>` — Security scan for a repo.",
            "`!review <pr>` — AI-powered code review.",
            "`!codereview <code>` — AI-powered code review.",
            "`!buildcmd <spec>` — Build a command from a specification."
        ],
        "🌐 Web Search & Natural Language": [
            "You can use `!search <query or url>` or just ask a question or paste a URL in chat. Monsterrr will search the web and summarize results like ChatGPT."
        ]
    }
    for category, cmds in commands_list.items():
        embed.add_field(name=category, value="\n".join(cmds), inline=False)
    embed.set_footer(text="✨ Powered by Monsterrr — All services are now available as commands.")
    await ctx.send(embed=embed)

@bot.command(name="status")
async def status_cmd(ctx: commands.Context):
    """Get current Monsterrr system status (detailed, with latest agent activity)."""
    import psutil, socket
    org = os.getenv("GITHUB_ORG", "unknown")
    now_ist = datetime.now(IST)
    uptime = str(now_ist - STARTUP_TIME).split(".")[0]
    try:
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        mem_usage = f"{mem.percent:.1f}% (≈ {mem.used // (1024**2)} MB of {mem.total // (1024**2)} MB allocated)"
    except Exception:
        cpu = "N/A"
        mem_usage = "N/A"
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
    except Exception:
        hostname = "Unknown"
        ip = "Unknown"
    repo_count = 0
    try:
        from services.github_service import GitHubService
        github = GitHubService(logger=logger)
        repos = github.list_repositories() if hasattr(github, "list_repositories") else []
        repo_count = len(repos)
    except Exception:
        pass
    recent_users = list(unique_users)[-3:] if unique_users else []
    recent_msgs = []
    for uid in recent_users:
        if uid in conversation_memory:
            recent_msgs.extend([m["content"] for m in conversation_memory[uid] if m.get("role") == "user"])
    recent_msgs = recent_msgs[-3:] if recent_msgs else []
    # Latest agent activity (last 3 assistant/agent messages)
    agent_msgs = []
    for uid in recent_users:
        if uid in conversation_memory:
            agent_msgs.extend([m["content"] for m in conversation_memory[uid] if m.get("role") in ("assistant", "agent")])
    agent_msgs = agent_msgs[-3:] if agent_msgs else []
    status_lines = [
        f"**Current operational snapshot**",
        f"- Uptime: {uptime} (started at {STARTUP_TIME.strftime('%Y-%m-%d %H:%M:%S IST')})",
        f"- CPU load: {cpu} %",
        f"- Memory usage: {mem_usage}",
        f"- Hostname / IP: {hostname} / {ip}",
        f"- Model in use: {GROQ_MODEL}",
        f"- Managing GitHub organization: {org}",
        f"- Repository count: {repo_count}",
        f"- Total messages received: {total_messages}",
        f"- Recent user activity:",
    ]
    if recent_msgs:
        for msg in recent_msgs:
            status_lines.append(f"    • {msg}")
    else:
        status_lines.append("    • No recent user activity.")
    status_lines.append(f"- Latest agent activity:")
    if agent_msgs:
        for msg in agent_msgs:
            status_lines.append(f"    • {msg}")
    else:
        status_lines.append("    • No recent agent activity.")
    embed = discord.Embed(
        title="🤖 Monsterrr Status",
        description="\n".join(status_lines),
        color=discord.Color.blue()
    )
    embed.set_footer(text=f"Monsterrr • {now_ist.strftime('%Y-%m-%d %H:%M IST')}")
    await ctx.send(embed=embed)

# Update handle_natural_command to support 'show_status' intent
async def handle_natural_command(intent, content, user_id):
    # ...existing code...
    if intent == "show_status":
        org = os.getenv("GITHUB_ORG", "unknown")
        repo_count = 0
        try:
            from services.github_service import GitHubService
            github = GitHubService(logger=logger)
            repos = github.list_repositories() if hasattr(github, "list_repositories") else []
            repo_count = len(repos)
        except Exception:
            pass
        status_lines = [
            f"Monsterrr is online and managing GitHub organization: {org}",
            f"Active repositories: {repo_count}",
            f"All core services are running."
        ]
        return "\n".join(status_lines)
    # ...existing code...

# --- Ideas Command ---
@bot.command(name="ideas")
async def ideas_cmd(ctx: commands.Context):
    """Show top ideas (from state or service)."""
    try:
        import json
        with open("monsterrr_state.json", "r", encoding="utf-8") as f:
            state = json.load(f)
        ideas = state.get("ideas", {}).get("top_ideas", [])
    except Exception:
        ideas = []
    if ideas:
        idea_list = "\n".join(f"- **{i.get('name','')}**: {i.get('description','')}" for i in ideas)
        embed = create_professional_embed("Top Ideas", idea_list)
        await ctx.send(embed=embed)
    else:
        await ctx.send("No ideas found.")