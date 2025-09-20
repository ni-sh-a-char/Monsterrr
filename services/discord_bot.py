def update_system_status_in_state():
    """Write system status fields to monsterrr_state.json for reporting."""
    try:
        import json
        now = datetime.now(IST)
        startup = STARTUP_TIME.strftime('%Y-%m-%d %H:%M:%S IST')
        uptime = str(now - STARTUP_TIME).split(".")[0]
        model = GROQ_MODEL
        guilds = len(bot.guilds)
        members = sum(g.member_count for g in bot.guilds)
        state_path = "monsterrr_state.json"
        if os.path.exists(state_path):
            with open(state_path, "r", encoding="utf-8") as f:
                state = json.load(f)
        else:
            state = {}
        state["startup"] = startup
        state["uptime"] = uptime
        state["model"] = model
        state["guilds"] = guilds
        state["members"] = members
        state["total_messages"] = total_messages
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to update system status in state: {e}")
"""
Monsterrr Discord bot — refactored single file
- Removed duplicate code and errors
- Single on_message flow for commands vs chat
- Robust Groq wrapper for different service APIs
- All commands defined once
- Preserved all functionality
"""

import os
import asyncio
import logging
import socket
import platform
import threading
import time
import re
import json
import smtplib
from collections import defaultdict, deque
from typing import Optional, Dict
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import psutil
import discord
from discord.ext import commands

# Import project services
from .roadmap_service import RoadmapService
from .onboarding_service import OnboardingService
from .merge_service import MergeService
from .language_service import LanguageService
from .doc_service import DocService
from .conversation_memory import ConversationMemory
from .integration_service import IntegrationService
from .search_service import SearchService
from .github_service import GitHubService
from .task_manager import TaskManager
from .triage_service import TriageService
from .poll_service import PollService
from .report_service import ReportService
from .recognition_service import RecognitionService
from .qa_service import QAService
from .security_service import SecurityService

# Try to import GroqService with fallback
try:
    from .groq_service import GroqService
except Exception:
    try:
        from .groq_service import Groq as GroqService
    except Exception:
        GroqService = None

# Optional services
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

# Configuration
MEMORY_LIMIT = 10
IST = timezone(timedelta(hours=5, minutes=30))
STARTUP_TIME = datetime.now(IST)

# Environment variables
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GUILD_ID = os.getenv("DISCORD_GUILD_ID")
CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

# Global state
total_messages = 0
unique_users = set()
custom_commands: Dict[str, str] = {}
conversation_memory: Dict[str, deque] = defaultdict(lambda: deque(maxlen=MEMORY_LIMIT))

# Logger setup
logger = logging.getLogger("monsterrr")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False

# Initialize services
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

# Initialize GroqService
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

# Initialize SearchService
search_service = None
try:
    search_service = SearchService(llm_client=groq_service, logger=logger)
except Exception as e:
    logger.error(f"SearchService could not be initialized: {e}")

# Alias for backwards compatibility
client = groq_service

# Autonomous Orchestrator Integration
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
    # Only start orchestrator if not already running (avoid multiple starts)
    if os.environ.get("MONSTERRR_ORCHESTRATOR_STARTED") != "1":
        os.environ["MONSTERRR_ORCHESTRATOR_STARTED"] = "1"
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

# Discord bot setup
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True
intents.messages = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# Message deduplication
_PROCESSED_MSG_IDS = deque(maxlen=20000)

def _is_processed(msg_id: int) -> bool:
    return msg_id in _PROCESSED_MSG_IDS

def _mark_processed(msg_id: int):
    _PROCESSED_MSG_IDS.append(msg_id)

# Helper functions
def extract_argument(text, key):
    """Extract argument value from text."""
    pattern = re.compile(rf"{key}[:=]?\s*([^,;\n]+)", re.IGNORECASE)
    match = pattern.search(text)
    if match:
        return match.group(1).strip()
    
    tokens = text.split()
    if key in tokens:
        idx = tokens.index(key)
        if idx + 1 < len(tokens):
            return tokens[idx + 1]
    return None

def extract_user_and_task(text):
    """Extract user and task from text."""
    user = None
    task = None
    
    user_match = re.search(r"@([\w\d_]+)", text)
    if user_match:
        user = user_match.group(1)
    else:
        user = extract_argument(text, "user")
    
    task = extract_argument(text, "task")
    
    if not task and ' to ' in text:
        parts = text.split(' to ', 1)
        if len(parts) == 2:
            task = parts[0].strip()
            user = parts[1].strip()
    
    return user, task

def extract_message_and_delay(text):
    """Extract message and delay from text."""
    msg = text
    delay = None
    match = re.search(r"in (\d+) ?s(ec(onds)?)?|after (\d+) ?s(ec(onds)?)?", text)
    if match:
        delay = int(match.group(1) or match.group(4))
        msg = text[:match.start()].strip()
    return msg, delay

async def schedule_discord_message(msg, delay):
    """Schedule a Discord message."""
    await asyncio.sleep(delay)
    logger.info(f"[Scheduled Message] {msg}")

def create_professional_embed(title: str, description: str, color: int = 0x2d7ff9) -> discord.Embed:
    """Create a professional Discord embed."""
    description = description[:4096]  # Discord limit
    embed = discord.Embed(title=title, description=description, color=color)
    now_ist = datetime.now(IST)
    embed.set_footer(text=f"Monsterrr • {now_ist.strftime('%Y-%m-%d %H:%M IST')}")
    return embed

async def send_long_message(channel, text, prefix=None):
    """Send long message split into chunks."""
    max_len = 2000
    if prefix:
        text = prefix + text
    for i in range(0, len(text), max_len):
        await channel.send(text[i:i+max_len])

def get_system_context(user_id: Optional[str] = None) -> str:
    """Get system context for AI responses."""
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
    """Call Groq API with error handling."""
    model = model or GROQ_MODEL
    if groq_service is None:
        raise RuntimeError("GroqService not initialized (check services/groq_service.py and GROQ_API_KEY).")
    
    # Try different interface patterns
    if hasattr(groq_service, "groq_llm"):
        try:
            return groq_service.groq_llm(prompt, model=model)
        except TypeError:
            return groq_service.groq_llm(prompt)
    
    if hasattr(groq_service, "chat") and hasattr(groq_service.chat, "completions"):
        resp = groq_service.chat.completions.create(model=model, messages=[{"role":"user","content":prompt}])
        try:
            return resp.choices[0].message.content.strip()
        except Exception:
            return str(resp)
    
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
    
    raise RuntimeError("Unrecognized GroqService interface; update services/groq_service.py or adapt _call_groq.")

