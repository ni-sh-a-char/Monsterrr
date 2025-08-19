"""
Monsterrr Autonomous Orchestrator
Runs daily: fetches ideas, plans 3 AI contributions, executes them, and maintains repos.
"""
import asyncio
import logging
from datetime import datetime, timedelta
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from agents.idea_agent import IdeaGeneratorAgent
from agents.maintainer_agent import MaintainerAgent
from agents.creator_agent import CreatorAgent
from services.github_service import GitHubService
from services.groq_service import GroqService
from utils.logger import setup_logger
from utils.config import Settings

logger = setup_logger()
settings = Settings()
settings.validate()
github = GitHubService(logger=logger)
groq = GroqService(api_key=settings.GROQ_API_KEY, logger=logger)
idea_agent = IdeaGeneratorAgent(groq, logger)
maintainer_agent = MaintainerAgent(github, groq, logger)
creator_agent = CreatorAgent(github, logger)

async def daily_orchestration():
    while True:
        logger.info("[Orchestrator] Starting daily AI orchestration cycle.")
        # 1. Fetch and rank new ideas
        ideas = idea_agent.fetch_and_rank_ideas(top_n=5)
        logger.info(f"[Orchestrator] Fetched and ranked {len(ideas)} ideas.")
        # 2. Plan 3 daily contributions
        plan = maintainer_agent.plan_daily_contributions(num_contributions=3)
        logger.info(f"[Orchestrator] Planned {len(plan)} daily contributions.")
        # 3. Execute the plan
        maintainer_agent.execute_daily_plan(plan, creator_agent=creator_agent)
        logger.info("[Orchestrator] Executed daily plan.")
        # 4. Perform repo maintenance
        maintainer_agent.perform_maintenance()
        logger.info("[Orchestrator] Performed repo maintenance.")
        # Sleep until next day (run at same time every day)
        now = datetime.now()
        next_run = (now + timedelta(days=1)).replace(hour=3, minute=0, second=0, microsecond=0)
        sleep_seconds = (next_run - now).total_seconds()
        logger.info(f"[Orchestrator] Sleeping for {sleep_seconds/3600:.2f} hours until next run.")
        await asyncio.sleep(max(60, sleep_seconds))

if __name__ == "__main__":
    asyncio.run(daily_orchestration())
