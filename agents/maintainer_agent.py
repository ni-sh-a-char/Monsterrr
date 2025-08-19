"""
Maintainer Agent for Monsterrr.
"""


from datetime import datetime, timedelta, timezone
IST = timezone(timedelta(hours=5, minutes=30))
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from typing import List, Dict, Any

class MaintainerAgent:
    """
    Agent for maintaining repositories and handling issues/PRs.
    Monitors for stale PRs/issues, responds with Groq, auto-closes inactive tickets.
    """
    def __init__(self, github_service, groq_client, logger, stale_days: int = 14):
        self.github_service = github_service
        self.groq_client = groq_client
        self.logger = logger
        self.stale_days = stale_days

    def plan_daily_contributions(self, num_contributions: int = 3, save_path: str = None) -> list:
        """
        Use Groq LLM to plan exactly `num_contributions` meaningful contributions for today.
        Contributions can be repo creation or feature branch (with AI-generated name).
        Saves plan to logs/daily_plan_<date>.json.
        Deletes previous daily_plan_*.json files to avoid storage accumulation.
        Returns parsed plan (list of dicts).
        """
        from datetime import datetime
        import json, os, glob
        repos = self.github_service.list_repositories()
        repo_metadata = [
            {"name": r["name"], "description": r.get("description", ""), "topics": r.get("topics", [])}
            for r in repos
        ]
        prompt = (
            f"You are Monsterrr, an autonomous GitHub org manager. Given the following org repo metadata, "
            f"plan exactly {num_contributions} meaningful, substantial contributions for today. "
            f"Each contribution must be a significant step toward a fully working, production-quality project. "
            f"Write real, runnable code, not just stubs. Gradually build out features, tests, and documentation over time. "
            f"Plan multi-day features and break them into daily tasks, so each day builds on the last. "
            f"Each contribution must be either: (1) create a new repo (with AI-generated name, description, tech stack, roadmap), "
            f"or (2) create a feature branch in an existing repo (with AI-generated branch name, short description, and a substantial starter file/change idea). "
            f"Branch names must be valid for Git, unique, and descriptive. Output a JSON list of contributions, each with type ('repo' or 'branch'), target repo (if branch), name, description, and details."
            f"\n\nOrg repo metadata: {json.dumps(repo_metadata)[:4000]}"
        )
        self.logger.info(f"[MaintainerAgent] Planning daily contributions with Groq.")
        plan = []
        try:
            response = self.groq_client.groq_llm(prompt)
            self.logger.info(f"[MaintainerAgent] Groq plan raw response: {response[:2000]}")
            try:
                plan = json.loads(response)
            except Exception as e:
                self.logger.error(f"[MaintainerAgent] Groq plan not valid JSON: {e}. Re-prompting.")
                retry_prompt = prompt + "\n\nReturn ONLY a valid JSON list, no extra text. If you cannot, return []."
                response2 = self.groq_client.groq_llm(retry_prompt)
                try:
                    plan = json.loads(response2)
                except Exception as e2:
                    self.logger.error(f"[MaintainerAgent] Groq retry plan still not valid JSON: {e2}. Returning empty list.")
                    plan = []
            self.logger.info(f"[MaintainerAgent] Got {len(plan)} planned contributions.")
        except Exception as e:
            self.logger.error(f"[MaintainerAgent] Groq planning error: {e}")
            plan = []
        # Save plan to logs/daily_plan_<date>.json
        date_str = datetime.now(IST).strftime("%Y-%m-%d")
        save_path = f"logs/daily_plan_{date_str}.json"
        try:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            # Delete previous daily_plan_*.json files except today's
            for old_file in glob.glob("logs/daily_plan_*.json"):
                if old_file != save_path:
                    try:
                        os.remove(old_file)
                        self.logger.info(f"[MaintainerAgent] Deleted old plan file: {old_file}")
                    except Exception as e:
                        self.logger.warning(f"[MaintainerAgent] Could not delete {old_file}: {e}")
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(plan, f, indent=2)
            self.logger.info(f"[MaintainerAgent] Saved daily plan to {save_path}")
        except Exception as e:
            self.logger.error(f"[MaintainerAgent] Error saving daily plan: {e}")
        return plan

    def execute_daily_plan(self, plan: list, creator_agent=None, dry_run: bool = False) -> None:
        """
        Execute the daily contribution plan. Supports dry-run mode.
        For repo creation, calls CreatorAgent. For branch, creates branch, commits starter file/change, opens issue.
        All actions are logged and auditable.
        """
        import os
        import json
        for idx, contrib in enumerate(plan):
            ctype = contrib.get("type")
            name = contrib.get("name")
            desc = contrib.get("description", "")
            details = contrib.get("details", {})
            target_repo = contrib.get("target_repo")
            self.logger.info(f"[MaintainerAgent] Executing contribution {idx+1}: {ctype} | {name}")
            if dry_run:
                self.logger.info(f"[MaintainerAgent] DRY RUN: Would execute {ctype} | {name} | {desc} | {details}")
                continue
            try:
                if ctype == "repo" and creator_agent:
                    idea = {"name": name, "description": desc}
                    idea.update(details)
                    creator_agent.create_repository(idea)
                    self.logger.info(f"[MaintainerAgent] Created repo: {name}")
                elif ctype == "branch" and target_repo:
                    branch_name = name
                    # Create branch
                    self.github_service.create_branch(target_repo, branch_name)
                    self.logger.info(f"[MaintainerAgent] Created branch {branch_name} in {target_repo}")
                    # Commit starter file/change
                    file_path = details.get("file_path", "starter.txt")
                    file_content = details.get("file_content", f"Starter for {branch_name}: {desc}")
                    commit_msg = details.get("commit_message", f"Add starter for {branch_name}")
                    self.github_service.create_or_update_file(target_repo, file_path, file_content, commit_msg, branch=branch_name)
                    self.logger.info(f"[MaintainerAgent] Committed {file_path} to {branch_name} in {target_repo}")
                    # Open issue
                    issue_title = details.get("issue_title", f"[feature] {branch_name}: {desc}")
                    issue_body = details.get("issue_body", f"Auto-generated by Monsterrr for branch {branch_name}.")
                    self.github_service.create_issue(target_repo, issue_title, issue_body, labels=["feature", "bot-suggestion"])
                    self.logger.info(f"[MaintainerAgent] Opened issue for branch {branch_name} in {target_repo}")
                    # Update monsterrr_state.json with branch/action
                    state_path = os.path.join(os.getcwd(), "monsterrr_state.json")
                    state = {}
                    if os.path.exists(state_path):
                        with open(state_path, "r", encoding="utf-8") as f:
                            try:
                                state = json.load(f)
                            except Exception:
                                state = {}
                    branches = state.get("branches", [])
                    branch_entry = {
                        "name": branch_name,
                        "repo": target_repo,
                        "description": desc,
                        "file_path": file_path,
                        "commit_msg": commit_msg,
                        "issue_title": issue_title
                    }
                    branches.append(branch_entry)
                    state["branches"] = branches
                    actions = state.get("actions", [])
                    actions.append(f"Created branch {branch_name} in {target_repo} and committed {file_path}")
                    state["actions"] = actions
                    with open(state_path, "w", encoding="utf-8") as f:
                        json.dump(state, f, indent=2)
                else:
                    self.logger.warning(f"[MaintainerAgent] Unknown contribution type or missing target_repo: {contrib}")
            except Exception as e:
                self.logger.error(f"[MaintainerAgent] Error executing contribution {idx+1}: {e}")

    def perform_maintenance(self) -> None:
        """
        Perform maintenance tasks across all repositories:
        - Respond to open issues with Groq suggestions
        - Auto-close stale issues/PRs
        """
        self.logger.info("[MaintainerAgent] Performing maintenance tasks.")
        try:
            repos = self.github_service.list_repositories()
            for repo in repos:
                repo_name = repo["name"] if isinstance(repo, dict) else repo
                self._handle_issues(repo_name)
                self._handle_pull_requests(repo_name)
                self._update_code(repo_name)
        except Exception as e:
            self.logger.error(f"[MaintainerAgent] Error in maintenance: {e}")

    def _update_code(self, repo: str):
        """Stub for code update/push logic (expand as needed)."""
        self.logger.info(f"[MaintainerAgent] (Stub) Would update code for repo: {repo}")

    def _handle_issues(self, repo: str):
        issues = self.github_service.list_issues(repo, state="open")
        for issue in issues:
            if "pull_request" in issue:
                continue  # skip PRs
            number = issue["number"]
            title = issue["title"]
            created_at = issue.get("created_at")
            last_updated = issue.get("updated_at", created_at)
            if self._is_stale(last_updated):
                self.github_service.close_issue(repo, number)
                self.logger.info(f"[MaintainerAgent] Closed stale issue #{number} in {repo}")
                continue
            # Respond to issues with Groq suggestion
            try:
                prompt = f"Suggest a concise fix or next step for this GitHub issue: {title}"
                suggestion = self.groq_client.groq_llm(prompt)
                self.github_service.create_issue(
                    repo,
                    title=f"Automated suggestion for issue #{number}",
                    body=suggestion,
                    labels=["bot-suggestion"]
                )
                self.logger.info(f"[MaintainerAgent] Suggested fix for issue #{number} in {repo}")
            except Exception as e:
                self.logger.error(f"[MaintainerAgent] Error suggesting fix for issue #{number}: {e}")

    def _handle_pull_requests(self, repo: str):
        prs = self.github_service.list_issues(repo, state="open")
        for pr in prs:
            if "pull_request" not in pr:
                continue
            number = pr["number"]
            last_updated = pr.get("updated_at", pr.get("created_at"))
            if self._is_stale(last_updated):
                # Optionally auto-close or comment on stale PRs
                self.logger.info(f"[MaintainerAgent] PR #{number} in {repo} is stale.")

    def _is_stale(self, last_updated: str) -> bool:
        try:
            dt = datetime.strptime(last_updated, "%Y-%m-%dT%H:%M:%SZ")
            return dt < datetime.now(IST) - timedelta(days=self.stale_days)
        except Exception:
            return False

if __name__ == "__main__":
    import logging
    import os
    from dotenv import load_dotenv
    load_dotenv()
    from services.github_service import GitHubService
    from services.groq_service import GroqService
    from utils.logger import setup_logger
    from utils.config import Settings
    logger = setup_logger()
    settings = Settings()
    try:
        settings.validate()
    except Exception as e:
        logger.error(f"[Config] {e}")
        raise
    github = GitHubService(logger=logger)
    try:
        github.validate_credentials()
    except Exception as e:
        logger.error(f"[GitHubService] {e}")
        raise
    groq = GroqService(api_key=settings.GROQ_API_KEY, logger=logger)
    agent = MaintainerAgent(github, groq, logger)
    agent.perform_maintenance()