# Startup message handler
async def send_startup_message_once():
    """Send startup message once."""
    startup_flag_path = "discord_startup_sent.json"
    flag = False
    
    try:
        if os.path.exists(startup_flag_path):
            with open(startup_flag_path, "r", encoding="utf-8") as f:
                flag = json.load(f).get("sent", False)
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
                await ch.send(embed=create_professional_embed("Monsterrr is online!", status_text, 0x00ff00))
                
                try:
                    with open(startup_flag_path, "w", encoding="utf-8") as f:
                        json.dump({"sent": True}, f, indent=2)
                except Exception:
                    logger.error("Failed to update discord_startup_sent.json")
        except Exception:
            logger.exception("startup message failed")

# Report generators
def build_daily_report():
    """Build daily report content."""
    try:
        with open("monsterrr_state.json", "r", encoding="utf-8") as f:
            state = json.load(f)
    except Exception:
        state = {}
    
    now = datetime.now(IST)
    startup = STARTUP_TIME.strftime('%Y-%m-%d %H:%M:%S IST')
    uptime = str(now - STARTUP_TIME).split(".")[0]
    ideas = state.get("ideas", {}).get("top_ideas", [])
    repos = state.get("repos", [])
    analytics = state.get("analytics", {})
    tasks = state.get("tasks", {})
    
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
    
    html += "</ul><h2 style='color:#222;font-size:1.15em;margin-bottom:0.5em;'>Active Repositories</h2><ul>"
    
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

# Background tasks
async def send_hourly_status_report():
    """Send hourly status reports."""
    while True:
        await asyncio.sleep(3600)  # 1 hour
        try:
            if CHANNEL_ID:
                ch = bot.get_channel(int(CHANNEL_ID))
                if ch:
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
                        mem_usage = f"{mem.percent:.1f}% (≈ {mem.used // (1024**2)} MB of {mem.total // (1024**2)} MB allocated)"
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
                    bots_status = [f"• {bot_name} – {bot_info}" for bot_name, bot_info in bots.items()]
                    
                    queue = state.get("queue", [])
                    queue_lines = [f"• {task}" for task in queue] if queue else ["• No active tasks in the queue."]
                    
                    next_actions = state.get("next_actions", [
                        "Deploy any of the ideas you liked from the previous list.",
                        "Provide a deeper dive into any metric (CPU spikes, memory trends, PR throughput).",
                        "Execute a specific automation (run the dependency scanner now, create a new repo, etc.)."
                    ])
                    
                    analytics = state.get("analytics", {})
                    tasks = state.get("tasks", {})
                    ideas = state.get("ideas", {}).get("top_ideas", [])
                    
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
                        f"- Hostname / IP: {hostname}",
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
                    
                    if analytics:
                        status_lines.append("- Analytics:")
                        for k, v in analytics.items():
                            status_lines.append(f"    • {k}: {v}")
                    
                    if tasks:
                        status_lines.append("- Tasks:")
                        for user, tlist in tasks.items():
                            status_lines.append(f"    • {user}: {', '.join(tlist)}")
                    
                    if ideas:
                        status_lines.append("- Top Ideas:")
                        for i in ideas:
                            status_lines.append(f"    • {i.get('name','')}: {i.get('description','')}")
                    
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

async def send_daily_email_report():
    """Send daily email reports."""
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

