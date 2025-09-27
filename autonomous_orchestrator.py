import json
import gc
import asyncio
import logging
from datetime import datetime, timedelta
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import services
from services.github_service import GitHubService
from services.groq_service import GroqService
from utils.logger import setup_logger
from utils.config import Settings

# Initialize services and agents
logger = setup_logger()
settings = Settings()
try:
    settings.validate()
except Exception as e:
    logger.error(f"Configuration validation failed: {e}")

# Initialize Groq service first
try:
    groq = GroqService(api_key=settings.GROQ_API_KEY, logger=logger)
except Exception as e:
    logger.error(f"Failed to initialize Groq service: {e}")
    groq = None

# Initialize GitHub service
try:
    github = GitHubService(logger=logger)
    if groq:
        github.groq_client = groq  # Pass Groq client to GitHub service for use in issue analysis
except Exception as e:
    logger.error(f"Failed to initialize GitHub service: {e}")
    github = None

# Import agents after services are initialized
try:
    from agents.idea_agent import IdeaGeneratorAgent
    from agents.maintainer_agent import MaintainerAgent
    from agents.creator_agent import CreatorAgent
    
    # Initialize agents
    idea_agent = IdeaGeneratorAgent(groq, logger) if groq else None
    maintainer_agent = MaintainerAgent(github, groq, logger) if github and groq else None
    creator_agent = CreatorAgent(github, logger) if github else None
except Exception as e:
    logger.error(f"Failed to initialize agents: {e}")
    idea_agent = None
    maintainer_agent = None
    creator_agent = None

def log_monsterrr_action(action_type, details):
    """Append an action to monsterrr_state.json for daily reporting."""
    state_path = "monsterrr_state.json"
    try:
        if os.path.exists(state_path):
            with open(state_path, "r", encoding="utf-8") as f:
                state = json.load(f)
        else:
            state = {}
        actions = state.get("actions", [])
        actions.append({
            "timestamp": datetime.now().isoformat(),
            "type": action_type,
            "details": details
        })
        state["actions"] = actions
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to log action: {e}")

"""
Monsterrr Autonomous Orchestrator
Runs daily: fetches ideas, plans 3 AI contributions, executes them, and maintains repos.
Now includes enhanced memory management to prevent exceeding Render limits.
"""

async def daily_orchestration():
    # Check if services are properly initialized
    if not all([groq, github, idea_agent, maintainer_agent, creator_agent]):
        logger.error("[Orchestrator] Services not properly initialized. Exiting.")
        return
        
    while True:
        logger.info("[Orchestrator] Starting daily AI orchestration cycle.")
        
        # Get organization stats for better awareness
        try:
            org_stats = github.get_organization_stats()
            logger.info(f"[Orchestrator] Organization stats: {org_stats.get('total_repos', 0)} repos, {org_stats.get('members', 0)} members")
            
            # Update state with organization stats
            state_path = "monsterrr_state.json"
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
            logger.error(f"[Orchestrator] Error getting organization stats: {e}")
            org_stats = {}
        
        # 1. Fetch and rank new ideas (limit to 3 to prevent memory issues)
        try:
            ideas = idea_agent.fetch_and_rank_ideas(top_n=3)
            logger.info(f"[Orchestrator] Fetched and ranked {len(ideas)} ideas.")
            log_monsterrr_action("ideas_fetched", {"count": len(ideas), "ideas": [i.get('name','') for i in ideas]})
        except Exception as e:
            logger.error(f"[Orchestrator] Error fetching ideas: {e}")
            ideas = []
        
        # 2. Plan 3 daily contributions (limit to prevent memory issues)
        try:
            plan = maintainer_agent.plan_daily_contributions(num_contributions=3)
            logger.info(f"[Orchestrator] Planned {len(plan)} daily contributions.")
            log_monsterrr_action("daily_plan", {"count": len(plan), "plan": plan})
        except Exception as e:
            logger.error(f"[Orchestrator] Error planning contributions: {e}")
            plan = []
        
        # 3. Execute the plan with memory management
        try:
            logger.info("[Orchestrator] Executing daily plan with memory management.")
            maintainer_agent.execute_daily_plan(plan, creator_agent=creator_agent)
            logger.info("[Orchestrator] Executed daily plan.")
            log_monsterrr_action("plan_executed", {"plan": plan})
        except Exception as e:
            logger.error(f"[Orchestrator] Error executing plan: {e}")
        
        # 4. Perform repo maintenance
        try:
            logger.info("[Orchestrator] Performing repo maintenance.")
            maintainer_agent.perform_maintenance()
            logger.info("[Orchestrator] Performed repo maintenance.")
            log_monsterrr_action("maintenance", {"status": "completed"})
        except Exception as e:
            logger.error(f"[Orchestrator] Error performing maintenance: {e}")
        
        # Force garbage collection to prevent memory issues
        collected = gc.collect()
        logger.info(f"[Orchestrator] Forced garbage collection, collected {collected} objects.")
        
        # Sleep until next day (run at same time every day)
        now = datetime.now()
        next_run = (now + timedelta(days=1)).replace(hour=3, minute=0, second=0, microsecond=0)
        sleep_seconds = (next_run - now).total_seconds()
        logger.info(f"[Orchestrator] Sleeping for {sleep_seconds/3600:.2f} hours until next run.")
        await asyncio.sleep(max(60, sleep_seconds))

if __name__ == "__main__":
    asyncio.run(daily_orchestration())