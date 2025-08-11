"""
Maintainer Agent for Monsterrr.
"""


from datetime import datetime, timedelta
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
        except Exception as e:
            self.logger.error(f"[MaintainerAgent] Error in maintenance: {e}")

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
            return dt < datetime.utcnow() - timedelta(days=self.stale_days)
        except Exception:
            return False

if __name__ == "__main__":
    import logging
    import os
    from services.github_service import GitHubService
    from services.groq_service import GroqService
    from utils.logger import setup_logger
    logger = setup_logger()
    github = GitHubService(logger=logger)
    groq = GroqService(api_key=os.getenv("GROQ_API_KEY"), logger=logger)
    agent = MaintainerAgent(github, groq, logger)
    agent.perform_maintenance()