# Command handler for natural language
async def handle_natural_command(intent, content, user_id):
    """Handle natural language commands."""
    
    # Repository management commands
    if intent in ["show_repos", "list_repos"]:
        try:
            github = GitHubService(logger=logger)
            repos = github.list_repositories() if hasattr(github, "list_repositories") else []
            if repos:
                repo_list = "\n".join(f"- {r['name']}" if isinstance(r, dict) and 'name' in r else f"- {r}" for r in repos)
                return f"**Managed Repositories:**\n{repo_list}"
            else:
                return "No repositories found."
        except Exception as e:
            return f"Failed to list repositories: {e}"
    
    elif intent == "create_repo":
        repo_name = extract_argument(content, "repo")
        if not repo_name:
            match = re.search(r"(?:create|add|new) (?:repo(?:sitory)?|project) (?:called |named )?([a-zA-Z0-9\-_]+)", content, re.IGNORECASE)
            if match:
                repo_name = match.group(1).strip()
        
        if repo_name:
            try:
                github = GitHubService(logger=logger)
                result = github.create_repository(repo_name) if hasattr(github, "create_repository") else None
                url = result.get('html_url') if isinstance(result, dict) and 'html_url' in result else None
                return f"GitHub agent created repository '{repo_name}'.{' URL: ' + url if url else ''}"
            except Exception as e:
                return f"Failed to create repository: {e}"
        return "Please specify the repository name."
    
    elif intent == "delete_repo":
        repo_name = extract_argument(content, "repo")
        if not repo_name:
            match = re.search(r"(?:delete|remove) (?:repo(?:sitory)?|project) (?:called |named )?([a-zA-Z0-9\-_]+)", content, re.IGNORECASE)
            if match:
                repo_name = match.group(1).strip()
        
        if repo_name:
            try:
                github = GitHubService(logger=logger)
                github.delete_repository(repo_name) if hasattr(github, "delete_repository") else None
                return f"GitHub agent deleted repository '{repo_name}'."
            except Exception as e:
                return f"Failed to delete repository: {e}"
        return "Please specify the repository name."
    
    # Task management commands
    elif intent == "assign_task":
        repo_match = re.search(r"(?:on|for|to|of) the ([\w\-]+) repo(?:sitory)?", content, re.IGNORECASE)
        repo_name = repo_match.group(1).strip() if repo_match else None
        
        if repo_name:
            try:
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
    
    # GitHub operations
    elif intent == "merge_pull_request":
        repo_name = extract_argument(content, "repo")
        pr_id = extract_argument(content, "pr")
        if not pr_id:
            match = re.search(r"pr(?:\s*#)?(\d+)", content, re.IGNORECASE)
            if match:
                pr_id = match.group(1)
        if not repo_name:
            match = re.search(r"(?:repo(?:sitory)?|project) ([\w\-]+)", content, re.IGNORECASE)
            if match:
                repo_name = match.group(1).strip()
        
        if repo_name and pr_id:
            try:
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
            match = re.search(r"(?:repo(?:sitory)?|project) ([\w\-]+)", content, re.IGNORECASE)
            if match:
                repo_name = match.group(1).strip()
        
        if repo_name and issue_id:
            try:
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
            match = re.search(r"(?:repo(?:sitory)?|project) ([\w\-]+)", content, re.IGNORECASE)
            if match:
                repo_name = match.group(1).strip()
        
        if repo_name and pr_id:
            try:
                from .code_review_service import CodeReviewService
                code_review_service = CodeReviewService()
                result = code_review_service.review_pr(f"{repo_name}/pull/{pr_id}") if hasattr(code_review_service, "review_pr") else None
                return f"GitHub agent reviewed pull request #{pr_id} in '{repo_name}'.{' Result: ' + str(result) if result else ''}"
            except Exception as e:
                return f"Failed to review pull request: {e}"
        return "Please specify the repository and pull request ID."
    
    elif intent == "scan_repo":
        repo_name = extract_argument(content, "repo")
        if not repo_name:
            match = re.search(r"(?:repo(?:sitory)?|project) ([\w\-]+)", content, re.IGNORECASE)
            if match:
                repo_name = match.group(1).strip()
        
        if repo_name:
            try:
                github = GitHubService(logger=logger)
                if hasattr(github, "scan_repository"):
                    result = github.scan_repository(repo_name)
                    return f"GitHub agent scanned repository '{repo_name}'. Result: {result}"
                else:
                    return f"Scan not implemented for repository '{repo_name}'."
            except Exception as e:
                return f"Failed to scan repository: {e}"
        return "Please specify the repository name."
    
    # Status and information commands
    elif intent == "show_status":
        return get_system_context(user_id)
    
    elif intent == "show_ideas":
        try:
            with open("monsterrr_state.json", "r", encoding="utf-8") as f:
                state = json.load(f)
            ideas = state.get("ideas", {}).get("top_ideas", [])
            if ideas:
                idea_list = "\n".join(f"- **{i.get('name','')}**: {i.get('description','')}" for i in ideas)
                return f"**Top Ideas:**\n{idea_list}"
            else:
                return "No ideas found."
        except Exception:
            return "No ideas available."
    
    elif intent == "show_tasks":
        try:
            with open("monsterrr_state.json", "r", encoding="utf-8") as f:
                state = json.load(f)
            tasks = state.get("tasks", {})
            if tasks:
                task_list = "\n".join(f"- **{user}**: {', '.join(tlist)}" for user, tlist in tasks.items())
                return f"**Current Tasks:**\n{task_list}"
            else:
                return "No tasks found."
        except Exception:
            return "No tasks available."
    
    elif intent == "show_analytics":
        try:
            with open("monsterrr_state.json", "r", encoding="utf-8") as f:
                state = json.load(f)
            analytics = state.get("analytics", {})
            if analytics:
                analytics_list = "\n".join(f"- **{k.replace('_',' ').title()}**: {v}" for k, v in analytics.items())
                return f"**Analytics Dashboard:**\n{analytics_list}"
            else:
                return "No analytics data available."
        except Exception:
            return "Analytics not available."
    
    # Service commands
    elif intent == "roadmap":
        project = extract_argument(content, "project") or "default"
        result = roadmap_service.generate_roadmap(project) if hasattr(roadmap_service, "generate_roadmap") else "Roadmap service not available"
        return f"Roadmap for {project}: {result}"
    
    elif intent == "triage_cmd":
        item = content.replace("triage", "").strip()
        result = triage_service.triage(item) if hasattr(triage_service, "triage") else "Triage service not available"
        return f"Triage result: {result}"
    
    elif intent == "onboard_cmd":
        user = extract_argument(content, "user") or f"<@{user_id}>"
        result = onboarding_service.onboard(user) if hasattr(onboarding_service, "onboard") else "Onboarding service not available"
        return f"Onboarding result for {user}: {result}"
    
    elif intent == "merge_cmd":
        pr = extract_argument(content, "pr")
        result = merge_service.merge_pr(pr) if hasattr(merge_service, "merge_pr") else "Merge service not available"
        return f"Merge result: {result}"
    
    elif intent == "language_cmd":
        lang = extract_argument(content, "lang") or "en"
        text = content.replace(f"translate to {lang}", "").strip()
        result = language_service.translate(lang, text) if hasattr(language_service, "translate") else "Translation service not available"
        return f"Translation to {lang}: {result}"
    
    elif intent == "poll_cmd":
        question = content.replace("poll", "").strip()
        result = poll_service.create_poll(question) if hasattr(poll_service, "create_poll") else "Poll service not available"
        return f"Poll created: {result}"
    
    elif intent == "report_cmd":
        period = extract_argument(content, "period") or "daily"
        result = report_service.generate_report(period) if hasattr(report_service, "generate_report") else "Report service not available"
        return f"Report ({period}): {result}"
    
    elif intent == "recognize_cmd":
        user = extract_argument(content, "user") or f"<@{user_id}>"
        result = recognition_service.recognize(user) if hasattr(recognition_service, "recognize") else "Recognition service not available"
        return f"Recognition for {user}: {result}"
    
    elif intent == "run_qa":
        time_param = extract_argument(content, "time") or "now"
        result = qa_service.schedule_qa(time_param) if hasattr(qa_service, "schedule_qa") else "QA service not available"
        return f"QA scheduled: {result}"
    
    elif intent == "integrate_platform":
        platform = extract_argument(content, "platform") or "unknown"
        result = integration_service.integrate(platform) if hasattr(integration_service, "integrate") else "Integration service not available"
        return f"Integration with {platform}: {result}"
    
    elif intent == "show_docs":
        repo = extract_argument(content, "repo") or "default"
        result = doc_service.update_docs(repo) if hasattr(doc_service, "update_docs") else "Documentation service not available"
        return f"Documentation for {repo}: {result}"
    
    # Additional service commands
    elif intent == "alerts_cmd":
        if alert_service:
            event = content.replace("alert", "").strip()
            result = alert_service.send_alert(event) if hasattr(alert_service, "send_alert") else "Alert sent"
            return f"Alert: {result}"
        return "Alert service not available"
    
    elif intent == "notify_cmd":
        if notification_service:
            message = content.replace("notify", "").strip()
            result = notification_service.notify(message) if hasattr(notification_service, "notify") else "Notification sent"
            return f"Notification: {result}"
        return "Notification service not available"
    
    elif intent == "codereview_cmd":
        code = content.replace("code review", "").strip()
        try:
            from .code_review_service import CodeReviewService
            code_review = CodeReviewService()
            result = code_review.review_code(code) if hasattr(code_review, "review_code") else "Code review not available"
            return f"Code review: {result}"
        except Exception:
            return "Code review service not available"
    
    elif intent == "buildcmd_cmd":
        if command_builder:
            spec = content.replace("build command", "").strip()
            result = command_builder.build_command(spec) if hasattr(command_builder, "build_command") else "Command built"
            return f"Command built: {result}"
        return "Command builder not available"
    
    elif intent == "search_cmd":
        query = content.replace("search", "").strip()
        if search_service:
            try:
                result = search_service.search_and_summarize(query)
                return f"Search results: {result}"
            except Exception as e:
                return f"Search failed: {e}"
        return "Search service not available"
    
    elif intent == "guide_cmd":
        return """**📘 Monsterrr Command Guide**

**🧭 General Commands:**
- `status` — Get current system status
- `ideas` — View top AI-generated ideas
- `search <query>` — Search the web
- `help` or `guide` — Show this guide

**📂 Repository Management:**
- `repos` or `show repos` — List all repositories
- `create repo <name>` — Create new repository
- `delete repo <name>` — Delete repository
- `assign task <user> <task>` — Assign task
- `start working on <repo>` — Begin work on repo

**💻 GitHub Operations:**
- `merge pr #<number> in <repo>` — Merge pull request
- `close issue #<number> in <repo>` — Close issue
- `review pr #<number> in <repo>` — Code review
- `scan repo <name>` — Security scan

**🏆 Project Tools:**
- `roadmap <project>` — Generate roadmap
- `triage <item>` — AI-powered triage
- `onboard <user>` — Onboard contributor
- `analytics` — View dashboard
- `tasks` — View current tasks

You can use natural language or the `!` prefix for commands."""
    
    return "Command not recognized or not implemented."

