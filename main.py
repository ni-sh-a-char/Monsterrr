import sys
from fastapi import Request
import requests
import threading
import time
# All FastAPI endpoints must be defined after app initialization
"""
FastAPI webhook server entrypoint for Monsterrr.
"""



from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import logging

import os
import json
import asyncio
from dotenv import load_dotenv
load_dotenv()
from utils.config import Settings
from utils.logger import setup_logger
from agents.idea_agent import IdeaGeneratorAgent
from agents.creator_agent import CreatorAgent
from agents.maintainer_agent import MaintainerAgent
from services.groq_service import GroqService
from services.github_service import GitHubService
from scheduler import start_scheduler

app = FastAPI(title="Monsterrr API", description="Autonomous GitHub org manager.")

# Keep-alive mechanism DISABLED - External monitoring via Pulsetic
# def keep_alive():
#     """Ping the service periodically to keep it alive on Render"""
#     PORT = os.environ.get("PORT", 8000)
#     while True:
#         try:
#             requests.get(f"http://localhost:{PORT}/health")
#             time.sleep(600)  # Ping every 10 minutes
#         except Exception as e:
#             print(f"Keep-alive ping failed: {e}")
#             time.sleep(600)  # Continue pinging even if one fails

def start_discord_bot():
    from services.discord_bot import bot
    import os
    token = os.getenv("DISCORD_BOT_TOKEN")
    if token:
        bot.run(token)
    else:
        print("DISCORD_BOT_TOKEN not set!")

# Unified FastAPI startup event: launches scheduler, watchdog, startup email, and Discord bot
@app.on_event("startup")
async def launch_services():
    loop = asyncio.get_event_loop()
    loop.create_task(start_scheduler())
    start_watchdog()
    # Keep-alive mechanism DISABLED - External monitoring via Pulsetic
    # Start Discord bot in a background thread
    if not hasattr(start_discord_bot, "_started"):
        discord_thread = threading.Thread(target=start_discord_bot, daemon=True)
        discord_thread.start()
        start_discord_bot._started = True
settings = Settings()
logger = setup_logger()
try:
    settings.validate()
except Exception as e:
    logger.error(f"[Config] {e}")
    raise
groq = GroqService(api_key=settings.GROQ_API_KEY, logger=logger)
github = GitHubService(logger=logger)
github.groq_client = groq  # Pass Groq client to GitHub service for use in issue analysis
try:
    github.validate_credentials()
except Exception as e:
    logger.error(f"[GitHubService] {e}")
    raise
idea_agent = IdeaGeneratorAgent(groq, logger)
creator_agent = CreatorAgent(github, logger)
maintainer_agent = MaintainerAgent(github, groq, logger)

class IdeaRequest(BaseModel):
    top_n: int = 3

@app.get("/")
async def root():
    return {"message": "Monsterrr AI is running."}


import threading
import time

@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": time.time()}

@app.get("/healthz")
async def healthz():
    """Health check endpoint for Render"""
    return {"status": "healthy", "timestamp": time.time()}

def watchdog():
    while True:
        time.sleep(60)
        # Check health, restart if needed
        try:
            PORT = os.environ.get("PORT", 8000)
            r = requests.get(f"http://localhost:{PORT}/health")
            if r.status_code != 200:
                logger.error("Health check failed, restarting...")
                os.execv(sys.executable, ['python'] + sys.argv)
        except Exception as e:
            logger.error(f"Watchdog error: {e}")
            os.execv(sys.executable, ['python'] + sys.argv)

def start_watchdog():
    t = threading.Thread(target=watchdog, daemon=True)
    t.start()

@app.on_event("startup")
async def launch_scheduler():
    loop = asyncio.get_event_loop()
    loop.create_task(start_scheduler())
    start_watchdog()
    # Startup email is now sent only by the scheduler, not here

# Start Discord bot in a background thread when FastAPI launches



# Manual trigger for idea agent
@app.post("/trigger/idea-agent")
async def trigger_idea_agent():
    ideas = idea_agent.fetch_and_rank_ideas(top_n=3)
    return {"ideas": ideas}

@app.get("/status")
async def status():
    """Get current Monsterrr state file."""
    if os.path.exists("monsterrr_state.json"):
        with open("monsterrr_state.json", "r", encoding="utf-8") as f:
            state = json.load(f)
        return state
    return {"error": "No state file found."}

@app.post("/ideas/generate")
async def generate_ideas(req: IdeaRequest):
    """Trigger idea generation and ranking."""
    ideas = idea_agent.fetch_and_rank_ideas(top_n=req.top_n)
    return {"ideas": ideas}


