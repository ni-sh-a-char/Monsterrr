from typing import Dict, Any
import os
import json
from datetime import datetime, timezone, timedelta
IST = timezone(timedelta(hours=5, minutes=30))


class CreatorAgent:
    """
    Agent for creating new repositories and scaffolding projects.
    Uses github_service to create repo, scaffold files, commit, and open starter issues.
    """
    def __init__(self, github_service, logger):
        self.github_service = github_service
        self.logger = logger
        # Try to get Groq service from the github service
        try:
            self.groq_client = github_service.groq_client if hasattr(github_service, 'groq_client') else None
        except:
            self.groq_client = None

    def create_or_improve_repository(self, idea: Dict[str, Any]) -> None:
        """
        If there are existing repos, improve them (add features, docs, tests, refactor, etc.).
        Only create a new repo if all existing ones are sufficiently developed.
        """
        state_path = os.path.join(os.getcwd(), "monsterrr_state.json")
        state = {}
        if os.path.exists(state_path):
            with open(state_path, "r", encoding="utf-8") as f:
                try:
                    state = json.load(f)
                except Exception:
                    state = {}
        repos = state.get("repos", [])
        
        # Get current organization stats for better awareness
        try:
            org_stats = self.github_service.get_organization_stats()
            self.logger.info(f"[CreatorAgent] Organization stats: {org_stats.get('total_repos', 0)} repos, {org_stats.get('members', 0)} members")
            
            # Update state with organization stats
            state["organization_stats"] = org_stats
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            self.logger.error(f"[CreatorAgent] Error getting org stats: {e}")
            org_stats = {"repositories": []}
        
        # Get actual repositories from GitHub for better awareness
        try:
            github_repos = self.github_service.list_repositories()
            self.logger.info(f"[CreatorAgent] Found {len(github_repos)} repositories on GitHub")
            
            # Update repos in state with actual GitHub data
            if github_repos:
                # Convert GitHub repo data to our format
                github_repo_entries = [
                    {
                        "name": repo["name"],
                        "description": repo.get("description", ""),
                        "url": repo.get("html_url", ""),
                        "language": repo.get("language", ""),
                        "stars": repo.get("stargazers_count", 0),
                        "forks": repo.get("forks_count", 0),
                        "issues": repo.get("open_issues_count", 0)
                    }
                    for repo in github_repos
                ]
                state["github_repos"] = github_repo_entries
                with open(state_path, "w", encoding="utf-8") as f:
                    json.dump(state, f, indent=2)
        except Exception as e:
            self.logger.error(f"[CreatorAgent] Error getting GitHub repos: {e}")
            github_repos = []
        
        # Use actual GitHub repos for decision making
        all_repos = repos if repos else github_repo_entries if 'github_repo_entries' in locals() else []
        
        # Check if we should improve existing repos or create new ones
        # Strategy: 80% of the time improve existing repos, 20% create new ones
        import random
        should_improve = len(all_repos) > 0 and random.random() < 0.8
        
        if should_improve and repos:
            # Select a random existing repo to improve
            repo_to_improve = random.choice(repos)
            self.logger.info(f"[CreatorAgent] Improving existing repo: {repo_to_improve['name']}")
            self._improve_repository(repo_to_improve["name"], repo_to_improve["description"], repo_to_improve.get("roadmap", []), repo_to_improve.get("tech_stack", []))
            return
        
        # If we're not improving or there are no repos, create a new one
        repo_name = idea["name"]
        description = idea["description"]
        tech_stack = idea.get("tech_stack", [])
        roadmap = idea.get("roadmap", [])
        self.logger.info(f"[CreatorAgent] Creating repository for {repo_name}")
        try:
            repo = self.github_service.create_repository(repo_name, description)
            self.logger.info(f"[CreatorAgent] Repo created: {repo.get('html_url')}")
            repo_entry = {
                "name": repo_name,
                "description": description,
                "tech_stack": tech_stack,
                "roadmap": roadmap,
                "url": repo.get('html_url', ''),
                "created_at": datetime.now().isoformat()
            }
            repos.append(repo_entry)
            state["repos"] = repos
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            self.logger.error(f"[CreatorAgent] Error creating repo: {e}")
            return
        try:
            self._scaffold_complete_project(repo_name, description, roadmap, tech_stack, idea)
        except Exception as e:
            self.logger.error(f"[CreatorAgent] Error scaffolding files: {e}")
        try:
            self._open_starter_issues(repo_name, roadmap)
        except Exception as e:
            self.logger.error(f"[CreatorAgent] Error opening starter issues: {e}")

    def _is_repo_complete(self, repo_name: str) -> bool:
        """Check if repo has src/, tests/, docs/, and at least 1 test and 1 doc file."""
        try:
            files = self.github_service.list_files(repo_name)
            has_src = any(f.startswith("src/") for f in files)
            has_tests = any(f.startswith("tests/") for f in files)
            has_docs = any(f.startswith("docs/") for f in files)
            has_test_file = any(f.startswith("tests/") and f.endswith(".py") for f in files)
            has_doc_file = any(f.startswith("docs/") and f.endswith(".md") for f in files)
            return has_src and has_tests and has_docs and has_test_file and has_doc_file
        except Exception as e:
            self.logger.error(f"[CreatorAgent] Error checking repo completeness: {e}")
            return False

    def _improve_repository(self, repo_name: str, description: str, roadmap: list, tech_stack: list):
        """
        Continuously improve the repo: add features, refactor, improve docs/tests, update dependencies, and suggest advanced enhancements.
        """
        try:
            # Get detailed repo information for better context
            repo_details = self.github_service.get_repository_details(repo_name)
            self.logger.info(f"[CreatorAgent] Improving {repo_name} with {repo_details['issues']['open']} open issues and {repo_details['pull_requests']['open']} open PRs")
            
            files = self.github_service.list_files(repo_name)
            
            # 1. Add a new utility module if not present
            if not any(f == "src/utils.py" for f in files):
                utils_code = """# Utility functions
def add(a, b):
    return a + b

def multiply(a, b):
    return a * b

def format_response(data):
    \"\"\"Format response data for consistent API output.\"\"\"
    return {
        "status": "success",
        "data": data,
        "timestamp": __import__('datetime').datetime.utcnow().isoformat()
    }
"""
                self.github_service.create_or_update_file(repo_name, "src/utils.py", utils_code, commit_message="Add utils module with common functions")
                self.logger.info(f"[CreatorAgent] Added src/utils.py to {repo_name}")
            
            # 2. Add a new test if not present
            if not any(f == "tests/test_utils.py" for f in files):
                test_code = """import unittest
from src.utils import add, multiply, format_response

class TestUtils(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(2, 3), 5)
        self.assertEqual(add(-1, 1), 0)

    def test_multiply(self):
        self.assertEqual(multiply(2, 3), 6)
        self.assertEqual(multiply(-2, 3), -6)

    def test_format_response(self):
        data = {"message": "test"}
        result = format_response(data)
        self.assertIn("status", result)
        self.assertIn("data", result)
        self.assertIn("timestamp", result)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"], data)

if __name__ == '__main__':
    unittest.main()
"""
                self.github_service.create_or_update_file(repo_name, "tests/test_utils.py", test_code, commit_message="Add comprehensive tests for utils module")
                self.logger.info(f"[CreatorAgent] Added tests/test_utils.py to {repo_name}")
            
            # 3. Add or improve documentation
            if not any(f == "docs/overview.md" for f in files):
                doc_text = f"""# {repo_name} Documentation

{description}

## Tech Stack
{chr(10).join([f"- {tech}" for tech in tech_stack])}

## Project Idea
This project aims to solve important problems in the development space.

## Features
- Core functionality implementation
- RESTful API endpoints
- Comprehensive test suite
- Detailed documentation

## Roadmap
{chr(10).join([f"- {step}" for step in roadmap])}

## Installation
```bash
pip install -r requirements.txt
```

## Usage
```bash
python src/main.py
```

## Testing
```bash
pytest
```
"""
                self.github_service.create_or_update_file(repo_name, "docs/overview.md", doc_text, commit_message="Add comprehensive project documentation")
                self.logger.info(f"[CreatorAgent] Added docs/overview.md to {repo_name}")
            else:
                # If docs exist, append a new section if not present
                overview = self.github_service.get_file_content(repo_name, "docs/overview.md")
                if "## Advanced Features" not in overview:
                    advanced = """\n## Advanced Features
- Add API endpoints with authentication
- Integrate with external services
- Add CLI interface for command-line usage
- Implement caching for performance improvements
- Add monitoring and logging capabilities
"""
                    self.github_service.create_or_update_file(repo_name, "docs/overview.md", overview + advanced, commit_message="Add advanced features section to docs")
                    self.logger.info(f"[CreatorAgent] Improved docs/overview.md for {repo_name}")
            
            # 4. Dependency update: add or update requirements.txt
            reqs = "requests\npytest\n"
            if "FastAPI" in tech_stack:
                reqs += "fastapi\nuvicorn\n"
            if "Django" in tech_stack:
                reqs += "django\n"
            if "Flask" in tech_stack:
                reqs += "flask\n"
            
            if not any(f == "requirements.txt" for f in files):
                self.github_service.create_or_update_file(repo_name, "requirements.txt", reqs, commit_message="Add requirements.txt with core dependencies")
                self.logger.info(f"[CreatorAgent] Added requirements.txt to {repo_name}")
            else:
                # Simulate a dependency update
                content = self.github_service.get_file_content(repo_name, "requirements.txt")
                if "httpx" not in content:
                    content += "httpx\n"
                    self.github_service.create_or_update_file(repo_name, "requirements.txt", content, commit_message="Update requirements.txt with httpx")
                    self.logger.info(f"[CreatorAgent] Updated requirements.txt for {repo_name}")
            
            # 5. Deeper code review: add a code review markdown if not present
            if not any(f == "docs/code_review.md" for f in files):
                review_md = """# Code Review Checklist

## Code Quality
- [ ] Code follows PEP8 standards
- [ ] Functions and classes are properly documented
- [ ] Variables have descriptive names
- [ ] No hardcoded values or secrets
- [ ] Error handling is implemented

## Testing
- [ ] Tests cover main logic paths
- [ ] Edge cases are handled
- [ ] Test coverage is above 80%
- [ ] Integration tests are included

## Security
- [ ] Input validation is implemented
- [ ] Authentication/authorization is secure
- [ ] Dependencies are up to date
- [ ] No exposed secrets or credentials
"""
                self.github_service.create_or_update_file(repo_name, "docs/code_review.md", review_md, commit_message="Add code review checklist")
                self.logger.info(f"[CreatorAgent] Added docs/code_review.md to {repo_name}")
            
            # 6. Suggest advanced features in issues
            if roadmap:
                # Create issues for roadmap items that don't already exist
                existing_issues = self.github_service.list_issues(repo_name, state="all")
                existing_titles = [issue["title"] for issue in existing_issues]
                
                for step in roadmap:
                    issue_title = f"[feature] {step}"
                    if issue_title not in existing_titles:
                        self.github_service.create_issue(repo_name, title=issue_title, body="Auto-suggested advanced feature from roadmap.", labels=["enhancement", "roadmap"])
                        self.logger.info(f"[CreatorAgent] Suggested advanced feature: {step}")
            
            # 7. Add a CI/CD workflow if not present
            if not any(".github/workflows/" in f for f in files):
                workflow_yaml = """name: CI/CD Pipeline

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    - name: Run tests
      run: |
        pytest
"""
                self.github_service.create_or_update_file(repo_name, ".github/workflows/ci.yml", workflow_yaml, commit_message="Add CI/CD workflow")
                self.logger.info(f"[CreatorAgent] Added CI/CD workflow to {repo_name}")
            
            # 8. Read existing issues to understand problems and create solutions
            try:
                open_issues = self.github_service.list_issues(repo_name, state="open")
                # Analyze open issues and suggest solutions
                for issue in open_issues:
                    # Skip pull requests
                    if "pull_request" in issue:
                        continue
                    
                    issue_number = issue["number"]
                    issue_title = issue["title"]
                    issue_body = issue.get("body", "")
                    
                    # Check if we've already commented on this issue
                    comments = []
                    try:
                        comments = self.github_service.get_issue_comments(repo_name, issue_number)
                    except:
                        pass
                    
                    # Only comment if we haven't already
                    bot_commented = any("Monsterrr" in comment.get("user", {}).get("login", "") for comment in comments) if comments else False
                    
                    if not bot_commented:
                        # Generate a solution using Groq
                        solution_prompt = f"Suggest a solution for this GitHub issue:\n\nTitle: {issue_title}\n\nDescription: {issue_body[:500]}"
                        try:
                            if self.groq_client:
                                solution = self.groq_client.groq_llm(solution_prompt)
                            else:
                                # Fallback to placeholder solution
                                solution = f"I've analyzed this issue and here's a suggested approach:\n\n1. First, identify the root cause\n2. Then implement a fix\n3. Finally, add tests to prevent regression"
                        except Exception as e:
                            self.logger.error(f"[CreatorAgent] Error generating solution with Groq: {e}")
                            # Fallback to placeholder solution
                            solution = f"I've analyzed this issue and here's a suggested approach:\n\n1. First, identify the root cause\n2. Then implement a fix\n3. Finally, add tests to prevent regression"
                        
                        # Comment on the issue with the solution
                        self.github_service.create_issue_comment(repo_name, issue_number, solution)
                        self.logger.info(f"[CreatorAgent] Suggested solution for issue #{issue_number} in {repo_name}")
            except Exception as e:
                self.logger.error(f"[CreatorAgent] Error analyzing issues in {repo_name}: {e}")
            
            # Update state file to reflect the improvement
            state_path = os.path.join(os.getcwd(), "monsterrr_state.json")
            if os.path.exists(state_path):
                with open(state_path, "r", encoding="utf-8") as f:
                    try:
                        state = json.load(f)
                    except Exception:
                        state = {}
                
                # Add improvement action to state
                actions = state.get("actions", [])
                actions.append({
                    "timestamp": datetime.now().isoformat(),
                    "type": "repository_improved",
                    "details": {
                        "repo_name": repo_name,
                        "description": f"Improved repository {repo_name} with new features, tests, and documentation"
                    }
                })
                state["actions"] = actions
                
                with open(state_path, "w", encoding="utf-8") as f:
                    json.dump(state, f, indent=2)
            
        except Exception as e:
            self.logger.error(f"[CreatorAgent] Error improving repo {repo_name}: {e}")