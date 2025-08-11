"""
Production scheduler for Monsterrr: daily jobs, status report email, robust logging, and one-time startup email.
"""

import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from utils.config import Settings
from utils.logger import setup_logger
import traceback
from agents.idea_agent import IdeaGeneratorAgent
from agents.creator_agent import CreatorAgent
from agents.maintainer_agent import MaintainerAgent
from services.groq_service import GroqService
from services.github_service import GitHubService
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import json
import os

settings = Settings()
logger = setup_logger()
groq = GroqService(api_key=settings.GROQ_API_KEY, logger=logger)
github = GitHubService(logger=logger)
idea_agent = IdeaGeneratorAgent(groq, logger)
creator_agent = CreatorAgent(github, logger)
maintainer_agent = MaintainerAgent(github, groq, logger)

scheduler = AsyncIOScheduler()

def daily_job():
    logger.info("[Scheduler] Running daily job: Idea + Creator + Maintainer agents + status report.")
    ideas = idea_agent.fetch_and_rank_ideas()
    if ideas:
        creator_agent.create_repository(ideas[0])
    maintainer_agent.perform_maintenance()
    send_status_report()

def send_status_report():
    logger.info("[Scheduler] Sending daily status report email.")
    state = {}
    if os.path.exists("monsterrr_state.json"):
        with open("monsterrr_state.json", "r", encoding="utf-8") as f:
            state = json.load(f)
        subject = "[Monsterrr] Daily Executive Status Report"
        html = f"""
<div style='font-family:Segoe UI,Arial,sans-serif;max-width:600px;margin:0 auto;background:#f9f9fb;padding:32px 24px;border-radius:12px;border:1px solid #e3e7ee;'>
    <h1 style='color:#2d7ff9;margin-bottom:0.2em;'>Monsterrr Daily Executive Report</h1>
    <p style='font-size:1.1em;color:#333;margin-top:0;'>
        <b>Date:</b> {__import__('datetime').datetime.utcnow().strftime('%A, %d %B %Y')}<br>
        <b>Organization:</b> {settings.GITHUB_ORG}
    </p>
    <hr style='border:0;border-top:1px solid #e3e7ee;margin:18px 0;'>
    <h2 style='color:#222;font-size:1.15em;margin-bottom:0.5em;'>Key Metrics</h2>
    <ul style='line-height:1.7;font-size:1.05em;'>
        <li><b>New repositories created:</b> {len(state.get('repos', []))}</li>
        <li><b>Issues opened:</b> {state.get('issues_opened', 0)} | <b>Issues closed:</b> {state.get('issues_closed', 0)}</li>
        <li><b>Top 3 project ideas:</b> <ul style='margin:0 0 0 1em;padding:0;color:#2d7ff9;'>
            {''.join(f"<li style='margin-bottom:2px;'><b>{i['name']}</b></li>" for i in state.get('ideas', {}).get('top_ideas', [])[:3])}
        </ul></li>
        <li><b>PR activity:</b> {state.get('prs_merged', 0)} merged, {state.get('prs_open', 0)} open</li>
        <li><b>Next actions:</b> <span style='color:#2d7ff9;'>{state.get('next_week', '[Groq-generated plan]')}</span></li>
    </ul>
    <hr style='border:0;border-top:1px solid #e3e7ee;margin:18px 0;'>
    <p style='font-size:0.98em;color:#555;'>
        <b>Monsterrr</b> is your autonomous, always-on GitHub organization manager.<br>
        <i>This report is generated and delivered automatically by Monsterrr AI.</i>
    </p>
</div>
"""
    text = f"""
Monsterrr Daily Status Report

New repositories created: {len(state.get('repos', []))}
Issues opened: {state.get('issues_opened', 0)} | Issues closed: {state.get('issues_closed', 0)}
Top 3 project ideas: {', '.join(i['name'] for i in state.get('ideas', {}).get('top_ideas', [])[:3])}
PR activity: {state.get('prs_merged', 0)} merged, {state.get('prs_open', 0)} open
Next actions: {state.get('next_week', '[Groq-generated plan]')}

--
This is an automated report from Monsterrr.
"""
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = settings.SMTP_USER
    msg['To'] = ", ".join(settings.recipients)
    msg.attach(MIMEText(text, 'plain'))
    msg.attach(MIMEText(html, 'html'))
    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASS)
            server.sendmail(settings.SMTP_USER, settings.recipients, msg.as_string())
        logger.info("[Scheduler] Status report sent.")
    except Exception as e:
        logger.error(f"[Scheduler] Failed to send status report: {e}\n{traceback.format_exc()}")

