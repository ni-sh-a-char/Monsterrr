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

# Discord bot setup (after all service initializations, before any bot usage)
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
                    # Gather professional status report data
                    status_text = (
                        f"**🤖 Monsterrr System Status**\n"
                        f"Startup time: {STARTUP_TIME.strftime('%Y-%m-%d %H:%M:%S IST')}\n"
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

    # --- Enhanced Natural Language Understanding ---
    # Use LLM to classify intent: command or general query
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
            ("create repo", "create_repository"),
            ("assign task", "assign_task"),
            ("show ideas", "show_ideas"),
            ("status", "show_status"),
            ("add idea", "add_idea"),
            ("merge", "merge_pull_request"),
            # Add more as needed
        ]
        intent = None
        intent_type = 'query'
        for kw, cmd in command_intents:
            if kw in content.lower():
                intent = cmd
                intent_type = 'command'
                break

    prompt_lines = [
        f"SYSTEM: {system_ctx}",
        "IMPORTANT: NEVER use tables, pipes (|), or any table-like formatting in your answers. For all lists or structured data, ALWAYS use bullet points, sub-points, and numbering for clarity.",
        "",
        "CONVERSATION:"]
    for m in conversation_memory[user_id]:
        role = m.get("role", "user")
        prompt_lines.append(f"{role.upper()}: {m.get('content','')}")
    prompt = "\n".join(prompt_lines)

    try:
        async with message.channel.typing():
            import re
            url_pattern = re.compile(r"https?://\S+", re.IGNORECASE)
            found_urls = url_pattern.findall(content)
            # If message is a command, handle as before
            if intent_type == 'command' and intent:
                reply = await handle_natural_command(intent, content, user_id)
                conversation_memory[user_id].append({"role": "assistant", "content": reply})
                try:
                    embed = create_professional_embed("Monsterrr Command Result", reply)
                    await message.channel.send(embed=embed)
                except Exception:
                    await send_long_message(message.channel, reply)
            # If message contains a URL, summarize it using SearchService
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
            # If message is a general query, use SearchService for web search
            elif search_service:
                try:
                    web_answer = await asyncio.to_thread(search_service.search, content)
                except Exception as e:
                    web_answer = None
                if web_answer:
                    answer = web_answer
                else:
                    # fallback to LLM if web search fails
                    ai_reply = await asyncio.to_thread(_call_groq, prompt, GROQ_MODEL)
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

