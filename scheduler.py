"""
Scheduler for Monsterrr's daily operations.
"""

import asyncio
import os
import json
import traceback
from datetime import datetime, timedelta
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
github.groq_client = groq  # Pass Groq client to GitHub service for use in issue analysis
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
    """Enhanced daily job that ensures actual work is performed."""
    logger.info("[Scheduler] Running enhanced daily job: MaintainerAgent plans and executes 3 contributions + status report.")
    
    try:
        # Generate new ideas
        logger.info("[Scheduler] Generating new ideas...")
        ideas = idea_agent.generate_ideas(count=5)
        logger.info(f"[Scheduler] Generated {len(ideas)} ideas.")
        
        # Plan daily contributions
        logger.info("[Scheduler] Planning daily contributions...")
        plan = maintainer_agent.plan_daily_contributions(ideas)
        logger.info(f"[Scheduler] Planned {len(plan)} contributions.")
        
        # Execute the plan
        logger.info("[Scheduler] Executing daily plan...")
        results = maintainer_agent.execute_plan(plan)
        logger.info(f"[Scheduler] Executed {len(results)} contributions.")
        
        # Update state file with actions
        state_path = "monsterrr_state.json"
        state = {}
        if os.path.exists(state_path):
            with open(state_path, "r", encoding="utf-8") as f:
                try:
                    state = json.load(f)
                except Exception:
                    state = {}
        
        # Add actions to state
        actions = state.get("actions", [])
        for result in results:
            actions.append({
                "timestamp": datetime.utcnow().isoformat(),
                "type": "contribution_executed",
                "details": result
            })
        state["actions"] = actions
        
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        
        # Perform maintenance tasks
        logger.info("[Scheduler] Performing maintenance tasks...")
        maintainer_agent.perform_maintenance()
        
        # After execution, send status report
        send_status_report()
        
    except Exception as e:
        logger.error(f"[Scheduler] Error in daily job: {e}\n{traceback.format_exc()}")

def send_status_report():
    """Send daily status report only once per day."""
    logger.info("[Scheduler] Checking if daily status report should be sent.")
    try:
        state_path = "monsterrr_state.json"
        flag_key = "scheduler_daily_report_sent"
        date_key = "scheduler_daily_report_date"
        
        # Load current state
        state = {}
        if os.path.exists(state_path):
            with open(state_path, "r", encoding="utf-8") as f:
                try:
                    state = json.load(f)
                except Exception:
                    state = {}
        
        # Check if daily report has already been sent today
        from datetime import datetime
        today = datetime.utcnow().strftime('%Y-%m-%d')
        last_sent_date = state.get(date_key, "")
        
        if last_sent_date == today:
            logger.info(f"[Scheduler] Daily status report already sent today ({today}), skipping.")
            return
        
        # Generate comprehensive report
        report = reporting_service.generate_comprehensive_report()
        
        # Send email report if configured
        if settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASS and settings.STATUS_REPORT_RECIPIENTS:
            recipients = settings.recipients
            success = reporting_service.send_email_report(recipients, report)
            if success:
                logger.info("[Scheduler] Email status report sent successfully.")
                
                # Update state to mark daily report as sent today
                try:
                    state[flag_key] = True
                    state[date_key] = today
                    with open(state_path, "w", encoding="utf-8") as f:
                        json.dump(state, f, indent=2)
                    logger.info(f"[Scheduler] Daily status report state updated for {today}.")
                except Exception as e:
                    logger.error(f"[Scheduler] Failed to update state file after sending daily report: {e}")
            else:
                logger.error("[Scheduler] Failed to send email status report.")
        else:
            logger.warning("[Scheduler] Email configuration incomplete. Skipping email report.")
            # Log what's missing
            missing = []
            if not settings.SMTP_HOST:
                missing.append("SMTP_HOST")
            if not settings.SMTP_USER:
                missing.append("SMTP_USER")
            if not settings.SMTP_PASS:
                missing.append("SMTP_PASS")
            if not settings.STATUS_REPORT_RECIPIENTS:
                missing.append("STATUS_REPORT_RECIPIENTS")
            logger.info(f"[Scheduler] Missing configuration: {', '.join(missing)}")
        
        # Update state file with report data
        state["last_report"] = report
        state["last_report_time"] = datetime.utcnow().isoformat()
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
            
    except Exception as e:
        logger.error(f"[Scheduler] Failed to send status report: {e}\n{traceback.format_exc()}")