@app.post("/webhook/github")
async def github_webhook(request: Request):
    payload = await request.json()
    event = request.headers.get("X-GitHub-Event", "unknown")
    repo = payload.get("repository", {}).get("name")
    # Smart event handling
    if event == "issues":
        action = payload.get("action")
        issue = payload.get("issue", {})
        if action == "opened":
            suggestion = groq.groq_llm(f"Suggest a fix for this GitHub issue: {issue.get('title')}")
            github.create_issue(repo, title=f"Automated suggestion for issue #{issue.get('number')}", body=suggestion, labels=["bot-suggestion"])
            logger.info(f"[Webhook] Suggested fix for new issue in {repo}")
        elif action == "closed":
            logger.info(f"[Webhook] Issue closed in {repo}: {issue.get('title')}")
        elif action == "reopened":
            logger.info(f"[Webhook] Issue reopened in {repo}: {issue.get('title')}")
        elif action == "commented":
            comment = payload.get("comment", {})
            reply = groq.groq_llm(f"Reply to this GitHub issue comment: {comment.get('body')}")
            github.comment_on_issue(repo, issue.get('number'), reply)
    elif event == "issue_comment":
        comment = payload.get("comment", {})
        issue = payload.get("issue", {})
        reply = groq.groq_llm(f"Reply to this GitHub issue comment: {comment.get('body')}")
        github.comment_on_issue(repo, issue.get('number'), reply)
    elif event == "pull_request":
        action = payload.get("action")
        pr = payload.get("pull_request", {})
        if action == "opened":
            logger.info(f"[Webhook] New PR opened in {repo}: {pr.get('title')}")
            github.add_labels_to_pr(repo, pr.get('number'), ["needs-review", "AI-checked"])
            review = groq.groq_llm(f"Review this PR: {pr.get('title')}\n{pr.get('body')}")
            github.comment_on_pr(repo, pr.get('number'), review)
        elif action == "closed":
            logger.info(f"[Webhook] PR closed in {repo}: {pr.get('title')}")
        elif action == "reopened":
            logger.info(f"[Webhook] PR reopened in {repo}: {pr.get('title')}")
        elif action == "commented":
            comment = payload.get("comment", {})
            reply = groq.groq_llm(f"Reply to this PR comment: {comment.get('body')}")
            github.comment_on_pr(repo, pr.get('number'), reply)
    elif event == "push":
        logger.info(f"[Webhook] Push event in {repo}")
        github.trigger_code_analysis(repo)
    elif event == "repository":
        action = payload.get("action")
        if action == "created":
            logger.info(f"[Webhook] New repository created: {repo}")
            github.onboard_new_repo(repo)
    elif event == "star":
        user = payload.get("sender", {}).get("login")
        logger.info(f"[Webhook] Repo {repo} starred by {user}")
        github.thank_user_for_star(repo, user)
    elif event == "fork":
        user = payload.get("sender", {}).get("login")
        logger.info(f"[Webhook] Repo {repo} forked by {user}")
        github.thank_user_for_fork(repo, user)


@app.post("/maintenance/run")
async def run_maintenance(background_tasks: BackgroundTasks):
    def _run():
        maintainer_agent.perform_maintenance()
    background_tasks.add_task(_run)
    return {"status": "Maintenance started."}

@app.post("/analyze/repo")
async def analyze_repo(repo_name: str):
    health = github.analyze_repo_health(repo_name)
    return {"repo": repo_name, "health": health}

@app.post("/suggest/issue")
async def suggest_issue_fix(repo: str, issue_number: int):
    issue = github.get_issue(repo, issue_number)
    suggestion = groq.groq_llm(f"Suggest a fix for this GitHub issue: {issue.get('title')}")
    return {"issue": issue.get('title'), "suggestion": suggestion}

@app.post("/trigger/daily-plan")
async def trigger_daily_plan():
    """Trigger the daily planning process."""
    try:
        plan = maintainer_agent.plan_daily_contributions(num_contributions=3)
        return {"status": "success", "plan": plan}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/trigger/execute-plan")
async def trigger_execute_plan():
    """Trigger the execution of the daily plan."""
    try:
        # Get the latest plan
        import glob
        import json
        plan_files = glob.glob("logs/daily_plan_*.json")
        if plan_files:
            plan_files.sort(reverse=True)
            with open(plan_files[0], "r", encoding="utf-8") as f:
                plan = json.load(f)
            
            maintainer_agent.execute_daily_plan(plan, creator_agent=creator_agent)
            return {"status": "success", "message": "Plan execution started"}
        else:
            return {"status": "error", "message": "No plan found to execute"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/trigger/maintenance")
async def trigger_maintenance():
    """Trigger maintenance tasks."""
    try:
        maintainer_agent.perform_maintenance()
        return {"status": "success", "message": "Maintenance tasks started"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/trigger/improve-repo")
async def trigger_improve_repo(repo_name: str):
    """Trigger improvement of a specific repository."""
    try:
        # Create a dummy idea for improvement
        idea = {
            "name": repo_name,
            "description": f"Improvement for {repo_name}",
            "tech_stack": [],
            "roadmap": [f"Improve {repo_name} functionality"]
        }
        
        creator_agent._improve_repository(repo_name, idea["description"], idea["roadmap"], idea["tech_stack"])
        return {"status": "success", "message": f"Improvement process started for {repo_name}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/trigger/brainstorm")
async def trigger_brainstorm():
    """Trigger brainstorming of new ideas."""
    try:
        ideas = idea_agent.fetch_and_rank_ideas(top_n=5)
        return {"status": "success", "ideas": ideas}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)