# Discord Events
@bot.event
async def on_ready():
    logger.info("Logged in as %s (id=%s)", bot.user, bot.user.id)
    bot.loop.create_task(send_startup_message_once())
    bot.loop.create_task(send_hourly_status_report())
    bot.loop.create_task(send_daily_email_report())

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    
    # Deduplication
    if _is_processed(message.id):
        logger.info(f"Duplicate message detected: {message.id}")
        return
    _mark_processed(message.id)
    
    content = (message.content or "").strip()
    if not content:
        return
    
    # Handle explicit commands with ! prefix
    if content.startswith("!"):
        await bot.process_commands(message)
        return
    
    # AI-first message handling
    async with message.channel.typing():
        global total_messages
        user_id = str(message.author.id)
        conversation_memory[user_id].append({"role": "user", "content": content})
        unique_users.add(user_id)
        total_messages += 1
        
        # Command intent detection
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
            parsed = json.loads(classification)
            intent_type = parsed.get('type')
            intent = parsed.get('intent')
        except Exception:
            # Fallback keyword matching
            command_intents = [
                ("status", "show_status"), ("system status", "show_status"), ("current status", "show_status"),
                ("guide", "guide_cmd"), ("help", "guide_cmd"), ("ideas", "show_ideas"), ("repos", "show_repos"),
                ("show repos", "show_repos"), ("list repos", "show_repos"), ("roadmap", "roadmap"),
                ("tasks", "show_tasks"), ("analytics", "show_analytics"), ("scan", "scan_repo"),
                ("review", "review_pr"), ("docs", "show_docs"), ("integrate", "integrate_platform"),
                ("qa", "run_qa"), ("close", "close_issue"), ("assign", "assign_task"), ("search", "search_cmd"),
                ("alerts", "alerts_cmd"), ("notify", "notify_cmd"), ("codereview", "codereview_cmd"),
                ("buildcmd", "buildcmd_cmd"), ("onboard", "onboard_cmd"), ("merge", "merge_cmd"),
                ("language", "language_cmd"), ("triage", "triage_cmd"), ("poll", "poll_cmd"),
                ("report", "report_cmd"), ("recognize", "recognize_cmd"), ("create", "create_repo"),
                ("delete", "delete_repo"), ("add", "add_repo"), ("show", "show_repos"), ("list", "show_repos"),
                ("brainstorm", "brainstorm_cmd"), ("plan", "plan_cmd"), ("execute", "execute_cmd"),
                ("improve", "improve_cmd"), ("maintain", "maintain_cmd")
            ]
            
            intent = None
            intent_type = 'query'
            
            for kw, cmd in command_intents:
                if kw in content.lower():
                    intent = cmd
                    intent_type = 'command'
                    break
        
        # URL detection for web search
        url_pattern = re.compile(r"https?://\S+", re.IGNORECASE)
        found_urls = url_pattern.findall(content)
        
        try:
            # Handle different message types
            if intent_type == 'command' and intent:
                # Handle natural language commands
                reply = await handle_natural_command(intent, content, user_id)
                conversation_memory[user_id].append({"role": "assistant", "content": reply})
                try:
                    embed = create_professional_embed("Monsterrr Command Result", reply)
                    await message.channel.send(embed=embed)
                except Exception:
                    await send_long_message(message.channel, reply)
                return
            
            elif found_urls and search_service:
                # Summarize URLs
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
                return
            
            elif search_service and not intent:
                # General web search for queries
                try:
                    result = await search_service.search_and_summarize(content)
                    summary = result
                    references = None
                    
                    if isinstance(result, dict):
                        summary = result.get("summary") or result.get("answer") or ""
                        references = result.get("references") or result.get("sources") or result.get("urls")
                    elif isinstance(result, tuple) and len(result) == 2:
                        summary, references = result
                    
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
                    return
                
                except Exception as e:
                    logger.exception("Web search failed: %s", e)
                    await send_long_message(message.channel, f"⚠️ Web Search Error: {e}")
                    return
            
            else:
                # Fallback to LLM
                if groq_service is None:
                    await send_long_message(message.channel, "⚠️ AI Error: Monsterrr's AI is not available. Please check configuration.")
                    return
                
                ai_reply = await asyncio.to_thread(_call_groq, content, GROQ_MODEL)
                if not ai_reply:
                    await send_long_message(message.channel, "Sorry, I couldn't generate a response.")
                    return
                
                org = os.getenv("GITHUB_ORG", "unknown")
                answer = re.sub(r"(?i)the GitHub organization I manage( is called| is|:)? [^\n.]+", 
                               f"the GitHub organization I manage is called {org}", ai_reply)
                
                conversation_memory[user_id].append({"role": "assistant", "content": answer})
                try:
                    embed = create_professional_embed("Monsterrr", answer)
                    await message.channel.send(embed=embed)
                except Exception:
                    await send_long_message(message.channel, answer)
                return
        
        except Exception as e:
            logger.exception("AI reply failed: %s", e)
            try:
                await send_long_message(message.channel, f"⚠️ AI Error: {e}")
            except Exception:
                pass