def send_startup_email():
    logger.info("[Scheduler] Sending one-time startup status email.")
    state = {}
    if os.path.exists("monsterrr_state.json"):
        with open("monsterrr_state.json", "r", encoding="utf-8") as f:
            try:
                state = json.load(f)
            except Exception:
                state = {}
    # Always define subject, html, and text, even if state is empty
    subject = "🚀 Monsterrr is Now Live! | Initial System Status"
    html = f"""
<div style='font-family:Segoe UI,Arial,sans-serif;max-width:600px;margin:0 auto;background:#f9f9fb;padding:32px 24px;border-radius:12px;border:1px solid #e3e7ee;'>
    <h1 style='color:#2d7ff9;margin-bottom:0.2em;'>Monsterrr is Now Live!</h1>
    <p style='font-size:1.1em;color:#333;margin-top:0;'>
        <b>Welcome to your autonomous GitHub organization manager.</b><br>
        <b>Organization:</b> {settings.GITHUB_ORG}
    </p>
    <hr style='border:0;border-top:1px solid #e3e7ee;margin:18px 0;'>
    <h2 style='color:#222;font-size:1.15em;margin-bottom:0.5em;'>Initial System Status</h2>
    <ul style='line-height:1.7;font-size:1.05em;'>
        <li><b>Repositories detected:</b> {len(state.get('repos', []))}</li>
        <li><b>Open issues:</b> {state.get('issues_opened', 0)}</li>
        <li><b>Closed issues:</b> {state.get('issues_closed', 0)}</li>
        <li><b>Top 3 project ideas:</b> <ul style='margin:0 0 0 1em;padding:0;color:#2d7ff9;'>
            {''.join(f"<li style='margin-bottom:2px;'><b>{i['name']}</b></li>" for i in state.get('ideas', {}).get('top_ideas', [])[:3])}
        </ul></li>
        <li><b>PRs merged:</b> {state.get('prs_merged', 0)}, <b>PRs open:</b> {state.get('prs_open', 0)}</li>
    </ul>
    <hr style='border:0;border-top:1px solid #e3e7ee;margin:18px 0;'>
    <p style='font-size:1em;color:#2d7ff9;'><b>Monsterrr is now running and will keep your organization healthy and growing, 24/7.</b></p>
    <p style='font-size:0.95em;color:#888;'>This is a one-time launch notification from Monsterrr.</p>
</div>
"""
    text = f"""
Monsterrr is Now Live!

Repositories detected: {len(state.get('repos', []))}
Open issues: {state.get('issues_opened', 0)}
Closed issues: {state.get('issues_closed', 0)}
Top 3 project ideas: {', '.join(i['name'] for i in state.get('ideas', {}).get('top_ideas', [])[:3])}
PRs merged: {state.get('prs_merged', 0)}, PRs open: {state.get('prs_open', 0)}

Monsterrr is now running and will keep your organization healthy and growing, 24/7.

--
This is a one-time launch notification from Monsterrr.
"""
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = settings.SMTP_USER
    msg['To'] = ", ".join(settings.recipients)
    msg.attach(MIMEText(text, 'plain'))
    msg.attach(MIMEText(html, 'html'))
    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASS)
            server.sendmail(settings.SMTP_USER, settings.recipients, msg.as_string())
        logger.info("[Scheduler] Startup email sent.")
    except Exception as e:
        logger.error(f"[Scheduler] Failed to send startup email: {e}\n{traceback.format_exc()}")

def smtp_connectivity_check():
    """Check SMTP credentials at startup and log result."""
    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASS)
        logger.info("[Startup] SMTP connectivity check: SUCCESS.")
    except Exception as e:
        logger.error(f"[Startup] SMTP connectivity check FAILED: {e}\n{traceback.format_exc()}")

async def start_scheduler():
    smtp_connectivity_check()
    scheduler.add_job(daily_job, "cron", hour=0)
    scheduler.start()
    logger.info("Scheduler started.")
    # One-time startup email logic (persisted in monsterrr_state.json)
    state_path = "monsterrr_state.json"
    state = {}
    if os.path.exists(state_path):
        with open(state_path, "r", encoding="utf-8") as f:
            try:
                state = json.load(f)
            except Exception:
                state = {}
    if not state.get("startup_email_sent", False):
        send_startup_email()
        state["startup_email_sent"] = True
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        pass

if __name__ == "__main__":
    asyncio.run(start_scheduler())