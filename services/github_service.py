"""
GitHub API wrapper for Monsterrr.
"""


import os
import httpx
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from typing import Optional, List, Dict, Any

class GitHubAPIError(Exception):
    """Custom exception for GitHub API errors."""
    pass

class BaseService:
    """Base service for shared retry, logging, and error handling."""
    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def log_request(self, method: str, url: str, **kwargs):
        self.logger.info(f"[GitHubService] {method} {url} | kwargs: { {k: v for k, v in kwargs.items() if k != 'headers'} }")

    def log_response(self, resp: httpx.Response):
        self.logger.info(f"[GitHubService] Response {resp.status_code} {resp.url}")

    def handle_error(self, resp: httpx.Response):
        if resp.status_code == 403 and 'X-RateLimit-Remaining' in resp.headers and resp.headers['X-RateLimit-Remaining'] == '0':
            reset = int(resp.headers.get('X-RateLimit-Reset', '0'))
            raise GitHubAPIError(f"Rate limit exceeded. Retry after {reset}.")
        elif resp.status_code == 404:
            raise GitHubAPIError(f"Resource not found: {resp.url}")
        else:
            raise GitHubAPIError(f"GitHub API error {resp.status_code}: {resp.text}")

class GitHubService(BaseService):
    def validate_credentials(self):
        """Validate GitHub token and org access, log redacted token/org, fail fast if invalid."""
        redacted_token = self.token[:6] + "..." + self.token[-4:] if self.token else "MISSING"
        self.logger.info(f"[GitHubService] Startup: GITHUB_ORG={self.org} GITHUB_TOKEN={redacted_token}")
        if not self.token:
            raise RuntimeError("Missing GITHUB_TOKEN")
        if not self.org:
            raise RuntimeError("Missing GITHUB_ORG")
        try:
            with httpx.Client(timeout=10) as client:
                user_resp = client.get(f"{self.BASE_URL}/user", headers=self.headers)
                org_resp = client.get(f"{self.BASE_URL}/orgs/{self.org}", headers=self.headers)
            if user_resp.status_code != 200:
                raise RuntimeError(f"GitHub token invalid: {user_resp.text}")
            if org_resp.status_code != 200:
                raise RuntimeError(f"GitHub org invalid or not visible: {org_resp.text}")
        except Exception as e:
            self.logger.error(f"[GitHubService] Credential validation error: {e}")
            raise
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), retry=retry_if_exception_type(httpx.RequestError))
    def fetch_trending_repositories(self) -> List[Dict[str, Any]]:
        """Fetch trending repositories using GitHub Search API (primary) or HTML scrape (fallback)."""
        search_url = f"{self.BASE_URL}/search/repositories?q=stars:>1000&sort=stars&order=desc&per_page=25"
        try:
            resp = self._request("GET", search_url)
            data = resp.json()
            repos = []
            for item in data.get("items", []):
                repos.append({"name": item["name"], "description": item.get("description", "")})
            if repos:
                return repos
        except Exception as e:
            self.logger.error(f"[GitHubService] Search API error: {e}")
        # Fallback: scrape HTML
        try:
            import requests
            from bs4 import BeautifulSoup
            html_url = "https://github.com/trending?since=weekly"
            resp = requests.get(html_url, timeout=10)
            bs = BeautifulSoup(resp.text, "html.parser")
            repos = []
            for repo_tag in bs.select("article.Box-row"):
                name_tag = repo_tag.select_one("h2 a")
                desc_tag = repo_tag.select_one("p")
                name = name_tag.text.strip().replace("\n", "").replace(" ", "") if name_tag else ""
                desc = desc_tag.text.strip() if desc_tag else ""
                if name:
                    repos.append({"name": name, "description": desc})
            if repos:
                return repos
        except Exception as e:
            self.logger.error(f"[GitHubService] Trending HTML scrape error: {e}")
        return []
    """
    Service for interacting with the GitHub REST API (and optional GraphQL API).
    Provides methods for repo, file, issue, PR, and branch management.
    """
    BASE_URL = "https://api.github.com"

    def __init__(self, logger: logging.Logger = None):
        logger = logger or logging.getLogger("monsterrr.github")
        super().__init__(logger)
        self.token = os.getenv("GITHUB_TOKEN")
        self.org = os.getenv("GITHUB_ORG")
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json"
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), retry=retry_if_exception_type(httpx.RequestError))
    def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        self.log_request(method, url, **kwargs)
        try:
            with httpx.Client(timeout=30) as client:
                resp = client.request(method, url, headers=self.headers, **kwargs)
            self.log_response(resp)
            if resp.status_code >= 400:
                self.handle_error(resp)
            return resp
        except httpx.RequestError as e:
            self.logger.error(f"[GitHubService] Network error: {e}")
            raise

    def list_repositories(self) -> List[Dict[str, Any]]:
        """List all repositories in the organization (handles pagination)."""
        url = f"{self.BASE_URL}/orgs/{self.org}/repos"
        repos = []
        params = {"per_page": 100, "type": "all"}
        while url:
            resp = self._request("GET", url, params=params)
            repos.extend(resp.json())
            url = resp.links.get('next', {}).get('url')
            params = None  # Only needed for first page
        return repos

    def create_repository(self, name: str, description: str = "", private: bool = False) -> Dict[str, Any]:
        """Create a new repository in the organization."""
        url = f"{self.BASE_URL}/orgs/{self.org}/repos"
        data = {"name": name, "description": description, "private": private, "auto_init": True}
        resp = self._request("POST", url, json=data)
        return resp.json()

    def delete_repository(self, repo_name: str, confirm: bool = False) -> None:
        """Delete a repository (requires confirm=True)."""
        if not confirm:
            raise ValueError("Set confirm=True to actually delete the repository.")
        url = f"{self.BASE_URL}/repos/{self.org}/{repo_name}"
        self._request("DELETE", url)

    def archive_repository(self, repo_name: str) -> Dict[str, Any]:
        """Archive a repository."""
        url = f"{self.BASE_URL}/repos/{self.org}/{repo_name}"
        data = {"archived": True}
        resp = self._request("PATCH", url, json=data)
        return resp.json()

    def get_file_contents(self, repo: str, path: str, branch: str = "main") -> str:
        """Get file contents from a repo."""
        url = f"{self.BASE_URL}/repos/{self.org}/{repo}/contents/{path}?ref={branch}"
        resp = self._request("GET", url)
        import base64
        content = resp.json()["content"]
        return base64.b64decode(content).decode("utf-8")

    def create_or_update_file(self, repo: str, path: str, content: str, commit_message: str, branch: str = "main") -> Dict[str, Any]:
        """Create or update a file in a repo."""
        url = f"{self.BASE_URL}/repos/{self.org}/{repo}/contents/{path}"
        import base64
        encoded = base64.b64encode(content.encode()).decode()
        # Check if file exists
        try:
            resp = self._request("GET", url, params={"ref": branch})
            sha = resp.json()["sha"]
        except GitHubAPIError:
            sha = None
        data = {"message": commit_message, "content": encoded, "branch": branch}
        if sha:
            data["sha"] = sha
        resp = self._request("PUT", url, json=data)
        return resp.json()

    def delete_file(self, repo: str, path: str, commit_message: str, branch: str = "main") -> Dict[str, Any]:
        """Delete a file from a repo."""
        url = f"{self.BASE_URL}/repos/{self.org}/{repo}/contents/{path}"
        # Get file SHA
        resp = self._request("GET", url, params={"ref": branch})
        sha = resp.json()["sha"]
        data = {"message": commit_message, "sha": sha, "branch": branch}
        resp = self._request("DELETE", url, json=data)
        return resp.json()

    def create_issue(self, repo: str, title: str, body: str = "", labels: Optional[List[str]] = None) -> Dict[str, Any]:
        """Create an issue in a repo."""
        url = f"{self.BASE_URL}/repos/{self.org}/{repo}/issues"
        data = {"title": title, "body": body}
        if labels:
            data["labels"] = labels
        resp = self._request("POST", url, json=data)
        return resp.json()

    def list_issues(self, repo: str, state: str = "open") -> List[Dict[str, Any]]:
        """List issues in a repo (handles pagination)."""
        url = f"{self.BASE_URL}/repos/{self.org}/{repo}/issues"
        issues = []
        params = {"state": state, "per_page": 100}
        while url:
            resp = self._request("GET", url, params=params)
            issues.extend(resp.json())
            url = resp.links.get('next', {}).get('url')
            params = None
        return issues

    def close_issue(self, repo: str, issue_number: int) -> Dict[str, Any]:
        """Close an issue in a repo."""
        url = f"{self.BASE_URL}/repos/{self.org}/{repo}/issues/{issue_number}"
        data = {"state": "closed"}
        resp = self._request("PATCH", url, json=data)
        return resp.json()

    def create_pull_request(self, repo: str, title: str, head_branch: str, base_branch: str = "main", body: str = "") -> Dict[str, Any]:
        """Create a pull request."""
        url = f"{self.BASE_URL}/repos/{self.org}/{repo}/pulls"
        data = {"title": title, "head": head_branch, "base": base_branch, "body": body}
        resp = self._request("POST", url, json=data)
        return resp.json()

    def merge_pull_request(self, repo: str, pr_number: int, merge_method: str = "merge") -> Dict[str, Any]:
        """Merge a pull request."""
        url = f"{self.BASE_URL}/repos/{self.org}/{repo}/pulls/{pr_number}/merge"
        data = {"merge_method": merge_method}
        resp = self._request("PUT", url, json=data)
        return resp.json()

    def list_branches(self, repo: str) -> List[str]:
        """List all branches in a repo."""
        url = f"{self.BASE_URL}/repos/{self.org}/{repo}/branches"
        resp = self._request("GET", url)
        return [b["name"] for b in resp.json()]

    def create_branch(self, repo: str, new_branch: str, from_branch: str = "main") -> Dict[str, Any]:
        """Create a new branch from an existing branch."""
        # Get SHA of from_branch
        url = f"{self.BASE_URL}/repos/{self.org}/{repo}/git/refs/heads/{from_branch}"
        resp = self._request("GET", url)
        sha = resp.json()["object"]["sha"]
        # Create new branch
        url = f"{self.BASE_URL}/repos/{self.org}/{repo}/git/refs"
        data = {"ref": f"refs/heads/{new_branch}", "sha": sha}
        resp = self._request("POST", url, json=data)
        return resp.json()

    def delete_branch(self, repo: str, branch: str) -> None:
        """Delete a branch from a repo."""
        url = f"{self.BASE_URL}/repos/{self.org}/{repo}/git/refs/heads/{branch}"
        self._request("DELETE", url)