# Discord Commands
@bot.command(name="repos")
async def repos_cmd(ctx: commands.Context):
    """List all managed repositories."""
    try:
        github = GitHubService(logger=logger)
        repos = github.list_repositories() if hasattr(github, "list_repositories") else []
        if repos:
            repo_list = "\n".join(f"- {r['name']}" if isinstance(r, dict) and 'name' in r else f"- {r}" for r in repos)
            embed = create_professional_embed("Repositories", repo_list)
            await ctx.send(embed=embed)
        else:
            await ctx.send("No repositories found.")
    except Exception as e:
        await ctx.send(f"Error listing repositories: {e}")

@bot.command(name="roadmap")
async def roadmap_cmd(ctx: commands.Context, *, project: str = None):
    """Generate a roadmap for a project."""
    if not project:
        await ctx.send("Please specify a project name.")
        return
    
    try:
        roadmap = roadmap_service.generate_roadmap(project) if hasattr(roadmap_service, "generate_roadmap") else None
        if roadmap:
            embed = create_professional_embed(f"Roadmap for {project}", roadmap)
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"No roadmap could be generated for {project}.")
    except Exception as e:
        await ctx.send(f"Error generating roadmap: {e}")

@bot.command(name="assign")
async def assign_cmd(ctx: commands.Context, user: str, *, task: str):
    """Assign a task to a contributor."""
    try:
        github = GitHubService(logger=logger)
        result = github.assign_task(user, task) if hasattr(github, "assign_task") else None
        await ctx.send(f"Task '{task}' assigned to {user}.{' Result: ' + str(result) if result else ''}")
    except Exception as e:
        await ctx.send(f"Error assigning task: {e}")

@bot.command(name="tasks")
async def tasks_cmd(ctx: commands.Context, user: str = None):
    """View tasks for a user or all users."""
    try:
        tasks = task_manager.get_tasks(user) if hasattr(task_manager, "get_tasks") else None
        if tasks:
            task_list = "\n".join(f"- {t}" for t in tasks)
            embed = create_professional_embed(f"Tasks for {user or 'all users'}", task_list)
            await ctx.send(embed=embed)
        else:
            await ctx.send("No tasks found.")
    except Exception as e:
        await ctx.send(f"Error retrieving tasks: {e}")

@bot.command(name="triage")
async def triage_cmd(ctx: commands.Context, *, item: str):
    """AI-powered triage for issues/PRs."""
    try:
        result = triage_service.triage(item) if hasattr(triage_service, "triage") else None
        await ctx.send(f"Triage result: {result}")
    except Exception as e:
        await ctx.send(f"Error in triage: {e}")

@bot.command(name="onboard")
async def onboard_cmd(ctx: commands.Context, user: str):
    """Onboard a new contributor."""
    try:
        result = onboarding_service.onboard(user) if hasattr(onboarding_service, "onboard") else None
        await ctx.send(f"Onboarding result: {result}")
    except Exception as e:
        await ctx.send(f"Error in onboarding: {e}")

@bot.command(name="merge")
async def merge_cmd(ctx: commands.Context, pr: str):
    """Auto-merge a PR."""
    try:
        github = GitHubService(logger=logger)
        result = github.merge_pull_request(pr) if hasattr(github, "merge_pull_request") else None
        await ctx.send(f"Merge result: {result}")
    except Exception as e:
        await ctx.send(f"Error merging PR: {e}")

@bot.command(name="close")
async def close_cmd(ctx: commands.Context, issue: str):
    """Auto-close an issue."""
    try:
        github = GitHubService(logger=logger)
        result = github.close_issue(issue) if hasattr(github, "close_issue") else None
        await ctx.send(f"Close result: {result}")
    except Exception as e:
        await ctx.send(f"Error closing issue: {e}")

@bot.command(name="recognize")
async def recognize_cmd(ctx: commands.Context, user: str):
    """Send contributor recognition."""
    try:
        result = recognition_service.recognize(user) if hasattr(recognition_service, "recognize") else None
        await ctx.send(f"Recognition result: {result}")
    except Exception as e:
        await ctx.send(f"Error in recognition: {e}")

@bot.command(name="report")
async def report_cmd(ctx: commands.Context, period: str = "daily"):
    """Executive reports."""
    try:
        result = report_service.generate_report(period) if hasattr(report_service, "generate_report") else None
        if not result:
            await ctx.send("No report available.")
            return
        # Split report into sections for embed fields
        lines = result.split('\n')
        title = f"Monsterrr {period.capitalize()} Report"
        embed = discord.Embed(title=title, color=0x2d7ff9)
        section = None
        value_lines = []
        for line in lines:
            if line.strip() == "":
                continue
            if any(line.startswith(h) for h in ["System Status:", "Top Ideas", "Active Repositories", "Branches", "Pull Requests", "Issues", "CI Pipeline", "Security Alerts", "Automation Bots", "Active Queue", "Analytics", "Tasks", "Recent User Activity", "What I can do next:", "Actions performed today:", "No actions recorded today."]):
                if section and value_lines:
                    embed.add_field(name=section, value="\n".join(value_lines)[:1024], inline=False)
                section = line.replace(":", "").strip()
                value_lines = []
            else:
                value_lines.append(line)
        if section and value_lines:
            embed.add_field(name=section, value="\n".join(value_lines)[:1024], inline=False)
        embed.set_footer(text=f"Monsterrr • {datetime.now(IST).strftime('%Y-%m-%d %H:%M IST')}")
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"Error generating report: {e}")

