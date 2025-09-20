# Background monitoring tasks
import asyncio
from services.github_service import GitHubService
from utils.logger import setup_logger
github = GitHubService(logger=setup_logger())

async def monitor_org_health():
    while True:
        # Check for stale issues
        stale_issues = github.find_stale_issues()
        for issue in stale_issues:
            github.close_issue(issue['repo'], issue['number'])
            github.comment_on_issue(issue['repo'], issue['number'], "Closed due to inactivity.")
        # Check for safe PRs to auto-merge
        safe_prs = github.find_safe_prs()
        for pr in safe_prs:
            github.merge_pr(pr['repo'], pr['number'])
            github.comment_on_pr(pr['repo'], pr['number'], "Auto-merged by Monsterrr.")
        # Check for repo activity and security
        github.audit_repos()
        await asyncio.sleep(3600)  # Run every hour

def start_background_monitoring():
    loop = asyncio.get_event_loop()
    loop.create_task(monitor_org_health())
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
from services.reporting_service import ReportingService
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

# Initialize reporting service
reporting_service = ReportingService(
    smtp_host=settings.SMTP_HOST,
    smtp_port=settings.SMTP_PORT,
    smtp_user=settings.SMTP_USER,
    smtp_pass=settings.SMTP_PASS,
    logger=logger
)

scheduler = AsyncIOScheduler()

def daily_job():
    logger.info("[Scheduler] Running daily job: MaintainerAgent plans and executes 3 contributions + status report.")
    # Plan 3 contributions and execute them (not dry-run)
    plan = maintainer_agent.plan_daily_contributions(num_contributions=3)
    maintainer_agent.execute_daily_plan(plan, creator_agent=creator_agent, dry_run=False)
    # After execution, send status report
    send_status_report()

def send_status_report():
    logger.info("[Scheduler] Sending daily status report.")
    try:
        # Generate comprehensive report
        report = reporting_service.generate_comprehensive_report()
        
        # Send email report if configured
        if settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASS and settings.STATUS_REPORT_RECIPIENTS:
            recipients = settings.recipients
            reporting_service.send_email_report(recipients, report)
            logger.info("[Scheduler] Email status report sent.")
        
        # Update state file with report data
        state_path = "monsterrr_state.json"
        state = {}
        if os.path.exists(state_path):
            with open(state_path, "r", encoding="utf-8") as f:
                try:
                    state = json.load(f)
                except Exception:
                    state = {}
        
        state["last_report"] = report
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
            
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
    
    # Generate comprehensive report for startup email
    report = reporting_service.generate_comprehensive_report()
    summary = report.get("summary", {})
    
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
        <li><b>Repositories detected:</b> {summary.get('repositories', 0)}</li>
        <li><b>Ideas generated:</b> {summary.get('ideas', 0)}</li>
        <li><b>Actions performed:</b> {summary.get('actions', 0)}</li>
        <li><b>Branches created:</b> {summary.get('branches', 0)}</li>
    </ul>
    <hr style='border:0;border-top:1px solid #e3e7ee;margin:18px 0;'>
    <p style='font-size:1em;color:#2d7ff9;'><b>Monsterrr is now running and will keep your organization healthy and growing, 24/7.</b></p>
    <p style='font-size:0.95em;color:#888;'>This is a one-time launch notification from Monsterrr.</p>
</div>
"""
    text = f"""
Monsterrr is Now Live!

Organization: {settings.GITHUB_ORG}

Initial System Status:
Repositories detected: {summary.get('repositories', 0)}
Ideas generated: {summary.get('ideas', 0)}
Actions performed: {summary.get('actions', 0)}
Branches created: {summary.get('branches', 0)}

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
    # Run daily_job at UTC midnight every day
    scheduler.add_job(daily_job, "cron", hour=0, minute=0)
    if not getattr(scheduler, 'running', False):
        scheduler.start()
        logger.info("Scheduler started.")
    else:
        logger.info("Scheduler already running. Skipping start().")
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
    # Keep the scheduler running indefinitely
    try:
        while True:
            await asyncio.sleep(3600)  # Check every hour
    except (KeyboardInterrupt, SystemExit):
        pass

if __name__ == "__main__":
    asyncio.run(start_scheduler())