def send_startup_email():
    logger.info("[Scheduler] Sending one-time startup status email.")
    
    # Check if SMTP is configured
    if not settings.SMTP_HOST or not settings.SMTP_USER or not settings.SMTP_PASS:
        logger.warning("[Scheduler] SMTP not configured. Skipping startup email.")
        return
        
    state = {}
    if os.path.exists("monsterrr_state.json"):
        with open("monsterrr_state.json", "r", encoding="utf-8") as f:
            try:
                state = json.load(f)
            except Exception:
                state = {}
    
    # Get organization stats to include in the report
    try:
        org_stats = github.get_organization_stats()
        # Update state with organization stats
        state["organization_stats"] = org_stats
        with open("monsterrr_state.json", "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.error(f"[Scheduler] Failed to get organization stats: {e}")
        org_stats = {}
    
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
        <b>Organization:</b> {settings.GITHUB_ORG or 'Not configured'}
    </p>
    <hr style='border:0;border-top:1px solid #e3e7ee;margin:18px 0;'>
    <h2 style='color:#222;font-size:1.15em;margin-bottom:0.5em;'>Initial System Status</h2>
    <ul style='line-height:1.7;font-size:1.05em;'>
        <li><b>Repositories detected:</b> {summary.get('repositories', 0)}</li>
        <li><b>Organization members:</b> {org_stats.get('members', 0) if org_stats else 0}</li>
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

Organization: {settings.GITHUB_ORG or 'Not configured'}

Initial System Status:
Repositories detected: {summary.get('repositories', 0)}
Organization members: {org_stats.get('members', 0) if org_stats else 0}
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
    msg['To'] = ", ".join(settings.recipients) if settings.recipients else settings.SMTP_USER
    msg.attach(MIMEText(text, 'plain'))
    msg.attach(MIMEText(html, 'html'))
    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT or 587) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASS)
            server.sendmail(settings.SMTP_USER, settings.recipients if settings.recipients else [settings.SMTP_USER], msg.as_string())
        logger.info("[Scheduler] Startup email sent.")
    except Exception as e:
        logger.error(f"[Scheduler] Failed to send startup email: {e}\n{traceback.format_exc()}")

def smtp_connectivity_check():
    """Check SMTP credentials at startup and log result."""
    if not settings.SMTP_HOST or not settings.SMTP_USER or not settings.SMTP_PASS:
        logger.warning("[Startup] SMTP configuration incomplete. Email reports will be disabled.")
        return
        
    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASS)
        logger.info("[Startup] SMTP connectivity check: SUCCESS.")
    except Exception as e:
        logger.error(f"[Startup] SMTP connectivity check FAILED: {e}\n{traceback.format_exc()}")

async def start_scheduler():
    smtp_connectivity_check()
    # Run daily_job more frequently - every 6 hours instead of daily
    scheduler.add_job(daily_job, "interval", hours=6)
    
    # Also add a quick check job that runs every hour to ensure activity
    scheduler.add_job(quick_check, "interval", minutes=60)
    
    if not getattr(scheduler, 'running', False):
        scheduler.start()
        logger.info("Scheduler started with enhanced frequency.")
    else:
        logger.info("Scheduler already running. Skipping start().")
    
    # One-time startup email logic (persisted in monsterrr_state.json)
    state_path = "monsterrr_state.json"
    state = {}
    
    # Check if state file exists and is valid
    if os.path.exists(state_path):
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:  # Check if file is not empty
                    state = json.loads(content)
                else:
                    logger.warning("[Scheduler] State file is empty, creating new state.")
                    state = {}
        except json.JSONDecodeError as e:
            logger.error(f"[Scheduler] State file is corrupted: {e}. Creating new state.")
            state = {}
        except Exception as e:
            logger.error(f"[Scheduler] Error reading state file: {e}. Creating new state.")
            state = {}
    else:
        logger.info("[Scheduler] No existing state file found.")
    
    # Check if startup email has already been sent
    if not state.get("startup_email_sent", False):
        logger.info("[Scheduler] Sending startup email for the first time.")
        send_startup_email()
        state["startup_email_sent"] = True
        state["initial_startup_time"] = datetime.utcnow().isoformat()
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(state_path) if os.path.dirname(state_path) else ".", exist_ok=True)
        
        try:
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, default=str)
            logger.info("[Scheduler] Startup email status saved to state file.")
        except Exception as e:
            logger.error(f"[Scheduler] Failed to save startup email status: {e}")
    else:
        startup_time = state.get("initial_startup_time", "Unknown")
        logger.info(f"[Scheduler] Startup email already sent. Initial startup time: {startup_time}")
    
    # Send a daily report immediately to verify email functionality (but only if not already sent today)
    logger.info("[Scheduler] Checking if initial status report should be sent to verify email functionality.")
    send_status_report()
    
    # Keep the scheduler running indefinitely
    try:
        while True:
            await asyncio.sleep(3600)  # Check every hour
    except (KeyboardInterrupt, SystemExit):
        pass

def quick_check():
    """Quick check to ensure the system is still running."""
    logger.info("[Scheduler] Quick system health check.")
    try:
        # Simple health check - try to get organization stats
        org_stats = github.get_organization_stats()
        logger.info(f"[Scheduler] Quick check successful. Organization has {org_stats.get('members', 0)} members.")
    except Exception as e:
        logger.error(f"[Scheduler] Quick check failed: {e}")