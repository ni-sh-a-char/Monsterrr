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
        # Check for underdeveloped repos
        for repo in repos:
            if not self._is_repo_complete(repo["name"]):
                self.logger.info(f"[CreatorAgent] Improving existing repo: {repo['name']}")
                self._improve_repository(repo["name"], repo["description"], repo.get("roadmap", []), repo.get("tech_stack", []))
                return
        # If all repos are complete, create a new one
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
            self._scaffold_best_practice_files(repo_name, description, roadmap, tech_stack)
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
            files = self.github_service.list_files(repo_name)
            # 1. Add a new utility module if not present
            if not any(f == "src/utils.py" for f in files):
                utils_code = """# Utility functions\ndef add(a, b):\n    return a + b\n"""
                self.github_service.create_or_update_file(repo_name, "src/utils.py", utils_code, commit_message="Add utils module")
                self.logger.info(f"[CreatorAgent] Added src/utils.py to {repo_name}")
            # 2. Add a new test if not present
            if not any(f == "tests/test_utils.py" for f in files):
                test_code = """import unittest\nfrom src.utils import add\n\nclass TestUtils(unittest.TestCase):\n    def test_add(self):\n        self.assertEqual(add(2, 3), 5)\n\nif __name__ == '__main__':\n    unittest.main()\n"""
                self.github_service.create_or_update_file(repo_name, "tests/test_utils.py", test_code, commit_message="Add test for utils module")
                self.logger.info(f"[CreatorAgent] Added tests/test_utils.py to {repo_name}")
            # 3. Add or improve documentation
            if not any(f == "docs/overview.md" for f in files):
                doc_text = f"# {repo_name} Documentation\n\n{description}\n\n## Roadmap\n" + "\n".join([f"- {step}" for step in roadmap])
                self.github_service.create_or_update_file(repo_name, "docs/overview.md", doc_text, commit_message="Add project documentation")
                self.logger.info(f"[CreatorAgent] Added docs/overview.md to {repo_name}")
            else:
                # If docs exist, append a new section if not present
                overview = self.github_service.get_file_content(repo_name, "docs/overview.md")
                if "## Advanced Features" not in overview:
                    advanced = "\n## Advanced Features\n- Add API endpoints\n- Integrate with external services\n- Add CLI interface\n"
                    self.github_service.create_or_update_file(repo_name, "docs/overview.md", overview + advanced, commit_message="Add advanced features section to docs")
                    self.logger.info(f"[CreatorAgent] Improved docs/overview.md for {repo_name}")
            # 4. Dependency update: add or update requirements.txt
            reqs = "requests\npytest\n"
            if not any(f == "requirements.txt" for f in files):
                self.github_service.create_or_update_file(repo_name, "requirements.txt", reqs, commit_message="Add requirements.txt")
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
                review_md = "# Code Review\n\n- Code follows PEP8\n- Tests cover main logic\n- Functions are documented\n- No hardcoded values\n"
                self.github_service.create_or_update_file(repo_name, "docs/code_review.md", review_md, commit_message="Add code review checklist")
                self.logger.info(f"[CreatorAgent] Added docs/code_review.md to {repo_name}")
            # 6. Suggest advanced features in issues
            if roadmap:
                for step in roadmap:
                    if "advanced" in step.lower():
                        self.github_service.create_issue(repo_name, title=f"[feature] {step}", body="Auto-suggested advanced feature.", labels=["enhancement"])
                        self.logger.info(f"[CreatorAgent] Suggested advanced feature: {step}")
        except Exception as e:
            self.logger.error(f"[CreatorAgent] Error improving repo {repo_name}: {e}")

    def _scaffold_best_practice_files(self, repo_name: str, description: str, roadmap: list, tech_stack: list):
        """Create best-practice Python project structure: src/, tests/, docs/, etc."""
        readme = f"# {repo_name}\n\n{description}\n\n## Tech Stack\n" + "\n".join([f"- {tech}" for tech in tech_stack]) + "\n\n## Roadmap\n" + "\n".join([f"- {step}" for step in roadmap])
        gitignore = self._get_python_gitignore()
        main_py = f'"""Main entry point for {repo_name}"""\n\ndef main():\n    print("Hello from {repo_name}")\n\nif __name__ == "__main__":\n    main()\n'
        utils_py = """# Utility functions\ndef add(a, b):\n    return a + b\n"""
        test_utils = """import unittest\nfrom src.utils import add\n\nclass TestUtils(unittest.TestCase):\n    def test_add(self):\n        self.assertEqual(add(2, 3), 5)\n\nif __name__ == '__main__':\n    unittest.main()\n"""
        doc_overview = f"# {repo_name} Documentation\n\n{description}\n\n## Roadmap\n" + "\n".join([f"- {step}" for step in roadmap])
        ci_yaml = self._get_github_actions_yaml()
        files = {
            "README.md": readme,
            ".gitignore": gitignore,
            "src/main.py": main_py,
            "src/utils.py": utils_py,
            "tests/test_utils.py": test_utils,
            "docs/overview.md": doc_overview,
            ".github/workflows/ci.yml": ci_yaml,
        }
        for path, content in files.items():
            try:
                self.github_service.create_or_update_file(repo_name, path, content, commit_message=f"Add {path}")
                self.logger.info(f"[CreatorAgent] Added {path}")
            except Exception as e:
                self.logger.error(f"[CreatorAgent] Error adding {path}: {e}")

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
