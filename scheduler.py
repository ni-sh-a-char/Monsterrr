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
    logger.info("[Scheduler] Running daily job: MaintainerAgent plans and executes 3 contributions + status report.")
    # Plan 3 contributions and execute them (not dry-run)
    plan = maintainer_agent.plan_daily_contributions(num_contributions=3)
    maintainer_agent.execute_daily_plan(plan, creator_agent=creator_agent, dry_run=False)
    # After execution, send status report
    send_status_report()

def send_status_report():
    logger.info("[Scheduler] Sending daily status report email.")
    state = {}
    if os.path.exists("monsterrr_state.json"):
        with open("monsterrr_state.json", "r", encoding="utf-8") as f:
            state = json.load(f)
    subject = "[Monsterrr] Daily Executive Status Report"
    today = __import__('datetime').datetime.utcnow().strftime('%A, %d %B %Y')
    # Gather details
    ideas = state.get('ideas', {}).get('top_ideas', [])
    repos = state.get('repos', [])
    issues_opened = state.get('issues_opened', 0)
    issues_closed = state.get('issues_closed', 0)
    prs_merged = state.get('prs_merged', 0)
    prs_open = state.get('prs_open', 0)
    repo_issues = state.get('repo_issues', {})
    actions = state.get('actions', [])
    # Quantifiable daily contributions
    daily_plan_path = f"logs/daily_plan_{today.replace(',', '').replace(' ', '_')}.json"
    contributions = []
    import glob
    # Find today's plan file (by date)
    plan_files = glob.glob("logs/daily_plan_*.json")
    if plan_files:
        # Use the latest file for today
        plan_files.sort(reverse=True)
        try:
            with open(plan_files[0], "r", encoding="utf-8") as pf:
                contributions = json.load(pf)
        except Exception:
            contributions = []
    num_contributions = len(contributions)
    # Compose executive summary
    # Build status report JSON
    report_json = {
        "date": today,
        "organization": settings.GITHUB_ORG,
        "ideas_processed": len(ideas),
        "ideas": ideas,
        "repositories_created": len(repos),
        "repositories": repos,
        "issues_detected_and_actions_taken": sum(len(str(issues)) for issues in repo_issues.values()) if repo_issues else 0,
        "repo_issues": repo_issues,
        "actions": actions,
        "prs_merged": prs_merged,
        "prs_open": prs_open,
        "daily_contributions_planned_executed": num_contributions,
        "contributions": contributions,
        "target_contributions": 3,
        "status": "pending"
    }
    # Save JSON before sending email
    json_path = f"logs/status_report_{today.replace(',', '').replace(' ', '_')}.json"
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    # Only create/replace the JSON if it doesn't exist for today
    if not os.path.exists(json_path):
        with open(json_path, "w", encoding="utf-8") as jf:
            json.dump(report_json, jf, indent=2)
    # Build HTML summary for email with full transparency
    idea_items = "".join([
        f"<li><b>{i['name']}</b>: {i['description']}<br>"
        f"<span style='color:#555;'>Tech: {', '.join(i.get('tech_stack', []) or i.get('techStack', []))} | Difficulty: {i.get('difficulty', 'N/A')} | Est. Dev Time: {i.get('estimated_dev_time', i.get('estimatedDevTime', 'N/A'))} weeks</span></li>"
        for i in ideas
    ]) if ideas else "<li>No ideas proposed today.</li>"

    repo_items = "".join([
        f"<li>{r.get('name', r)}</li>" for r in repos
    ]) if repos else "<li>No repositories created today.</li>"

    def format_contribution(c):
        if c.get('type') == 'repo':
            details = c.get('details', {})
            tech = ', '.join(details.get('techStack', []))
            roadmap = details.get('roadmap', [])
            roadmap_html = '<ul style="margin:4px 0 0 16px;">' + ''.join(f'<li>{step}</li>' for step in roadmap) + '</ul>' if roadmap else ''
            return (
                f"<li><b>Repository:</b> {c.get('name')}<br>"
                f"<span style='color:#555;'>{c.get('description')}<br>Tech Stack: {tech}</span>{roadmap_html}</li>"
            )
        elif c.get('type') == 'branch':
            details = c.get('details', {})
            return (
                f"<li><b>Branch:</b> {c.get('name')} in <b>{c.get('targetRepo')}</b><br>"
                f"<span style='color:#555;'>{c.get('description')}<br>Starter File: {details.get('starterFile', 'N/A')}<br>Change Idea: {details.get('changeIdea', 'N/A')}</span></li>"
            )
        else:
            return f"<li>{str(c)}</li>"

    contribution_items = "".join([format_contribution(c) for c in contributions]) if contributions else "<li>No contributions planned/executed today.</li>"

    action_items = "".join([
        f"<li>{a}</li>" for a in actions
    ]) if actions else "<li>No actions taken today.</li>"

    issues_items = "".join([
        f"<li><b>{repo}</b>: {issues}</li>" for repo, issues in repo_issues.items()
    ]) if repo_issues else "<li>No issues detected today.</li>"

    summary = f"""
<div style='font-family:Segoe UI,Arial,sans-serif;max-width:600px;margin:0 auto;background:#f9f9fb;padding:32px 24px;border-radius:12px;border:1px solid #e3e7ee;'>
    <h1 style='color:#2d7ff9;margin-bottom:0.2em;'>Monsterrr Daily Executive Report</h1>
    <p style='font-size:1.1em;color:#333;margin-top:0;'>
        <b>Date:</b> {today}<br>
        <b>Organization:</b> {settings.GITHUB_ORG}
    </p>
    <hr style='border:0;border-top:1px solid #e3e7ee;margin:18px 0;'>
    <h2 style='color:#222;font-size:1.15em;margin-bottom:0.5em;'>Executive Summary</h2>
    <ul style='line-height:1.7;font-size:1.05em;'>
        <li><b>Ideas processed:</b> {len(ideas)}</li>
        <li><b>Repositories created:</b> {len(repos)}</li>
        <li><b>Issues detected and actions taken:</b> {sum(len(str(issues)) for issues in repo_issues.values()) if repo_issues else 0}</li>
        <li><b>PR activity:</b> {prs_merged} merged, {prs_open} open</li>
        <li><b>Daily contributions planned/executed:</b> {num_contributions} (target: 3)</li>
    </ul>
    <hr style='border:0;border-top:1px solid #e3e7ee;margin:18px 0;'>
    <h3 style='color:#2d7ff9;'>Ideas Proposed</h3>
    <ul>{idea_items}</ul>
    <h3 style='color:#2d7ff9;'>Daily Plan / Contributions</h3>
    <ul>{contribution_items}</ul>
    <h3 style='color:#2d7ff9;'>Repositories Created</h3>
    <ul>{repo_items}</ul>
    <h3 style='color:#2d7ff9;'>Actions Taken</h3>
    <ul>{action_items}</ul>
    <h3 style='color:#2d7ff9;'>Issues Detected</h3>
    <ul>{issues_items}</ul>
    <hr style='border:0;border-top:1px solid #e3e7ee;margin:18px 0;'>
    <p style='font-size:1em;color:#2d7ff9;'><b>Monsterrr</b> is your autonomous, always-on GitHub organization manager.<br><i>This report is generated and delivered automatically by Monsterrr AI.</i></p>
</div>
"""
    # Plain text version
    text = f"""
Monsterrr Daily Status Report

Date: {today}
Organization: {settings.GITHUB_ORG}

Executive Summary:
Today, Monsterrr proactively monitored your organization, processed trending open-source ideas, created new repositories, and maintained existing projects. Below is a detailed account of today's activities:

Ideas processed: {len(ideas)}
{chr(10).join(f"- {i['name']}: {i['description']} [Tech: {', '.join(i.get('tech_stack', []) or i.get('techStack', []))} | Difficulty: {i.get('difficulty', 'N/A')} | Est. Dev Time: {i.get('estimated_dev_time', i.get('estimatedDevTime', 'N/A'))} weeks]" for i in ideas)}

Repositories created: {len(repos)}
{chr(10).join(f"- {r.get('name', r)}" for r in repos)}

Issues detected and actions taken: {sum(len(str(issues)) for issues in repo_issues.values()) if repo_issues else 0}
{chr(10).join(f"- {repo}: {issues}" for repo, issues in repo_issues.items()) if repo_issues else '- No issues detected today.'}
{chr(10).join(f"- {a}" for a in actions)}

PR activity: {prs_merged} merged, {prs_open} open
Daily contributions planned/executed: {num_contributions} (target: 3)

---
This is an automated report from Monsterrr.
"""
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = settings.SMTP_USER
    msg['To'] = ", ".join(settings.recipients)
    msg.attach(MIMEText(text, 'plain'))
    msg.attach(MIMEText(summary, 'html'))
    try:
        logger.info(f"[Scheduler] Email subject: {subject}")
        logger.info(f"[Scheduler] Email recipients: {settings.recipients}")
        logger.info(f"[Scheduler] Email HTML: {summary}")
        logger.info(f"[Scheduler] Email text: {text}")
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASS)
            server.sendmail(settings.SMTP_USER, settings.recipients, msg.as_string())
        logger.info("[Scheduler] Status report sent.")
    # Do NOT replace the JSON after sending email; keep it for the day
    # The JSON will be replaced only when a new day starts and daily_job runs again
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
    # Run daily_job at UTC midnight every day
    scheduler.add_job(daily_job, "cron", hour=0, minute=0)
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