@bot.command(name="analytics")
async def analytics_cmd(ctx: commands.Context):
    """View analytics dashboard."""
    try:
        result = analytics_service.get_dashboard() if analytics_service and hasattr(analytics_service, "get_dashboard") else None
        if result:
            embed = create_professional_embed("Analytics Dashboard", str(result))
            await ctx.send(embed=embed)
        else:
            await ctx.send("Analytics not available.")
    except Exception as e:
        await ctx.send(f"Error retrieving analytics: {e}")

@bot.command(name="docs")
async def docs_cmd(ctx: commands.Context, repo: str):
    """Update documentation for a repo."""
    try:
        result = doc_service.update_docs(repo) if hasattr(doc_service, "update_docs") else None
        await ctx.send(f"Docs update: {result}")
    except Exception as e:
        await ctx.send(f"Error updating docs: {e}")

@bot.command(name="scan")
async def scan_cmd(ctx: commands.Context, repo: str):
    """Security scan for a repo."""
    try:
        github = GitHubService(logger=logger)
        result = github.scan_repository(repo) if hasattr(github, "scan_repository") else None
        await ctx.send(f"Scan result: {result}")
    except Exception as e:
        await ctx.send(f"Error scanning repository: {e}")

@bot.command(name="review")
async def review_cmd(ctx: commands.Context, pr: str):
    """AI-powered code review."""
    try:
        from .code_review_service import CodeReviewService
        code_review = CodeReviewService()
        result = code_review.review_pr(pr) if hasattr(code_review, "review_pr") else None
        await ctx.send(f"Review result: {result}")
    except Exception as e:
        await ctx.send(f"Error in code review: {e}")

@bot.command(name="alert")
async def alert_cmd(ctx: commands.Context, *, event: str):
    """Send a real-time alert."""
    try:
        result = alert_service.send_alert(event) if alert_service and hasattr(alert_service, "send_alert") else None
        await ctx.send(f"Alert: {result}")
    except Exception as e:
        await ctx.send(f"Error sending alert: {e}")

@bot.command(name="poll")
async def poll_cmd(ctx: commands.Context, *, question: str):
    """Create a poll."""
    try:
        result = poll_service.create_poll(question) if hasattr(poll_service, "create_poll") else None
        await ctx.send(f"Poll: {result}")
    except Exception as e:
        await ctx.send(f"Error creating poll: {e}")

@bot.command(name="notify")
async def notify_cmd(ctx: commands.Context, *, message: str):
    """Send a notification."""
    try:
        result = notification_service.notify(message) if notification_service and hasattr(notification_service, "notify") else None
        await ctx.send(f"Notification: {result}")
    except Exception as e:
        await ctx.send(f"Error sending notification: {e}")

# Add new command handlers for enhanced functionality
@bot.command(name="brainstorm")
async def brainstorm_cmd(ctx: commands.Context, *, topic: str = None):
    """Brainstorm new project ideas."""
    try:
        from agents.idea_agent import IdeaGeneratorAgent
        idea_agent = IdeaGeneratorAgent(groq_service, logger)
        ideas = idea_agent.fetch_and_rank_ideas(top_n=5)
        
        if ideas:
            idea_list = "\n".join([
                f"**{i.get('name', 'Project')}**\n"
                f"Description: {i.get('description', 'N/A')}\n"
                f"Tech Stack: {', '.join(i.get('tech_stack', []))}\n"
                f"Features: {', '.join(i.get('features', []))}"
                for i in ideas
            ])
            embed = create_professional_embed("Brainstormed Ideas", idea_list)
            await ctx.send(embed=embed)
        else:
            await ctx.send("No ideas could be generated at this time.")
    except Exception as e:
        await ctx.send(f"Error brainstorming ideas: {e}")

@bot.command(name="plan")
async def plan_cmd(ctx: commands.Context):
    """Generate a daily plan for contributions."""
    try:
        from agents.maintainer_agent import MaintainerAgent
        from services.github_service import GitHubService
        github = GitHubService(logger=logger)
        maintainer = MaintainerAgent(github, groq_service, logger)
        plan = maintainer.plan_daily_contributions(num_contributions=3)
        
        if plan:
            plan_text = "\n".join([
                f"**{p.get('type', 'task').title()}:** {p.get('name', 'N/A')}\n"
                f"Description: {p.get('description', 'N/A')}\n"
                f"Details: {p.get('details', 'N/A')}"
                for p in plan
            ])
            embed = create_professional_embed("Daily Contribution Plan", plan_text)
            await ctx.send(embed=embed)
        else:
            await ctx.send("No plan could be generated at this time.")
    except Exception as e:
        await ctx.send(f"Error generating plan: {e}")

@bot.command(name="execute")
async def execute_cmd(ctx: commands.Context):
    """Execute the daily plan."""
    try:
        from agents.maintainer_agent import MaintainerAgent
        from agents.creator_agent import CreatorAgent
        from services.github_service import GitHubService
        
        github = GitHubService(logger=logger)
        maintainer = MaintainerAgent(github, groq_service, logger)
        creator = CreatorAgent(github, logger)
        
        # Get the latest plan
        import glob
        import json
        plan_files = glob.glob("logs/daily_plan_*.json")
        if plan_files:
            plan_files.sort(reverse=True)
            with open(plan_files[0], "r", encoding="utf-8") as f:
                plan = json.load(f)
            
            maintainer.execute_daily_plan(plan, creator_agent=creator)
            await ctx.send("Daily plan execution started. Check back later for results.")
        else:
            await ctx.send("No plan found to execute. Generate a plan first with `!plan`.")
    except Exception as e:
        await ctx.send(f"Error executing plan: {e}")