@bot.command(name="status")
async def status_command(ctx):

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
    guild_count = len(bot.guilds)
    member_count = sum(guild.member_count for guild in bot.guilds)
    ideas = state.get("ideas", {}).get("top_ideas", [])
    repos = state.get("repos", [])
    analytics = state.get("analytics", {})
    tasks = state.get("tasks", {})

    # System resource usage
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

    # Recent user activity (last 3 messages)
    recent_users = list(unique_users)[-3:] if unique_users else []
    recent_msgs = []
    for uid in recent_users:
        if uid in conversation_memory:
            recent_msgs.extend([m["content"] for m in conversation_memory[uid] if m.get("role") == "user"])
    recent_msgs = recent_msgs[-3:] if recent_msgs else []

    # Org context
    import os
    github_org = os.getenv("GITHUB_ORG", "unknown")
    # Enforce org restriction: only operate for the configured org
    allowed_org = os.getenv("GITHUB_ORG", "unknown")
    if github_org != allowed_org:
        await ctx.send(f"This bot is restricted to operate only for the organization specified in the .env file. Current org: {github_org}")
        return
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

    # Automation bots
    bots = state.get("automation_bots", {})
    bots_status = []
    for bot_name, bot_info in bots.items():
        bots_status.append(f"• {bot_name} – {bot_info}")

    # Current tasks in the queue
    queue = state.get("queue", [])
    queue_lines = [f"• {task}" for task in queue] if queue else ["• No active tasks in the queue."]

    # Next actions (suggestions)
    next_actions = state.get("next_actions", [
        "Deploy any of the ideas you liked from the previous list.",
        "Provide a deeper dive into any metric (CPU spikes, memory trends, PR throughput).",
        "Execute a specific automation (run the dependency scanner now, create a new repo, etc.)."
    ])

    # Compose professional, detailed status message
    status_lines = [
        f"**Current operational snapshot**",
        f"- Uptime: {uptime} (started at {STARTUP_TIME.strftime('%Y-%m-%d %H:%M:%S IST')})",
        f"- CPU load: {cpu} %",
        f"- Memory usage: {mem_usage}",
        f"- Hostname / IP: {hostname} / {ip}",
        f"- Model in use: {GROQ_MODEL}",
        f"- Managing GitHub organization: {github_org}",
        f"- Recent user activity:"
    ]
    if recent_msgs:
        for msg in recent_msgs:
            status_lines.append(f"    • {msg}")
    else:
        status_lines.append("    • No recent user activity.")
    status_lines.extend([
        f"- Org-wide health indicators:",
        f"    • Repository count: {len(repos)} active repos under the organization '{github_org}'",
        f"    • Pending pull-requests: {pr_count} (average age {pr_age} days)",
        f"    • Open issues: {issue_count} (critical {issue_crit}, high {issue_high}, medium {issue_med}, low {issue_low})",
        f"    • CI pipeline health: {ci_status}; average duration {ci_duration}",
        f"    • Security alerts: {sec_crit} critical, {sec_warn} warnings pending triage",
        f"- Automation bots:",
    ])
    if bots_status:
        status_lines.extend(bots_status)
    else:
        status_lines.append("    • No automation bots configured.")
    status_lines.append("- Current tasks in the queue:")
    status_lines.extend(queue_lines)
    status_lines.append("- What I can do next:")
    for action in next_actions:
        status_lines.append(f"    • {action}")

    # Build embed
    embed = discord.Embed(
        title="� Monsterrr System Status",
        description="\n".join(status_lines),
        color=discord.Color.green()
    )
    embed.set_footer(text=f"Monsterrr • {now_ist.strftime('%Y-%m-%d %H:%M IST')}")
    await ctx.send(embed=embed)


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
            "`!codereview <code>` — AI-powered code review.",
            "`!buildcmd <spec>` — Build a command from a specification.",
            "`!review <pr>` — AI-powered PR review.",
            "`!scan <repo>` — Security scan for a repo.",
            "`!integrate <platform>` — Integrate with other platforms.",
            "`!qa <time>` — Schedule a Q&A session."
        ],
        "🔔 Alerts & Notifications": [
            "`!alerts` — Show real-time alerts.",
            "`!notify <message>` — Send a notification."
        ]
    }

    # Add any additional service commands not already listed
    commands_list["🛠️ Advanced Services"] = [
        "`!commandbuilder <spec>` — Build a command from a specification.",
        "`!codereview <code>` — Review code using the code review service.",
        "`!report <period>` — Generate a report for a given period.",
    ]

    for category, cmds in commands_list.items():
        embed.add_field(name=category, value="\n".join(cmds), inline=False)

    embed.add_field(
        name="🌐 Web Search & Natural Language",
        value="You can use `!search <query or url>` or just ask a question or paste a URL in chat. Monsterrr will search the web and summarize results like ChatGPT.",
        inline=False
    )
    embed.set_footer(text="✨ Powered by Monsterrr — All services are now available as commands.")

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
        # Ensure github_service is initialized
        global github_service
        if 'github_service' not in globals() or github_service is None:
            from .github_service import GitHubService
            github_service = GitHubService(logger=logger)
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


# ---------------------------
# !search command implementation
# ---------------------------
@bot.command(name="search")
async def search_cmd(ctx: commands.Context, *, query: str = None):
    """Search the web and summarize results using SearchService."""
    if not query:
        await ctx.send("Please provide a search query or URL. Usage: `!search <query or url>`")
        return
    if search_service is None:
        await ctx.send("Search service is not available. Please contact the administrator.")
        return
    try:
        async with ctx.typing():
            # SearchService may be sync or async; try both
            import inspect
            # Use the correct method: search_and_summarize
            if inspect.iscoroutinefunction(getattr(search_service, "search_and_summarize", None)):
                result = await search_service.search_and_summarize(query)
            else:
                result = await asyncio.to_thread(search_service.search_and_summarize, query)
            if not result:
                await ctx.send("No results found or failed to summarize.")
                return
            # Try to send as embed if possible
            try:
                embed = discord.Embed(title=f"🔎 Web Search: {query}", description=result, color=discord.Color.blue())
                embed.set_footer(text="Monsterrr Web Search")
                await ctx.send(embed=embed)
            except Exception:
                await ctx.send(result)
    except Exception as e:
        logger.exception("search command error: %s", e)
        await ctx.send(f"Search failed: {e}")

