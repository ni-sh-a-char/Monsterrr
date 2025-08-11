"""
Production scheduler for Monsterrr: daily/weekly jobs, status report email, robust logging.
"""

import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from utils.config import Settings
from utils.logger import setup_logger
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
    logger.info("[Scheduler] Running daily job: Idea + Creator agents.")
    ideas = idea_agent.fetch_and_rank_ideas()
    if ideas:
        creator_agent.create_repository(ideas[0])

def weekly_job():
    logger.info("[Scheduler] Running weekly job: Maintainer agent + status report.")
    maintainer_agent.perform_maintenance()
    send_status_report()

def send_status_report():
    logger.info("[Scheduler] Sending weekly status report email.")
    state = {}
    if os.path.exists("monsterrr_state.json"):
        with open("monsterrr_state.json", "r", encoding="utf-8") as f:
            state = json.load(f)
    # Compose report
    subject = "Monsterrr Weekly Status Report"
    html = f"""
    <h2>Monsterrr Weekly Status Report</h2>
    <ul>
      <li>New repositories created: {len(state.get('repos', []))}</li>
      <li>Issues opened: {state.get('issues_opened', 0)} | Issues closed: {state.get('issues_closed', 0)}</li>
      <li>Top 3 project ideas: <ul>{''.join(f'<li>{i['name']}</li>' for i in state.get('ideas', {}).get('top_ideas', [])[:3])}</ul></li>
      <li>PR activity: {state.get('prs_merged', 0)} merged, {state.get('prs_open', 0)} open</li>
      <li>Next week: {state.get('next_week', '[Groq-generated plan]')}</li>
    </ul>
    """
    text = f"""
Monsterrr Weekly Status Report

New repositories created: {len(state.get('repos', []))}
Issues opened: {state.get('issues_opened', 0)} | Issues closed: {state.get('issues_closed', 0)}
Top 3 project ideas: {', '.join(i['name'] for i in state.get('ideas', {}).get('top_ideas', [])[:3])}
PR activity: {state.get('prs_merged', 0)} merged, {state.get('prs_open', 0)} open
Next week: {state.get('next_week', '[Groq-generated plan]')}
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
        logger.error(f"[Scheduler] Failed to send status report: {e}")

def start_scheduler():
    scheduler.add_job(daily_job, "cron", hour=0)
    scheduler.add_job(weekly_job, "cron", day_of_week="mon", hour=1)
    scheduler.start()
    logger.info("Scheduler started.")
    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass

if __name__ == "__main__":
    start_scheduler()