@bot.command(name="improve")
async def improve_cmd(ctx: commands.Context, repo: str):
    """Improve an existing repository."""
    try:
        from agents.creator_agent import CreatorAgent
        from services.github_service import GitHubService
        
        github = GitHubService(logger=logger)
        creator = CreatorAgent(github, logger)
        
        # Create a dummy idea for improvement
        idea = {
            "name": repo,
            "description": f"Improvement for {repo}",
            "tech_stack": [],
            "roadmap": [f"Improve {repo} functionality"]
        }
        
        creator._improve_repository(repo, idea["description"], idea["roadmap"], idea["tech_stack"])
        await ctx.send(f"Improvement process started for repository: {repo}")
    except Exception as e:
        await ctx.send(f"Error improving repository: {e}")

@bot.command(name="maintain")
async def maintain_cmd(ctx: commands.Context):
    """Perform maintenance on all repositories."""
    try:
        from agents.maintainer_agent import MaintainerAgent
        from services.github_service import GitHubService
        
        github = GitHubService(logger=logger)
        maintainer = MaintainerAgent(github, groq_service, logger)
        maintainer.perform_maintenance()
        
        await ctx.send("Maintenance tasks started across all repositories.")
    except Exception as e:
        await ctx.send(f"Error performing maintenance: {e}")


@bot.command(name="language")
async def language_cmd(ctx: commands.Context, lang: str, *, text: str):
    """Translate text to another language."""
    try:
        result = language_service.translate(lang, text) if hasattr(language_service, "translate") else None
        await ctx.send(f"Translation: {result}")
    except Exception as e:
        await ctx.send(f"Error in translation: {e}")

@bot.command(name="integrate")
async def integrate_cmd(ctx: commands.Context, platform: str):
    """Integrate with other platforms."""
    try:
        result = integration_service.integrate(platform) if hasattr(integration_service, "integrate") else None
        await ctx.send(f"Integration: {result}")
    except Exception as e:
        await ctx.send(f"Error in integration: {e}")

@bot.command(name="qa")
async def qa_cmd(ctx: commands.Context, time: str):
    """Schedule a Q&A session."""
    try:
        result = qa_service.schedule_qa(time) if hasattr(qa_service, "schedule_qa") else None
        await ctx.send(f"Q&A scheduled: {result}")
    except Exception as e:
        await ctx.send(f"Error scheduling Q&A: {e}")

@bot.command(name="buildcmd")
async def buildcmd_cmd(ctx: commands.Context, *, spec: str):
    """Build a command from a specification."""
    try:
        result = command_builder.build_command(spec) if command_builder and hasattr(command_builder, "build_command") else None
        await ctx.send(f"Command built: {result}")
    except Exception as e:
        await ctx.send(f"Error building command: {e}")

@bot.command(name="codereview")
async def codereview_cmd(ctx: commands.Context, *, code: str):
    """AI-powered code review."""
    try:
        from .code_review_service import CodeReviewService
        code_review = CodeReviewService()
        result = code_review.review_code(code) if hasattr(code_review, "review_code") else None
        await ctx.send(f"Code review: {result}")
    except Exception as e:
        await ctx.send(f"Error in code review: {e}")

@bot.command(name="customcmd")
async def customcmd_cmd(ctx: commands.Context, name: str, *, action: str):
    """Create a custom command."""
    custom_commands[name] = action
    await ctx.send(f"Custom command '{name}' created.")

@bot.command(name="search")
async def search_cmd(ctx, *, query: str):
    """Search the web and summarize results using AI."""
    if not search_service:
        await ctx.send("Web search is not available.")
        return
    async with ctx.typing():
        try:
            result = await search_service.search_and_summarize(query)
            summary = None
            references = None
            if isinstance(result, dict):
                summary = result.get("summary") or result.get("answer") or ""
                references = result.get("references") or result.get("sources") or result.get("urls")
            elif isinstance(result, tuple) and len(result) == 2:
                summary, references = result
            else:
                summary = str(result)
            if not summary or "summarization failed" in summary.lower():
                await ctx.send("Search succeeded, but summarization failed. Please try a different query or check the LLM configuration.")
                return
            ref_text = ""
            if references:
                if isinstance(references, (list, tuple)):
                    ref_lines = [f"[{i+1}] {url}" for i, url in enumerate(references)]
                    ref_text = "\n\n**References:**\n" + "\n".join(ref_lines)
                elif isinstance(references, str):
                    ref_text = f"\n\n**References:**\n{references}"
            full_text = (summary or "") + (ref_text or "")
            embed = create_professional_embed("Monsterrr Web Search", full_text)
            await ctx.send(embed=embed)
            # Sync search result to shared state for agent-bot sync
            update_shared_state("search", {"query": query, "summary": summary, "references": references, "timestamp": datetime.now(IST).isoformat()})
        except Exception as e:
            logger.exception("Web search failed: %s", e)
            await ctx.send(f"⚠️ Web Search Error: {e}")

def update_shared_state(key, value):
    """Update the shared monsterrr_state.json for agent-bot sync."""
    try:
        import json
        state_path = "monsterrr_state.json"
        if os.path.exists(state_path):
            with open(state_path, "r", encoding="utf-8") as f:
                state = json.load(f)
        else:
            state = {}
        state[key] = value
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to update shared state: {e}")

