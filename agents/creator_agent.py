"""
Creator Agent for Monsterrr.
"""


import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from typing import Dict, Any
import base64
import json

class CreatorAgent:
    """
    Agent for creating new repositories and scaffolding projects.
    Uses github_service to create repo, scaffold files, commit, and open starter issues.
    """
    def __init__(self, github_service, logger):
        self.github_service = github_service
        self.logger = logger

    def create_repository(self, idea: Dict[str, Any]) -> None:
        """
        Create a new repository for the given idea, scaffold files, and open starter issues.
        Args:
            idea (dict): Idea metadata (name, description, roadmap, etc.)
        """
        repo_name = idea["name"]
        description = idea["description"]
        tech_stack = idea.get("tech_stack", [])
        roadmap = idea.get("roadmap", [])
        self.logger.info(f"[CreatorAgent] Creating repository for {repo_name}")
        try:
            repo = self.github_service.create_repository(repo_name, description)
            self.logger.info(f"[CreatorAgent] Repo created: {repo.get('html_url')}")
            # Update monsterrr_state.json with new repo
            state_path = os.path.join(os.getcwd(), "monsterrr_state.json")
            state = {}
            if os.path.exists(state_path):
                with open(state_path, "r", encoding="utf-8") as f:
                    try:
                        state = json.load(f)
                    except Exception:
                        state = {}
            repos = state.get("repos", [])
            repo_entry = {
                "name": repo_name,
                "description": description,
                "tech_stack": tech_stack,
                "roadmap": roadmap,
                "url": repo.get('html_url', '')
            }
            repos.append(repo_entry)
            state["repos"] = repos
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            self.logger.error(f"[CreatorAgent] Error creating repo: {e}")
            return
        try:
            self._scaffold_files(repo_name, description, roadmap, tech_stack)
        except Exception as e:
            self.logger.error(f"[CreatorAgent] Error scaffolding files: {e}")
        try:
            self._open_starter_issues(repo_name, roadmap)
        except Exception as e:
            self.logger.error(f"[CreatorAgent] Error opening starter issues: {e}")

    def _scaffold_files(self, repo_name: str, description: str, roadmap: list, tech_stack: list):
        """Create README.md, LICENSE, .gitignore, main.py, and CI config."""
        readme = f"# {repo_name}\n\n{description}\n\n## Tech Stack\n" + "\n".join([f"- {tech}" for tech in tech_stack]) + "\n\n## Roadmap\n" + "\n".join([f"- {step}" for step in roadmap])
        license_text = self._get_mit_license()
        gitignore = self._get_python_gitignore()
        main_py = f'# Entry point for the project\n\nif __name__ == "__main__":\n    print("Hello from {repo_name}")\n'
        ci_yaml = self._get_github_actions_yaml()
        files = {
            "README.md": readme,
            "LICENSE": license_text,
            ".gitignore": gitignore,
            f"{repo_name}/main.py": main_py,
            ".github/workflows/ci.yml": ci_yaml,
        }
        for path, content in files.items():
            try:
                self.github_service.create_or_update_file(repo_name, path, content, commit_message=f"Add {path}")
                self.logger.info(f"[CreatorAgent] Added {path}")
            except Exception as e:
                self.logger.error(f"[CreatorAgent] Error adding {path}: {e}")
            readme = f"# {repo_name}\n\n{description}\n\n## Tech Stack\n" + "\n".join([f"- {tech}" for tech in tech_stack]) + "\n\n## Roadmap\n" + "\n".join([f"- {step}" for step in roadmap])
            license_text = self._get_mit_license()
            gitignore = self._get_python_gitignore()
            main_py = f'# Entry point for the project\n\nif __name__ == "__main__":\n    print("Hello from {repo_name}")\n'
            ci_yaml = self._get_github_actions_yaml()
            files = {
                "README.md": readme,
                "LICENSE": license_text,
                ".gitignore": gitignore,
                f"{repo_name}/main.py": main_py,
                ".github/workflows/ci.yml": ci_yaml,
            }
            for path, content in files.items():
                try:
                    self.github_service.create_or_update_file(repo_name, path, content, commit_message=f"Add {path}")
                    self.logger.info(f"[CreatorAgent] Added {path}")
                except Exception as e:
                    self.logger.error(f"[CreatorAgent] Error adding {path}: {e}")

    def _open_starter_issues(self, repo: str, roadmap: list):
        """Open 'good first issues' based on roadmap."""
        for item in roadmap:
            try:
                self.github_service.create_issue(repo, title=f"[good first issue] {item}", body="Auto-generated by Monsterrr.", labels=["good first issue"])
                self.logger.info(f"[CreatorAgent] Opened issue: {item}")
            except Exception as e:
                self.logger.error(f"[CreatorAgent] Error opening issue for {item}: {e}")

    def _get_mit_license(self) -> str:
        """Return MIT license text."""
        return (
            "MIT License\n\nCopyright (c) 2025 ni-sh-a-char\n\nPermission is hereby granted, free of charge, to any person obtaining a copy "
            "of this software and associated documentation files (the \"Software\"), to deal in the Software without "
            "restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, "
            "and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to "
            "the following conditions:\n\nTHE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED."
        )

    def _get_python_gitignore(self) -> str:
        """Return a standard Python .gitignore."""
        return (
            "__pycache__/\n*.py[cod]\n*.env\n.venv/\n.env/\n.DS_Store\n*.log\n*.sqlite3\n" 
            "# Byte-compiled / optimized / DLL files\n__pycache__/\n*.py[cod]\n*$py.class\n" 
            "# Distribution / packaging\nbuild/\ndist/\n.eggs/\n*.egg-info/\n" 
            "# VSCode\n.vscode/\n"
        )

    def _get_github_actions_yaml(self) -> str:
        """Return a basic GitHub Actions CI config for Python."""
        return (
            "name: CI\n\non: [push, pull_request]\njobs:\n  build:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v3\n"
            "      - name: Set up Python\n        uses: actions/setup-python@v4\n        with:\n          python-version: '3.11'\n"
            "      - name: Install dependencies\n        run: |\n          python -m pip install --upgrade pip\n          pip install -r requirements.txt\n"
            "      - name: Run tests\n        run: |\n          pytest\n"
        )

if __name__ == "__main__":
    import logging
    import os
    from dotenv import load_dotenv
    load_dotenv()
    from services.github_service import GitHubService
    from services.groq_service import GroqService
    from utils.logger import setup_logger
    from agents.idea_agent import IdeaGeneratorAgent
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
    idea_agent = IdeaGeneratorAgent(groq, logger)
    agent = CreatorAgent(github, logger)
    # Always use AI-generated idea
    ideas = idea_agent.fetch_and_rank_ideas(top_n=1)
    if ideas:
        agent.create_repository(ideas[0])
