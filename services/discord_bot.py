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
import discord
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
STARTUP_TIME = datetime.utcnow()
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

# GitHub service (ensure logger exists)
try:
    github_service = GitHubService(logger=logger)
except TypeError:
    github_service = GitHubService()
    setattr(github_service, "logger", logger)

# Groq client (wrap different possible implementations)
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

# Expose `client` as alias used in older code
client = groq_service

# ---------------------------
# Discord bot setup
# ---------------------------
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
    embed.set_footer(text=f"Monsterrr • Status at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}")
    return embed

def get_system_context(user_id: Optional[str] = None) -> str:
    now = datetime.utcnow()
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
    ctx = (
        f"Current UTC time: {now.strftime('%Y-%m-%d %H:%M:%S')}. "
        f"Startup: {STARTUP_TIME.strftime('%Y-%m-%d %H:%M:%S')}. "
        f"Uptime: {uptime}. "
        f"Model: {GROQ_MODEL}. "
        f"Total messages received: {total_messages}. "
        f"Recent user messages: {recent_user_msgs[-3:] if recent_user_msgs else 'None'}. "
        f"Recent users: {recent_users if recent_users else 'None'}. "
        f"CPU: {cpu}. Memory: {mem_usage}. "
        f"Hostname: {hostname}. IP: {ip}. "
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
                    f"Startup time: {STARTUP_TIME.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
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
                    # Gather professional status report data
                    status_text = (
                        f"**🤖 Monsterrr System Status**\n"
                        f"Startup time: {STARTUP_TIME.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
                        f"Model: {GROQ_MODEL}\n"
                        f"Guilds: {len(bot.guilds)}\nMembers: {sum(g.member_count for g in bot.guilds)}\n"
                        f"Total messages: {total_messages}\n"
                    )
                    # Add ideas, tasks, analytics, etc.
                    try:
                        with open("monsterrr_state.json", "r", encoding="utf-8") as f:
                            state = __import__("json").load(f)
                        ideas = state.get("ideas", {}).get("top_ideas", [])
                        repos = state.get("repos", [])
                        status_text += f"\n**Top Ideas:**\n" + "\n".join([f"• {i['name']}: {i['description']}" for i in ideas])
                        status_text += f"\n**Repos:**\n" + "\n".join([f"• {r['name']}: {r['description']}" for r in repos])
                    except Exception as e:
                        status_text += "\n(No state file found)"
                        logger.error(f"Hourly report: Could not read monsterrr_state.json: {e}")
                    await ch.send(embed=format_embed("Monsterrr Hourly Status", status_text, 0x2d7ff9))
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
    now = datetime.utcnow()
    startup = STARTUP_TIME.strftime('%Y-%m-%d %H:%M:%S UTC')
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
    html += f"<p style='font-size:0.95em;color:#888;'>Report generated at {now.strftime('%Y-%m-%d %H:%M UTC')}</p>"
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

@bot.event
async def on_message(message: discord.Message):
    # 1) ignore bots
    if message.author.bot:
        return

    # 2) in-process dedupe (prevents double-handling inside same process)
    try:
        # Use a set for processed message IDs, keep only recent ones
        global _processed_message_ids
        if '_processed_message_ids' not in globals():
            _processed_message_ids = set()
        if message.id in _processed_message_ids:
            logger.info(f"Duplicate message detected: {message.id}")
            return
        _processed_message_ids.add(message.id)
        # Optionally, keep set size reasonable
        if len(_processed_message_ids) > 10000:
            _processed_message_ids = set(list(_processed_message_ids)[-5000:])
    except Exception as e:
        logger.error(f"Deduplication error: {e}")

    # 3) If this looks like a command: let discord.py command processor handle it (single call)
    if message.content and message.content.lstrip().startswith(bot.command_prefix):
        await bot.process_commands(message)
        return

    # 4) Non-command messages -> AI path
    content = (message.content or "").strip()
    if not content:
        return

    user_id = str(message.author.id)
    conversation_memory[user_id].append({"role": "user", "content": content})
    unique_users.add(user_id)
    global total_messages
    total_messages += 1

    # --- Natural Language Command Parsing ---
    # Simple intent detection: if message contains certain keywords, treat as command
    command_intents = [
        ("create repo", "create_repository"),
        ("assign task", "assign_task"),
        ("show ideas", "show_ideas"),
        ("status", "show_status"),
        ("add idea", "add_idea"),
        ("merge", "merge_pull_request"),
        # Add more as needed
    ]
    intent = None
    for kw, cmd in command_intents:
        if kw in content.lower():
            intent = cmd
            break

    system_ctx = get_system_context(user_id)
    prompt_lines = [f"SYSTEM: {system_ctx}", "", "CONVERSATION:"]
    for m in conversation_memory[user_id]:
        role = m.get("role", "user")
        prompt_lines.append(f"{role.upper()}: {m.get('content','')}")
    prompt = "\n".join(prompt_lines)

    try:
        async with message.channel.typing():
            if intent:
                # Example: call a function based on intent
                reply = await handle_natural_command(intent, content, user_id)
                conversation_memory[user_id].append({"role": "assistant", "content": reply})
                await message.channel.send(reply)
            else:
                ai_reply = await asyncio.to_thread(_call_groq, prompt, GROQ_MODEL)
                if not ai_reply:
                    await message.channel.send("Sorry, I couldn't generate a response.")
                    return
                conversation_memory[user_id].append({"role": "assistant", "content": ai_reply})
                await message.channel.send(ai_reply)
    except Exception as e:
        logger.exception("AI reply failed: %s", e)
        try:
            await message.channel.send(f"⚠️ AI Error: {e}")
        except Exception:
            pass

# --- Handler for natural language commands ---
async def handle_natural_command(intent, content, user_id):
    # Fully autonomous Jarvis-like implementation
    # You can expand this with real integrations and logic
    # Expanded command set for full autonomy
    if intent == "create_repository":
        repo_name = extract_argument(content, "repo")
        if repo_name:
            try:
                from services.github_service import GitHubService
                github = GitHubService(logger=logger)
                github.create_repository(repo_name)
                return f"Repository '{repo_name}' created successfully."
            except Exception as e:
                return f"Failed to create repository: {e}"
        return "Please specify the repository name."
    elif intent == "delete_repository":
        repo_name = extract_argument(content, "repo")
        if repo_name:
            try:
                from services.github_service import GitHubService
                github = GitHubService(logger=logger)
                github.delete_repository(repo_name)
                return f"Repository '{repo_name}' deleted successfully."
            except Exception as e:
                return f"Failed to delete repository: {e}"
        return "Please specify the repository name."
    elif intent == "assign_task":
        user, task = extract_user_and_task(content)
        if user and task:
            # Here you would update monsterrr_state.json or your task manager
            return f"Task '{task}' assigned to {user}."
        return "Please specify both user and task."
    elif intent == "show_ideas":
        try:
            with open("monsterrr_state.json", "r", encoding="utf-8") as f:
                state = __import__("json").load(f)
            ideas = state.get("ideas", {}).get("top_ideas", [])
            if ideas:
                return "Top Ideas:\n" + "\n".join([f"• {i['name']}: {i['description']}" for i in ideas])
            else:
                return "No ideas found."
        except Exception as e:
            return f"Could not read ideas: {e}"
    elif intent == "delete_idea":
        idea = extract_argument(content, "idea")
        if idea:
            try:
                with open("monsterrr_state.json", "r", encoding="utf-8") as f:
                    state = __import__("json").load(f)
                ideas = state.get("ideas", {}).get("top_ideas", [])
                state["ideas"]["top_ideas"] = [i for i in ideas if i["name"] != idea]
                with open("monsterrr_state.json", "w", encoding="utf-8") as f:
                    __import__("json").dump(state, f, indent=2)
                return f"Idea '{idea}' deleted successfully."
            except Exception as e:
                return f"Failed to delete idea: {e}"
        return "Please specify the idea to delete."
    elif intent == "show_status":
        return f"System Status:\nStartup: {STARTUP_TIME}\nModel: {GROQ_MODEL}\nGuilds: {len(bot.guilds)}\nMembers: {sum(g.member_count for g in bot.guilds)}\nTotal messages: {total_messages}"
    elif intent == "add_idea":
        idea = extract_argument(content, "idea")
        if idea:
            try:
                with open("monsterrr_state.json", "r", encoding="utf-8") as f:
                    state = __import__("json").load(f)
            except Exception:
                state = {}
            ideas = state.setdefault("ideas", {}).setdefault("top_ideas", [])
            ideas.append({"name": idea, "description": "Added by AI"})
            try:
                with open("monsterrr_state.json", "w", encoding="utf-8") as f:
                    __import__("json").dump(state, f, indent=2)
                return f"Idea '{idea}' added successfully."
            except Exception as e:
                return f"Failed to add idea: {e}"
        return "Please specify the idea to add."
    elif intent == "merge_pull_request":
        pr_id = extract_argument(content, "pr")
        if pr_id:
            # Here you would call your merge logic
            return f"Pull request '{pr_id}' merged."
        return "Please specify the pull request ID."
    elif intent == "close_issue":
        issue_id = extract_argument(content, "issue")
        if issue_id:
            # Here you would call your close issue logic
            return f"Issue '{issue_id}' closed."
        return "Please specify the issue ID."
    elif intent == "schedule_message":
        msg, delay = extract_message_and_delay(content)
        if msg and delay:
            asyncio.create_task(schedule_discord_message(msg, delay))
            return f"Message scheduled to be sent in {delay} seconds."
        return "Please specify message and delay."
    elif intent == "self_update":
        new_model = extract_argument(content, "model")
        if new_model:
            os.environ["GROQ_MODEL"] = new_model
            return f"Model updated to {new_model}."
        return "Please specify the new model."
    elif intent == "show_repos":
        try:
            with open("monsterrr_state.json", "r", encoding="utf-8") as f:
                state = __import__("json").load(f)
            repos = state.get("repos", [])
            if repos:
                return "Repositories:\n" + "\n".join([f"• {r['name']}: {r['description']}" for r in repos])
            else:
                return "No repositories found."
        except Exception as e:
            return f"Could not read repositories: {e}"
    elif intent == "add_repo":
        repo_name = extract_argument(content, "repo")
        if repo_name:
            try:
                with open("monsterrr_state.json", "r", encoding="utf-8") as f:
                    state = __import__("json").load(f)
            except Exception:
                state = {}
            repos = state.setdefault("repos", [])
            repos.append({"name": repo_name, "description": "Added by AI"})
            try:
                with open("monsterrr_state.json", "w", encoding="utf-8") as f:
                    __import__("json").dump(state, f, indent=2)
                return f"Repository '{repo_name}' added to state."
            except Exception as e:
                return f"Failed to add repository: {e}"
        return "Please specify the repository to add."
    elif intent == "delete_repo":
        repo_name = extract_argument(content, "repo")
        if repo_name:
            try:
                with open("monsterrr_state.json", "r", encoding="utf-8") as f:
                    state = __import__("json").load(f)
                repos = state.get("repos", [])
                state["repos"] = [r for r in repos if r["name"] != repo_name]
                with open("monsterrr_state.json", "w", encoding="utf-8") as f:
                    __import__("json").dump(state, f, indent=2)
                return f"Repository '{repo_name}' deleted from state."
            except Exception as e:
                return f"Failed to delete repository: {e}"
        return "Please specify the repository to delete."
    elif intent == "show_tasks":
        try:
            with open("monsterrr_state.json", "r", encoding="utf-8") as f:
                state = __import__("json").load(f)
            tasks = state.get("tasks", {})
            if tasks:
                return "Tasks:\n" + "\n".join([f"• {user}: {', '.join(tlist)}" for user, tlist in tasks.items()])
            else:
                return "No tasks found."
        except Exception as e:
            return f"Could not read tasks: {e}"
    elif intent == "add_task":
        user, task = extract_user_and_task(content)
        if user and task:
            try:
                with open("monsterrr_state.json", "r", encoding="utf-8") as f:
                    state = __import__("json").load(f)
            except Exception:
                state = {}
            tasks = state.setdefault("tasks", {})
            tasks.setdefault(user, []).append(task)
            try:
                with open("monsterrr_state.json", "w", encoding="utf-8") as f:
                    __import__("json").dump(state, f, indent=2)
                return f"Task '{task}' added for {user}."
            except Exception as e:
                return f"Failed to add task: {e}"
        return "Please specify both user and task."
    elif intent == "delete_task":
        user, task = extract_user_and_task(content)
        if user and task:
            try:
                with open("monsterrr_state.json", "r", encoding="utf-8") as f:
                    state = __import__("json").load(f)
                tasks = state.get("tasks", {})
                if user in tasks:
                    tasks[user] = [t for t in tasks[user] if t != task]
                    with open("monsterrr_state.json", "w", encoding="utf-8") as f:
                        __import__("json").dump(state, f, indent=2)
                    return f"Task '{task}' deleted for {user}."
                else:
                    return f"No tasks found for {user}."
            except Exception as e:
                return f"Failed to delete task: {e}"
        return "Please specify both user and task."
    elif intent == "show_analytics":
        try:
            with open("monsterrr_state.json", "r", encoding="utf-8") as f:
                state = __import__("json").load(f)
            analytics = state.get("analytics", {})
            if analytics:
                return "Analytics:\n" + "\n".join([f"• {k}: {v}" for k, v in analytics.items()])
            else:
                return "No analytics found."
        except Exception as e:
            return f"Could not read analytics: {e}"
    elif intent == "add_analytics":
        key = extract_argument(content, "key")
        value = extract_argument(content, "value")
        if key and value:
            try:
                with open("monsterrr_state.json", "r", encoding="utf-8") as f:
                    state = __import__("json").load(f)
            except Exception:
                state = {}
            analytics = state.setdefault("analytics", {})
            analytics[key] = value
            try:
                with open("monsterrr_state.json", "w", encoding="utf-8") as f:
                    __import__("json").dump(state, f, indent=2)
                return f"Analytics '{key}: {value}' added."
            except Exception as e:
                return f"Failed to add analytics: {e}"
        return "Please specify both key and value."
    elif intent == "delete_analytics":
        key = extract_argument(content, "key")
        if key:
            try:
                with open("monsterrr_state.json", "r", encoding="utf-8") as f:
                    state = __import__("json").load(f)
                analytics = state.get("analytics", {})
                if key in analytics:
                    del analytics[key]
                    with open("monsterrr_state.json", "w", encoding="utf-8") as f:
                        __import__("json").dump(state, f, indent=2)
                    return f"Analytics '{key}' deleted."
                else:
                    return f"No analytics found for key '{key}'."
            except Exception as e:
                return f"Failed to delete analytics: {e}"
        return "Please specify the key to delete."
    elif intent == "integrate_platform":
        platform = extract_argument(content, "platform")
        if platform:
            # Here you would call your integration logic
            return f"Platform '{platform}' integrated."
        return "Please specify the platform to integrate."
    elif intent == "run_qa":
        time_str = extract_argument(content, "time")
        if time_str:
            # Here you would call your QA logic
            return f"QA scheduled at {time_str}."
        return "Please specify the time for QA."
    elif intent == "scan_repo":
        repo_name = extract_argument(content, "repo")
        if repo_name:
            # Here you would call your scan logic
            return f"Repository '{repo_name}' scanned."
        return "Please specify the repository to scan."
    elif intent == "review_pr":
        pr_id = extract_argument(content, "pr")
        if pr_id:
            # Here you would call your review logic
            return f"Pull request '{pr_id}' reviewed."
        return "Please specify the pull request ID."
    elif intent == "show_docs":
        repo_name = extract_argument(content, "repo")
        if repo_name:
            # Here you would call your docs logic
            return f"Documentation for '{repo_name}' displayed."
        return "Please specify the repository for docs."
    elif intent == "roadmap":
        project = extract_argument(content, "project")
        if project:
            # Here you would call your roadmap logic
            return f"Roadmap for project '{project}' displayed."
        return "Please specify the project for roadmap."
    elif intent == "guide":
        # Here you would call your guide logic
        return "Guide displayed."
    elif intent == "help":
        # Here you would call your help logic
        return "Help displayed."
    # Add more autonomous actions as needed
    return "Sorry, I couldn't understand your command."

# --- Helper functions for argument extraction and scheduling ---
def extract_argument(text, key):
    # Simple extraction: look for 'key: value' in text
    import re
    match = re.search(rf"{key}[:=]\s*(\w+)", text, re.IGNORECASE)
    return match.group(1) if match else None

def extract_user_and_task(text):
    # Example: 'assign task to @user: do something'
    import re
    user_match = re.search(r"@([\w]+)", text)
    task_match = re.search(r"task[:=]\s*(.+)", text)
    user = user_match.group(1) if user_match else None
    task = task_match.group(1) if task_match else None
    return user, task

def extract_message_and_delay(text):
    # Example: 'schedule message: Hello in 60 seconds'
    import re
    msg_match = re.search(r"message[:=]\s*([\w\s]+)", text)
    delay_match = re.search(r"in (\d+) seconds", text)
    msg = msg_match.group(1) if msg_match else None
    delay = int(delay_match.group(1)) if delay_match else None
    return msg, delay

async def schedule_discord_message(msg, delay):
    await asyncio.sleep(delay)
    if CHANNEL_ID:
        ch = bot.get_channel(int(CHANNEL_ID))
        if ch:
            await ch.send(msg)

# ---------------------------
# Command definitions (single occurrences)
# ---------------------------
@bot.command(name="help")
async def help_cmd(ctx: commands.Context):
    help_text = (
        "**Monsterrr Commands**\n"
        "• `!help` - show this help\n"
        "• `!guide` - show extended guide\n"
        "• `!status` - system & self-awareness status\n"
        "• `!ideas` - show active ideas/polls\n"
        "• `!assign @user <task>` - assign task\n"
        "• `!poll <question>` - start poll\n"
        "• `!customcmd <name> <action>` - create a custom command\n\n"
        "You can also chat normally (no `!`) in the configured channel or DM."
    )
    await ctx.send(help_text)

@bot.command(name="status")
async def status_command(ctx):
    import json
    from datetime import datetime

    try:
        with open("monsterrr_state.json", "r", encoding="utf-8") as f:
            state = json.load(f)
    except Exception:
        state = {}

    user_id = str(ctx.author.id)
    raw_context = get_system_context(user_id)  # This returns the long one-liner
    guild_count = len(bot.guilds)
    member_count = sum(guild.member_count for guild in bot.guilds)

    ideas = state.get("ideas", {}).get("top_ideas", [])
    repos = state.get("repos", [])
    analytics = state.get("analytics", {})

    # --- Format the context into readable lines ---
    def format_context(text: str) -> str:
        # Split on ". " to break sentences into items
        parts = [p.strip() for p in text.split(". ") if p.strip()]
        formatted = []
        for p in parts:
            if ": " in p:
                key, val = p.split(": ", 1)
                formatted.append(f"• **{key.strip()}:** {val.strip()}")
            else:
                formatted.append(p)  # fallback for sentences without colon
        return "\n".join(formatted)

    context = format_context(raw_context)

    # Build Embed
    embed = discord.Embed(
        title="🟢 Monsterrr System Status",
        description=f"**System Info**\n{context}\n\n**📌 Overview**\n"
                    f"• 💡 **Ideas:** `{len(ideas)}`\n"
                    f"• 📂 **Repos:** `{len(repos)}`\n"
                    f"• 🌐 **Guilds:** `{guild_count}`\n"
                    f"• 👥 **Members:** `{member_count}`",
        color=discord.Color.green()
    )

    # Top Ideas
    if ideas:
        top_ideas_text = "\n".join(
            [f"{i+1}. 💡 {idea['name']}" for i, idea in enumerate(ideas[:3])]
        )
        embed.add_field(name="✨ Top Ideas", value=top_ideas_text, inline=False)

    # Repos
    if repos:
        repos_text = "\n".join(
            [f"{i+1}. 📂 {repo['name']}" for i, repo in enumerate(repos[:3])]
        )
        embed.add_field(name="📂 Active Repos", value=repos_text, inline=False)

    # Analytics (if present in state.json separately)
    if analytics:
        analytics_text = "\n".join(
            [f"• **{key.replace('_',' ').title()}:** {value}" for key, value in analytics.items()]
        )
        embed.add_field(name="📊 Analytics", value=analytics_text[:1024], inline=False)

    # Footer
    embed.set_footer(
        text=f"Monsterrr • Status checked at {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
    )

    await ctx.send(embed=embed)


@bot.command(name="guide")
async def guide_cmd(ctx: commands.Context):
    embed = discord.Embed(
        title="📘 Monsterrr Discord Interface — Command Guide",
        description="Here’s a full list of available commands and their usage:",
        color=discord.Color.blue()
    )

    commands_list = {
        "🧭 General": [
            "`!guide` — Show all available commands and usage instructions.",
            "`!status` — Get current Monsterrr system status.",
            "`!ideas` — View top AI-generated ideas.",
            "`!alerts` — Real-time alerts.",
            "`!poll <question>` — Create a poll.",
            "`!language <lang> <text>` — Translate text."
        ],
        "📂 Project Management": [
            "`!repos` — List all managed repositories.",
            "`!roadmap <project>` — Generate a roadmap for a project.",
            "`!assign <user> <task>` — Assign a task to a contributor.",
            "`!tasks [user]` — View tasks for a user or all users.",
            "`!triage <issue|pr> <item>` — AI-powered triage for issues/PRs."
        ],
        "🏆 Contributor Tools": [
            "`!recognize <user>` — Send contributor recognition.",
            "`!onboard <user>` — Onboard a new contributor."
        ],
        "📊 Reports & Analytics": [
            "`!report [daily|weekly|monthly]` — Executive reports.",
            "`!analytics` — View analytics dashboard."
        ],
        "💻 Code & Repos": [
            "`!docs <repo>` — Update documentation for a repo.",
            "`!customcmd <name> <action>` — Create a custom command.",
            "`!integrate <platform>` — Integrate with other platforms.",
            "`!qa <time>` — Schedule a Q&A session.",
            "`!merge <pr>` — Auto-merge a PR.",
            "`!close <issue>` — Auto-close an issue.",
            "`!scan <repo>` — Security scan for a repo.",
            "`!review <pr>` — AI-powered code review."
        ]
    }

    for category, cmds in commands_list.items():
        embed.add_field(name=category, value="\n".join(cmds), inline=False)

    embed.set_footer(text="✨ Powered by Monsterrr — Making open-source collaboration smarter.")

    await ctx.send(embed=embed)


@bot.command(name="ideas")
async def ideas_cmd(ctx: commands.Context):
    state = {}
    try:
        with open("monsterrr_state.json", "r", encoding="utf-8") as f:
            state = __import__("json").load(f)
    except Exception:
        state = {}
    ideas = state.get("ideas", {}).get("top_ideas", []) if isinstance(state, dict) else []
    if not ideas:
        await ctx.send("No ideas found.")
        return
    msg = "Top Ideas:\n" + "\n".join([f"{i+1}. {idea.get('name','<no name>')}: {idea.get('description','')}" for i, idea in enumerate(ideas)])
    await ctx.send(msg)

@bot.command(name="repos")
async def repos_cmd(ctx: commands.Context):
    try:
        with open("monsterrr_state.json", "r", encoding="utf-8") as f:
            state = __import__("json").load(f)
    except Exception:
        state = {}
    repos = state.get("repos", []) if isinstance(state, dict) else []
    if not repos:
        await ctx.send("No repositories found.")
        return
    msg = "Managed Repositories:\n" + "\n".join([f"{i+1}. {repo.get('name','')}: {repo.get('description','')} ({repo.get('url','')})" for i, repo in enumerate(repos)])
    await ctx.send(msg)

@bot.command(name="roadmap")
async def roadmap_cmd(ctx: commands.Context, *, project: str = None):
    if not project:
        await ctx.send("Please specify a project name.")
        return
    try:
        with open("monsterrr_state.json", "r", encoding="utf-8") as f:
            state = __import__("json").load(f)
    except Exception:
        state = {}
    for repo in state.get("repos", []):
        if repo.get("name", "").lower() == project.lower():
            roadmap = repo.get("roadmap", [])
            msg = f"Roadmap for {project}:\n" + "\n".join([f"- {step}" for step in roadmap])
            await ctx.send(msg)
            return
    await ctx.send(f"Project '{project}' not found.")

@bot.command(name="tasks")
async def tasks_cmd(ctx: commands.Context, user: discord.Member = None):
    try:
        with open("monsterrr_state.json", "r", encoding="utf-8") as f:
            state = __import__("json").load(f)
    except Exception:
        state = {}
    tasks = state.get("tasks", {}) if isinstance(state, dict) else {}
    if user:
        user_tasks = tasks.get(str(user.id), [])
        msg = f"Tasks for {user.mention}:\n" + "\n".join(user_tasks) if user_tasks else f"No tasks for {user.mention}."
    else:
        if not tasks:
            msg = "No tasks found."
        else:
            msg = "All Tasks:\n" + "\n".join([f"{k}: {', '.join(v)}" for k, v in tasks.items()])
    await ctx.send(msg)

@bot.command(name="analytics")
async def analytics_cmd(ctx: commands.Context):
    try:
        with open("monsterrr_state.json", "r", encoding="utf-8") as f:
            state = __import__("json").load(f)
    except Exception:
        state = {}
    analytics = state.get("analytics", {}) if isinstance(state, dict) else {}
    if not analytics:
        await ctx.send("No analytics data found.")
        return
    await ctx.send("Analytics Dashboard:\n" + __import__("json").dumps(analytics, indent=2))

@bot.command(name="scan")
async def scan_cmd(ctx: commands.Context, repo: str):
    findings = []
    try:
        findings = security_service.scan_repo(repo)
    except Exception as e:
        logger.exception("scan error: %s", e)
        await ctx.send(f"Security scan failed: {e}")
        return
    if findings:
        await ctx.send("Security findings:\n" + "\n".join(findings))
    else:
        await ctx.send("No security issues found.")

@bot.command(name="review")
async def review_cmd(ctx: commands.Context, pr: str):
    try:
        review = qa_service.review_pr(pr)
    except Exception as e:
        logger.exception("review error: %s", e)
        await ctx.send(f"Review failed: {e}")
        return
    await ctx.send(f"Code review for PR {pr}:\n{review}")

@bot.command(name="docs")
async def docs_cmd(ctx: commands.Context, repo: str):
    try:
        result = doc_service.update_docs(repo)
    except Exception as e:
        logger.exception("docs error: %s", e)
        await ctx.send(f"Docs update failed: {e}")
        return
    await ctx.send(f"Documentation update for {repo}:\n{result}")

@bot.command(name="integrate")
async def integrate_cmd(ctx: commands.Context, platform_name: str):
    try:
        result = integration_service.integrate(platform_name)
    except Exception as e:
        logger.exception("integrate error: %s", e)
        await ctx.send(f"Integration failed: {e}")
        return
    await ctx.send(f"Integration with {platform_name}:\n{result}")

@bot.command(name="qa")
async def qa_cmd(ctx: commands.Context, time: str):
    try:
        result = qa_service.schedule_qa(time)
    except Exception as e:
        logger.exception("qa error: %s", e)
        await ctx.send(f"Q&A scheduling failed: {e}")
        return
    await ctx.send(f"Q&A session scheduled at {time}:\n{result}")

@bot.command(name="close")
async def close_cmd(ctx: commands.Context, issue: str):
    try:
        result = github_service.close_issue(issue)
    except Exception as e:
        logger.exception("close error: %s", e)
        await ctx.send(f"Failed to close issue: {e}")
        return
    await ctx.send(f"Issue {issue} closed: {result}")

@bot.command(name="assign")
async def assign_cmd(ctx: commands.Context, user: discord.Member, *, task: str):
    task_manager.assign_task(str(user), task)
    await ctx.send(f"Task assigned to {user.mention}: {task}")

# ---------------------------
# Command error handling
# ---------------------------
@bot.event
async def on_command_error(ctx: commands.Context, error: Exception):
    if isinstance(error, commands.CommandNotFound):
        name = ctx.message.content.lstrip().split()[0].lstrip(bot.command_prefix)
        if name in custom_commands:
            await ctx.send(f"Custom command `{name}`: {custom_commands[name]}")
            return
        await ctx.send("Unknown command. Type `!help` for usage.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Missing argument: {error.param.name}")
    else:
        logger.exception("Command error: %s", error)
        try:
            await ctx.send(f"Command error: {error}")
        except Exception:
            pass

# ---------------------------
# Compatibility shim for external runner
# ---------------------------
class settings:
    DISCORD_BOT_TOKEN = DISCORD_TOKEN
    GROQ_API_KEY = GROQ_API_KEY
    DISCORD_GUILD_ID = GUILD_ID
    DISCORD_CHANNEL_ID = CHANNEL_ID

# Exports for discord_bot_runner
__all__ = ["bot", "client", "groq_service", "settings"]

# End of file