@bot.command(name="guide", aliases=["help"])
async def guide_cmd(ctx: commands.Context):
    """Show comprehensive command guide."""
    embed = discord.Embed(
        title="📘 Monsterrr Discord Interface — Command Guide",
        description="Here's a full list of available commands and their usage:",
        color=discord.Color.blue()
    )
    
    commands_list = {
        "🧭 General": [
            "`!guide` — Show all available commands and usage instructions.",
            "`!help` — Show all available commands and usage instructions.",
            "`!status` — Get current Monsterrr system status.",
            "`!ideas` — View top AI-generated ideas.",
            "`!search <query or url>` — Search the web and summarize results.",
            "`!alert <event>` — Show real-time alerts.",
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
            "`!buildcmd <spec>` — Build a command from a specification.",
            "`!integrate <platform>` — Integrate with other platforms.",
            "`!qa <time>` — Schedule a Q&A session."
        ],
        "🧠 Autonomous AI Operations": [
            "`!brainstorm` — Generate new project ideas autonomously.",
            "`!plan` — Create a daily contribution plan.",
            "`!execute` — Execute the daily plan.",
            "`!improve <repo>` — Improve an existing repository.",
            "`!maintain` — Perform maintenance on all repositories."
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
    update_system_status_in_state()
    """Get current Monsterrr system status (with agent/service sync)."""
    try:
        org = os.getenv("GITHUB_ORG", "unknown")
        now_ist = datetime.now(IST)
        uptime = str(now_ist - STARTUP_TIME).split(".")[0]
        try:
            cpu = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            mem_usage = f"{mem.percent:.1f}% (≈ {mem.used // (1024**2)} MB of {mem.total // (1024**2)} MB allocated)"
        except Exception:
            cpu = "N/A"
            mem_usage = "N/A"
        try:
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
        except Exception:
            hostname = "Unknown"
            ip = "Unknown"

        try:
            with open("monsterrr_state.json", "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            state = {}

        # Compose embed
        embed = discord.Embed(
            title="🤖 Monsterrr System Status",
            description=f"**Organization:** {org}\n**Startup:** {STARTUP_TIME.strftime('%Y-%m-%d %H:%M:%S IST')}\n**Uptime:** {uptime}",
            color=0x2d7ff9
        )
        embed.add_field(name="Model", value=GROQ_MODEL, inline=True)
        embed.add_field(name="Guilds", value=str(len(bot.guilds)), inline=True)
        embed.add_field(name="Members", value=str(sum(g.member_count for g in bot.guilds)), inline=True)
        embed.add_field(name="CPU Usage", value=str(cpu), inline=True)
        embed.add_field(name="Memory Usage", value=str(mem_usage), inline=True)
        embed.add_field(name="Host", value=f"{hostname} ({ip})", inline=True)
        total_messages = state.get("total_messages", "N/A")
        embed.add_field(name="Total Messages", value=str(total_messages), inline=True)

        # Orchestrator status
        orch = state.get("orchestrator", {})
        embed.add_field(
            name="Orchestrator",
            value=f"Last Run: {orch.get('last_run', 'N/A')}\nLast Success: {orch.get('last_success', 'N/A')}\nLast Error: {orch.get('last_error', 'None')}\nLog: {orch.get('last_log', 'N/A')}",
            inline=False
        )

        # Top ideas
        ideas = state.get("ideas", {}).get("top_ideas", [])
        if ideas:
            idea_lines = [f"• **{i.get('name','')}**: {i.get('description','')}" for i in ideas[:3]]
            embed.add_field(name="Top Ideas", value="\n".join(idea_lines), inline=False)

        # Active repos
        repos = state.get("repos", [])
        if repos:
            repo_lines = [f"• **{r.get('name','')}**: {r.get('description','')}" for r in repos[:3]]
            embed.add_field(name="Active Repositories", value="\n".join(repo_lines), inline=False)

        # Issues summary
        issues = state.get("issues", {})
        if issues:
            embed.add_field(
                name="Issues",
                value=f"Total: {issues.get('count','N/A')} | Critical: {issues.get('critical',0)} | High: {issues.get('high',0)} | Medium: {issues.get('medium',0)} | Low: {issues.get('low',0)}",
                inline=False
            )

        # CI status
        ci = state.get("ci", {})
        if ci:
            embed.add_field(
                name="CI Pipeline",
                value=f"Status: {ci.get('status','N/A')} | Avg Duration: {ci.get('avg_duration','N/A')}",
                inline=False
            )

        # Security alerts
        sec = state.get("security", {})
        if sec:
            embed.add_field(
                name="Security Alerts",
                value=f"Critical: {sec.get('critical_alerts',0)} | Warnings: {sec.get('warnings',0)}",
                inline=False
            )

        # Recent actions (today)
        actions = state.get("actions", [])
        if actions:
            today = now_ist.date()
            action_lines = []
            for a in actions:
                try:
                    ts = a.get("timestamp")
                    ts_date = datetime.fromisoformat(ts).date() if ts else None
                    if ts_date == today:
                        action_type = a.get("type", "action")
                        details = a.get("details", {})
                        if action_type == "ideas_fetched":
                            action_lines.append(f"💡 Ideas fetched: {details.get('count',0)}")
                        elif action_type == "daily_plan":
                            plan = details.get('plan', [])
                            plan_str = '; '.join(str(p) for p in plan)
                            action_lines.append(f"📝 Planned: {plan_str}")
                        elif action_type == "plan_executed":
                            plan = details.get('plan', [])
                            plan_str = '; '.join(str(p) for p in plan)
                            action_lines.append(f"✅ Executed: {plan_str}")
                        elif action_type == "maintenance":
                            action_lines.append("🛠️ Maintenance performed")
                        else:
                            action_lines.append(f"🔹 {action_type}: {details}")
                except Exception:
                    continue
            if action_lines:
                embed.add_field(name="Today's Actions", value="\n".join(action_lines), inline=False)

        embed.set_footer(text="✨ Powered by Monsterrr — All services are always available as commands.")
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"Error retrieving status: {e}")

# --- IDEAS COMMAND ---
@bot.command(name="ideas")
async def ideas_cmd(ctx: commands.Context):
    """Show top AI-generated ideas."""
    try:
        import json
        with open("monsterrr_state.json", "r", encoding="utf-8") as f:
            state = json.load(f)
        ideas = state.get("ideas", {}).get("top_ideas", [])
        if ideas:
            idea_list = "\n".join(f"- **{i.get('name','')}**: {i.get('description','')}" for i in ideas)
            embed = create_professional_embed("Top Ideas", idea_list)
            await ctx.send(embed=embed)
        else:
            await ctx.send("No ideas found.")
    except Exception as e:
        await ctx.send(f"Error retrieving ideas: {e}")

# Run the bot
def run_bot():
    """Run the Discord bot."""
    if not DISCORD_TOKEN:
        logger.error("DISCORD_BOT_TOKEN environment variable not set")
        return
    
    try:
        bot.run(DISCORD_TOKEN)
    except Exception as e:
        logger.error(f"Failed to run bot: {e}")

if __name__ == "__main__":
    run_bot()