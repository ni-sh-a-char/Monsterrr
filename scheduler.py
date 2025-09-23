# Background monitoring tasks
import asyncio
from datetime import datetime
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
        # Ensure we have the latest organization stats
        try:
            org_stats = github.get_organization_stats()
            logger.info(f"[Scheduler] Organization stats: {org_stats.get('total_repos', 0)} repos, {org_stats.get('members', 0)} members")
            
            # Update state with organization stats
            state_path = "monsterrr_state.json"
            state = {}
            if os.path.exists(state_path):
                with open(state_path, "r", encoding="utf-8") as f:
                    try:
                        state = json.load(f)
                    except Exception:
                        state = {}
            
            state["organization_stats"] = org_stats
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"[Scheduler] Error getting organization stats: {e}")
        
        # Plan 3 contributions and execute them (not dry-run)
        logger.info("[Scheduler] Planning daily contributions...")
        plan = maintainer_agent.plan_daily_contributions(num_contributions=3)
        
        if plan:
            logger.info(f"[Scheduler] Executing {len(plan)} planned contributions...")
            maintainer_agent.execute_daily_plan(plan, creator_agent=creator_agent, dry_run=False)
            
            # Log successful execution
            state_path = "monsterrr_state.json"
            if os.path.exists(state_path):
                with open(state_path, "r", encoding="utf-8") as f:
                    try:
                        state = json.load(f)
                    except Exception:
                        state = {}
                
                actions = state.get("actions", [])
                actions.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "daily_plan_executed",
                    "details": {
                        "contributions_count": len(plan),
                        "plan": plan
                    }
                })
                state["actions"] = actions
                
                with open(state_path, "w", encoding="utf-8") as f:
                    json.dump(state, f, indent=2)
        else:
            logger.warning("[Scheduler] No contributions planned. Creating a default repository...")
            # If no plan was generated, create a default repository
            default_idea = {
                "name": f"monsterrr-project-{datetime.utcnow().strftime('%Y%m%d-%H%M')}",
                "description": "Auto-generated project by Monsterrr autonomous agent",
                "tech_stack": ["Python", "FastAPI"],
                "roadmap": ["Initialize project structure", "Add basic API endpoints", "Implement tests"]
            }
            creator_agent.create_or_improve_repository(default_idea)
            
            # Log this action
            state_path = "monsterrr_state.json"
            if os.path.exists(state_path):
                with open(state_path, "r", encoding="utf-8") as f:
                    try:
                        state = json.load(f)
                    except Exception:
                        state = {}
                
                actions = state.get("actions", [])
                actions.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "default_repo_created",
                    "details": {
                        "repo_name": default_idea["name"]
                    }
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
        <b>Organization:</b> {settings.GITHUB_ORG}
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

Organization: {settings.GITHUB_ORG}

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
    
    # Keep the scheduler running indefinitely
    try:
        while True:
            await asyncio.sleep(3600)  # Check every hour
    except (KeyboardInterrupt, SystemExit):
        pass

def quick_check():
    """Quick check to ensure Monsterrr is active and performing work."""
    logger.info("[Scheduler] Quick check - ensuring Monsterrr activity")
    
    try:
        # Check if we have any repositories
        repos = github.list_repositories()
        logger.info(f"[Scheduler] Quick check found {len(repos)} repositories")
        
        # If no repositories, create one
        if len(repos) == 0:
            logger.info("[Scheduler] No repositories found. Creating initial repository...")
            default_idea = {
                "name": f"monsterrr-starter-{datetime.utcnow().strftime('%Y%m%d-%H%M')}",
                "description": "Starter repository created by Monsterrr",
                "tech_stack": ["Python"],
                "roadmap": ["Initialize project", "Add basic structure"]
            }
            creator_agent.create_or_improve_repository(default_idea)
            
            # Log this action
            state_path = "monsterrr_state.json"
            if os.path.exists(state_path):
                with open(state_path, "r", encoding="utf-8") as f:
                    try:
                        state = json.load(f)
                    except Exception:
                        state = {}
                
                actions = state.get("actions", [])
                actions.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "starter_repo_created",
                    "details": {
                        "repo_name": default_idea["name"]
                    }
                })
                state["actions"] = actions
                
                with open(state_path, "w", encoding="utf-8") as f:
                    json.dump(state, f, indent=2)
                    
    except Exception as e:
        logger.error(f"[Scheduler] Error in quick check: {e}")

if __name__ == "__main__":
    asyncio.run(start_scheduler())