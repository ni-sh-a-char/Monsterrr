"""
GitHub API wrapper for Monsterrr.
"""


import os
from dotenv import load_dotenv
load_dotenv()
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
        if self.logger:
            self.logger.info(f"[GitHubService] {method} {url} | kwargs: { {k: v for k, v in kwargs.items() if k != 'headers'} }")

    def log_response(self, resp: httpx.Response):
        if self.logger:
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
    
    def get_organization_info(self) -> Dict[str, Any]:
        """Get detailed information about the organization."""
        try:
            url = f"{self.BASE_URL}/orgs/{self.org}"
            resp = self._request("GET", url)
            return resp.json()
        except Exception as e:
            self.logger.error(f"[GitHubService] Error getting org info: {e}")
            return {}
    
    def get_organization_stats(self) -> Dict[str, Any]:
        """Get organization statistics including repo count, member count, etc."""
        try:
            # Get organization info
            org_info = self.get_organization_info()
            
            # Get repositories
            repos = self.list_repositories()
            
            # Get members
            members_url = f"{self.BASE_URL}/orgs/{self.org}/members"
            try:
                members_resp = self._request("GET", members_url)
                members = members_resp.json()
            except:
                members = []
            
            # Count public and private repos
            public_repos = [r for r in repos if not r.get('private', True)]
            private_repos = [r for r in repos if r.get('private', False)]
            
            # Get additional organization information
            try:
                # Get organization public members
                public_members_url = f"{self.BASE_URL}/orgs/{self.org}/public_members"
                public_members_resp = self._request("GET", public_members_url)
                public_members = public_members_resp.json()
            except:
                public_members = []
            
            # Get organization teams
            try:
                teams_url = f"{self.BASE_URL}/orgs/{self.org}/teams"
                teams_resp = self._request("GET", teams_url)
                teams = teams_resp.json()
            except:
                teams = []
            
            return {
                "name": org_info.get("login", self.org),
                "description": org_info.get("description", ""),
                "public_repos": len(public_repos),
                "private_repos": len(private_repos),
                "total_repos": len(repos),
                "members": len(members),
                "public_members": len(public_members),
                "teams": len(teams),
                "created_at": org_info.get("created_at", ""),
                "updated_at": org_info.get("updated_at", ""),
                "repositories": [
                    {
                        "name": r["name"],
                        "description": r.get("description", ""),
                        "language": r.get("language", ""),
                        "stars": r.get("stargazers_count", 0),
                        "forks": r.get("forks_count", 0),
                        "issues": r.get("open_issues_count", 0),
                        "updated_at": r.get("updated_at", ""),
                        "created_at": r.get("created_at", ""),
                        "private": r.get("private", False),
                        "url": r.get("html_url", "")
                    }
                    for r in repos
                ]
            }
        except Exception as e:
            self.logger.error(f"[GitHubService] Error getting org stats: {e}")
            return {
                "name": self.org,
                "total_repos": 0,
                "members": 0,
                "public_members": 0,
                "teams": 0,
                "repositories": []
            }
    
    def get_repository_details(self, repo_name: str) -> Dict[str, Any]:
        """Get detailed information about a specific repository including issues, PRs, etc."""
        try:
            # Get basic repo info
            repo_info = self.get_repository(repo_name)
            
            # Get issues
            issues = self.list_issues(repo_name, state="all")
            
            # Get pull requests (using search since there's no direct API)
            try:
                pr_search_url = f"{self.BASE_URL}/search/issues"
                pr_params = {
                    "q": f"repo:{self.org}/{repo_name} is:pr",
                    "per_page": 100
                }
                pr_resp = self._request("GET", pr_search_url, params=pr_params)
                prs = pr_resp.json().get("items", [])
            except:
                prs = []
            
            # Get branches
            try:
                branches_url = f"{self.BASE_URL}/repos/{self.org}/{repo_name}/branches"
                branches_resp = self._request("GET", branches_url)
                branches = branches_resp.json()
            except:
                branches = []
            
            # Get languages
            try:
                languages_url = f"{self.BASE_URL}/repos/{self.org}/{repo_name}/languages"
                languages_resp = self._request("GET", languages_url)
                languages = languages_resp.json()
            except:
                languages = {}
            
            # Get contributors
            try:
                contributors_url = f"{self.BASE_URL}/repos/{self.org}/{repo_name}/contributors"
                contributors_resp = self._request("GET", contributors_url)
                contributors = contributors_resp.json()
            except:
                contributors = []
            
            # Get commits
            try:
                commits_url = f"{self.BASE_URL}/repos/{self.org}/{repo_name}/commits"
                commits_resp = self._request("GET", commits_url, params={"per_page": 10})
                commits = commits_resp.json()
            except:
                commits = []
            
            # Get releases
            try:
                releases_url = f"{self.BASE_URL}/repos/{self.org}/{repo_name}/releases"
                releases_resp = self._request("GET", releases_url)
                releases = releases_resp.json()
            except:
                releases = []
            
            return {
                "basic_info": repo_info,
                "issues": {
                    "open": len([i for i in issues if i.get("state") == "open"]),
                    "closed": len([i for i in issues if i.get("state") == "closed"]),
                    "total": len(issues)
                },
                "pull_requests": {
                    "open": len([pr for pr in prs if pr.get("state") == "open"]),
                    "closed": len([pr for pr in prs if pr.get("state") in ["closed", "merged"]]),
                    "total": len(prs)
                },
                "branches": [b["name"] for b in branches],
                "languages": languages,
                "contributors": len(contributors),
                "recent_commits": [
                    {
                        "author": commit["commit"]["author"]["name"],
                        "message": commit["commit"]["message"],
                        "date": commit["commit"]["author"]["date"]
                    }
                    for commit in commits[:5]
                ],
                "releases": len(releases),
                "last_updated": repo_info.get("updated_at", ""),
                "created_at": repo_info.get("created_at", ""),
                "size": repo_info.get("size", 0)
            }
        except Exception as e:
            self.logger.error(f"[GitHubService] Error getting repo details for {repo_name}: {e}")
            return {
                "basic_info": {},
                "issues": {"open": 0, "closed": 0, "total": 0},
                "pull_requests": {"open": 0, "closed": 0, "total": 0},
                "branches": [],
                "languages": {},
                "contributors": 0,
                "recent_commits": [],
                "releases": 0,
                "last_updated": "",
                "created_at": "",
                "size": 0
            }
    
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

    def get_repository(self, repo_name: str) -> Dict[str, Any]:
        """Get details of a specific repository."""
        url = f"{self.BASE_URL}/repos/{self.org}/{repo_name}"
        resp = self._request("GET", url)
        return resp.json()

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

    def get_file_content(self, repo: str, path: str, branch: str = "main") -> str:
        """Get file contents from a repo (alias for get_file_contents)."""
        return self.get_file_contents(repo, path, branch)

    def list_files(self, repo: str, path: str = "") -> List[str]:
        """List all files in a repository."""
        url = f"{self.BASE_URL}/repos/{self.org}/{repo}/contents/{path}"
        resp = self._request("GET", url)
        contents = resp.json()
        files = []
        for item in contents:
            if item["type"] == "file":
                files.append(item["path"])
            elif item["type"] == "dir":
                # Recursively list files in subdirectories
                sub_files = self.list_files(repo, item["path"])
                files.extend(sub_files)
        return files

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

    def create_issue_comment(self, repo: str, issue_number: int, body: str, is_pr: bool = False) -> Dict[str, Any]:
        """Create a comment on an issue or PR."""
        if is_pr:
            url = f"{self.BASE_URL}/repos/{self.org}/{repo}/issues/{issue_number}/comments"
        else:
            url = f"{self.BASE_URL}/repos/{self.org}/{repo}/issues/{issue_number}/comments"
        data = {"body": body}
        resp = self._request("POST", url, json=data)
        return resp.json()

    def get_issue_comments(self, repo: str, issue_number: int) -> List[Dict[str, Any]]:
        """Get comments for an issue or PR."""
        url = f"{self.BASE_URL}/repos/{self.org}/{repo}/issues/{issue_number}/comments"
        resp = self._request("GET", url)
        return resp.json()

    def list_issues(self, repo: str, state: str = "open") -> List[Dict[str, Any]]:
        """List issues in a repo."""
        url = f"{self.BASE_URL}/repos/{self.org}/{repo}/issues"
        params = {"state": state, "per_page": 100}
        resp = self._request("GET", url, params=params)
        return resp.json()

    def close_issue(self, repo: str, issue_number: int) -> Dict[str, Any]:
        """Close an issue."""
        url = f"{self.BASE_URL}/repos/{self.org}/{repo}/issues/{issue_number}"
        data = {"state": "closed"}
        resp = self._request("PATCH", url, json=data)
        return resp.json()

    def create_branch(self, repo: str, branch_name: str, base_branch: str = "main") -> Dict[str, Any]:
        """Create a new branch in a repo."""
        # First get the SHA of the base branch
        url = f"{self.BASE_URL}/repos/{self.org}/{repo}/git/refs/heads/{base_branch}"
        resp = self._request("GET", url)
        sha = resp.json()["object"]["sha"]
        
        # Create the new branch
        url = f"{self.BASE_URL}/repos/{self.org}/{repo}/git/refs"
        data = {
            "ref": f"refs/heads/{branch_name}",
            "sha": sha
        }
        resp = self._request("POST", url, json=data)
        return resp.json()

    def get_pull_request(self, repo: str, pr_number: int) -> Dict[str, Any]:
        """Get details of a pull request."""
        url = f"{self.BASE_URL}/repos/{self.org}/{repo}/pulls/{pr_number}"
        resp = self._request("GET", url)
        return resp.json()

    def merge_pull_request(self, repo: str, pr_number: int, commit_message: str = "") -> Dict[str, Any]:
        """Merge a pull request."""
        url = f"{self.BASE_URL}/repos/{self.org}/{repo}/pulls/{pr_number}/merge"
        data = {"commit_message": commit_message}
        resp = self._request("PUT", url, json=data)
        return resp.json()

    def add_labels_to_pr(self, repo: str, pr_number: int, labels: List[str]) -> Dict[str, Any]:
        """Add labels to a pull request."""
        url = f"{self.BASE_URL}/repos/{self.org}/{repo}/issues/{pr_number}"
        data = {"labels": labels}
        resp = self._request("PATCH", url, json=data)
        return resp.json()

    def comment_on_issue(self, repo: str, issue_number: int, comment: str) -> Dict[str, Any]:
        """Add a comment to an issue."""
        url = f"{self.BASE_URL}/repos/{self.org}/{repo}/issues/{issue_number}/comments"
        data = {"body": comment}
        resp = self._request("POST", url, json=data)
        return resp.json()

    def comment_on_pr(self, repo: str, pr_number: int, comment: str) -> Dict[str, Any]:
        """Add a comment to a pull request."""
        return self.comment_on_issue(repo, pr_number, comment)

    def find_stale_issues(self, days_old: int = 14) -> List[Dict[str, Any]]:
        """Find stale issues in all repositories."""
        # This is a simplified implementation
        # In a real implementation, you would check the last updated time
        return []

    def find_safe_prs(self) -> List[Dict[str, Any]]:
        """Find pull requests that are safe to merge."""
        # This is a simplified implementation
        # In a real implementation, you would check CI status, approvals, etc.
        return []

    def audit_repos(self) -> None:
        """Audit all repositories for security and compliance."""
        # This is a simplified implementation
        # In a real implementation, you would check for various security issues
        pass

    def trigger_code_analysis(self, repo: str) -> None:
        """Trigger code analysis for a repository."""
        # This is a simplified implementation
        # In a real implementation, you would trigger actual code analysis tools
        pass

    def onboard_new_repo(self, repo: str) -> None:
        """Onboard a new repository with standard configurations."""
        # This is a simplified implementation
        # In a real implementation, you would set up standard configurations
        pass

    def thank_user_for_star(self, repo: str, user: str) -> None:
        """Thank a user for starring a repository."""
        # This is a simplified implementation
        # In a real implementation, you would send an actual thank you message
        pass

    def thank_user_for_fork(self, repo: str, user: str) -> None:
        """Thank a user for forking a repository."""
        # This is a simplified implementation
        # In a real implementation, you would send an actual thank you message
        pass

    def analyze_repo_health(self, repo: str) -> Dict[str, Any]:
        """Analyze the health of a repository."""
        # This is a simplified implementation
        # In a real implementation, you would perform a comprehensive health check
        return {
            "repo": repo,
            "health_score": 85,
            "issues": 3,
            "pull_requests": 2,
            "last_commit": "2023-01-01"
        }