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

# Start the background scheduler when the app starts
@app.on_event("startup")
async def launch_scheduler():
    loop = asyncio.get_event_loop()
    loop.create_task(start_scheduler())
settings = Settings()
logger = setup_logger()
try:
    settings.validate()
except Exception as e:
    logger.error(f"[Config] {e}")
    raise
groq = GroqService(api_key=settings.GROQ_API_KEY, logger=logger)
github = GitHubService(logger=logger)
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

@app.get("/health")
async def health():
    return {"status": "ok"}

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

@app.post("/repos/create")
async def create_repo(background_tasks: BackgroundTasks):
    """Trigger repo creation for top idea."""
    def _create():
        ideas = idea_agent.fetch_and_rank_ideas(top_n=1)
        if ideas:
            creator_agent.create_repository(ideas[0])
    background_tasks.add_task(_create)
    return {"status": "Repository creation started."}


# Manual trigger for all agents (idea, creator, maintainer)
@app.post("/run-agents")
async def run_all_agents(background_tasks: BackgroundTasks):
    """Trigger all agents manually."""
    def _run():
        ideas = idea_agent.fetch_and_rank_ideas(top_n=1)
        if ideas:
            creator_agent.create_repository(ideas[0])
        maintainer_agent.perform_maintenance()
    background_tasks.add_task(_run)
    return {"status": "All agents triggered."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