# End of file
# --- Additional Service Commands: Full Coverage (after all other @bot.command) ---
try:
    from .alert_service import AlertService
    alert_service = AlertService()
    @bot.command(name="alerts")
    async def alerts_cmd(ctx: commands.Context):
        try:
            alerts = alert_service.get_alerts() if hasattr(alert_service, "get_alerts") else "No alert method."
            await ctx.send(f"Current alerts:\n{alerts}")
        except Exception as e:
            await ctx.send(f"Failed to fetch alerts: {e}")
except Exception:
    pass

try:
    from .notification_service import NotificationService
    notification_service = NotificationService()
    @bot.command(name="notify")
    async def notify_cmd(ctx: commands.Context, *, message: str):
        try:
            result = notification_service.send_notification(message) if hasattr(notification_service, "send_notification") else "No send_notification method."
            await ctx.send(f"Notification sent: {result}")
        except Exception as e:
            await ctx.send(f"Failed to send notification: {e}")
except Exception:
    pass

try:
    from .code_review_service import CodeReviewService
    code_review_service = CodeReviewService()
    @bot.command(name="codereview")
    async def codereview_cmd(ctx: commands.Context, *, code: str):
        try:
            review = code_review_service.review_code(code) if hasattr(code_review_service, "review_code") else "No review_code method."
            await ctx.send(f"Code review:\n{review}")
        except Exception as e:
            await ctx.send(f"Failed to review code: {e}")
except Exception:
    pass

try:
    from .command_builder import CommandBuilder
    command_builder = CommandBuilder()
    @bot.command(name="buildcmd")
    async def buildcmd_cmd(ctx: commands.Context, *, spec: str):
        try:
            cmd = command_builder.build_command(spec) if hasattr(command_builder, "build_command") else "No build_command method."
            await ctx.send(f"Built command: {cmd}")
        except Exception as e:
            await ctx.send(f"Failed to build command: {e}")
except Exception:
    pass

# Onboarding Service
try:
    @bot.command(name="onboard")
    async def onboard_cmd(ctx: commands.Context, user: discord.Member):
        try:
            result = onboarding_service.onboard(user.name) if hasattr(onboarding_service, "onboard") else "No onboard method."
            await ctx.send(f"Onboarding result: {result}")
        except Exception as e:
            await ctx.send(f"Failed to onboard: {e}")
except Exception:
    pass

# Merge Service
try:
    @bot.command(name="merge")
    async def merge_cmd(ctx: commands.Context, pr: str):
        try:
            result = merge_service.merge(pr) if hasattr(merge_service, "merge") else "No merge method."
            await ctx.send(f"Merge result: {result}")
        except Exception as e:
            await ctx.send(f"Failed to merge: {e}")
except Exception:
    pass

# Language Service
try:
    @bot.command(name="language")
    async def language_cmd(ctx: commands.Context, lang: str, *, text: str):
        try:
            result = language_service.translate(lang, text) if hasattr(language_service, "translate") else "No translate method."
            await ctx.send(f"Translation: {result}")
        except Exception as e:
            await ctx.send(f"Failed to translate: {e}")
except Exception:
    pass

# Triage Service
try:
    @bot.command(name="triage")
    async def triage_cmd(ctx: commands.Context, item_type: str, item: str):
        try:
            result = triage_service.triage(item_type, item) if hasattr(triage_service, "triage") else "No triage method."
            await ctx.send(f"Triage result: {result}")
        except Exception as e:
            await ctx.send(f"Failed to triage: {e}")
except Exception:
    pass

# Poll Service
try:
    @bot.command(name="poll")
    async def poll_cmd(ctx: commands.Context, *, question: str):
        try:
            result = poll_service.create_poll(question) if hasattr(poll_service, "create_poll") else "No create_poll method."
            await ctx.send(f"Poll created: {result}")
        except Exception as e:
            await ctx.send(f"Failed to create poll: {e}")
except Exception:
    pass

# Report Service
try:
    @bot.command(name="report")
    async def report_cmd(ctx: commands.Context, period: str = "daily"):
        try:
            result = report_service.generate_report(period) if hasattr(report_service, "generate_report") else "No generate_report method."
            await ctx.send(f"Report: {result}")
        except Exception as e:
            await ctx.send(f"Failed to generate report: {e}")
except Exception:
    pass

# Recognition Service
try:
    @bot.command(name="recognize")
    async def recognize_cmd(ctx: commands.Context, user: discord.Member):
        try:
            result = recognition_service.recognize(user.name) if hasattr(recognition_service, "recognize") else "No recognize method."
            await ctx.send(f"Recognition: {result}")
        except Exception as e:
            await ctx.send(f"Failed to recognize: {e}")
except Exception:
    pass