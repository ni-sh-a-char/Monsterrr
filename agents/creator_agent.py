from typing import Dict, Any
import os
import json
from datetime import datetime, timezone, timedelta
IST = timezone(timedelta(hours=5, minutes=30))


class CreatorAgent:
    """
    Enhanced agent for creating new repositories and scaffolding projects.
    Uses github_service to create repo, scaffold files, commit, and open starter issues.
    Now includes superhuman decision-making capabilities.
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
        Enhanced repository creation with superhuman decision-making capabilities.
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
        
        # Superhuman decision-making for repository creation
        repo_name = idea["name"]
        description = idea["description"]
        tech_stack = idea.get("tech_stack", [])
        roadmap = idea.get("roadmap", [])
        
        # Determine repository visibility using enhanced logic
        project_type = self._determine_project_type(idea)
        audience = self._determine_audience(idea)
        is_private = self.github_service.determine_repo_visibility(repo_name, project_type, audience)
        
        self.logger.info(f"[CreatorAgent] Creating {'' if is_private else 'public'} repository for {repo_name} (type: {project_type}, audience: {audience})")
        
        try:
            repo = self.github_service.create_repository(repo_name, description, private=is_private)
            self.logger.info(f"[CreatorAgent] Repo created: {repo.get('html_url')}")
            repo_entry = {
                "name": repo_name,
                "description": description,
                "tech_stack": tech_stack,
                "roadmap": roadmap,
                "url": repo.get('html_url', ''),
                "created_at": datetime.now().isoformat(),
                "visibility": "private" if is_private else "public",
                "project_type": project_type,
                "audience": audience
            }
            repos.append(repo_entry)
            state["repos"] = repos
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            self.logger.error(f"[CreatorAgent] Error creating repo: {e}")
            return
            
        try:
            # Create project board for tracking
            project_board = self.github_service.create_project_board(
                repo_name, 
                f"{repo_name} Development", 
                f"Project board for tracking development of {repo_name}"
            )
            self.logger.info(f"[CreatorAgent] Created project board for {repo_name}")
            
            # Add roadmap items to project board
            for i, step in enumerate(roadmap[:10]):  # Limit to first 10 steps
                self.github_service.add_item_to_project_board(
                    repo_name,
                    project_board["number"],
                    f"Roadmap Step {i+1}: {step}",
                    f"Implementation of roadmap step: {step}",
                    "To Do"
                )
            
            # Update state with project board info
            state["project_boards"] = state.get("project_boards", [])
            state["project_boards"].append({
                "repo": repo_name,
                "project_issue_number": project_board["number"],
                "url": project_board["html_url"] if "html_url" in project_board else f"{repo.get('html_url', '')}/issues/{project_board['number']}"
            })
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            self.logger.error(f"[CreatorAgent] Error creating project board: {e}")
            
        try:
            self._scaffold_complete_project(repo_name, description, roadmap, tech_stack, idea)
        except Exception as e:
            self.logger.error(f"[CreatorAgent] Error scaffolding files: {e}")
            
        try:
            self._open_starter_issues(repo_name, roadmap, project_board["number"] if "number" in locals() else None)
        except Exception as e:
            self.logger.error(f"[CreatorAgent] Error opening starter issues: {e}")

    def _determine_project_type(self, idea: Dict[str, Any]) -> str:
        """Determine the project type based on idea characteristics."""
        description = idea.get("description", "").lower()
        tech_stack = [tech.lower() for tech in idea.get("tech_stack", [])]
        roadmap = [step.lower() for step in idea.get("roadmap", [])]
        
        # Check for security-related keywords
        if any(keyword in description for keyword in ["security", "auth", "authentication", "encryption", "secure"]):
            return "security"
        
        # Check for research/experimental keywords
        if any(keyword in description for keyword in ["research", "experiment", "prototype", "proof of concept", "poc"]):
            return "experiment"
        
        # Check for template keywords
        if any(keyword in description for keyword in ["template", "boilerplate", "starter", "skeleton"]):
            return "template"
        
        # Check for demo keywords
        if any(keyword in description for keyword in ["demo", "example", "sample", "tutorial"]):
            return "demo"
        
        # Check for production keywords
        if any(keyword in description for keyword in ["production", "enterprise", "scalable", "robust"]):
            return "production"
        
        # Default to research for new projects
        return "research"

    def _determine_audience(self, idea: Dict[str, Any]) -> str:
        """Determine the intended audience for the project."""
        description = idea.get("description", "").lower()
        
        # Check for internal/confidential keywords
        if any(keyword in description for keyword in ["internal", "confidential", "private", "proprietary"]):
            return "confidential"
        
        # Check for team/organization keywords
        if any(keyword in description for keyword in ["team", "organization", "company", "enterprise"]):
            return "internal"
        
        # Default to general audience
        return "general"

    def _scaffold_complete_project(self, repo_name: str, description: str, roadmap: list, tech_stack: list, idea: Dict[str, Any]):
        """
        Scaffold a complete project with real, runnable code.
        """
        self.logger.info(f"[CreatorAgent] Scaffolding complete project for {repo_name}")
        
        try:
            # Create src directory structure
            src_code = self._generate_source_code(repo_name, tech_stack, idea)
            self.github_service.create_or_update_file(
                repo_name, 
                "src/main.py", 
                src_code, 
                f"Add main application code for {repo_name}"
            )
            
            # Create requirements.txt
            requirements = self._generate_requirements(tech_stack)
            self.github_service.create_or_update_file(
                repo_name, 
                "requirements.txt", 
                requirements, 
                "Add project dependencies"
            )
            
            # Create README.md
            readme = self._generate_readme(repo_name, description, tech_stack, roadmap)
            self.github_service.create_or_update_file(
                repo_name, 
                "README.md", 
                readme, 
                "Add project documentation"
            )
            
            # Create tests
            test_code = self._generate_test_code(repo_name, tech_stack)
            self.github_service.create_or_update_file(
                repo_name, 
                "tests/test_main.py", 
                test_code, 
                "Add initial tests"
            )
            
            # Create docs
            docs_content = self._generate_docs(repo_name, description, tech_stack, roadmap)
            self.github_service.create_or_update_file(
                repo_name, 
                "docs/index.md", 
                docs_content, 
                "Add documentation"
            )
            
            # Create .gitignore
            gitignore_content = """# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# C extensions
*.so

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# PyInstaller
#  Usually these files are written by a python script from a template
#  before PyInstaller builds the exe, so as to inject date/other infos into it.
*.manifest
*.spec

# Installer logs
pip-log.txt
pip-delete-this-directory.txt

# Unit test / coverage reports
htmlcov/
.tox/
.nox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
.hypothesis/
.pytest_cache/

# Translations
*.mo
*.pot

# Django stuff:
*.log
local_settings.py
db.sqlite3
db.sqlite3-journal

# Flask stuff:
instance/
.webassets-cache

# Scrapy stuff:
.scrapy

# Sphinx documentation
docs/_build/

# PyBuilder
target/

# Jupyter Notebook
.ipynb_checkpoints

# IPython
profile_default/
ipython_config.py

# pyenv
.python-version

# pipenv
#   According to pypa/pipenv#598, it is recommended to include Pipfile.lock in version control.
#   However, in case of collaboration, if having platform-specific dependencies or dependencies
#   having no cross-platform support, pipenv may install dependencies that don't work, or not
#   install all needed dependencies.
#Pipfile.lock

# celery beat schedule file
celerybeat-schedule

# SageMath parsed files
*.sage.py

# Environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# Spyder project settings
.spyderproject
.spyproject

# Rope project settings
.ropeproject
"""
            self.github_service.create_or_update_file(
                repo_name, 
                ".gitignore", 
                gitignore_content, 
                "Add gitignore"
            )
            
            # Create a basic CI workflow
            workflow_content = """name: CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, '3.10', '3.11']

    steps:
    - uses: actions/checkout@v3
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    - name: Test with pytest
      run: |
        pytest
"""
            self.github_service.create_or_update_file(
                repo_name, 
                ".github/workflows/ci.yml", 
                workflow_content, 
                "Add CI workflow"
            )
            
            # Create CONTRIBUTING.md
            contributing_content = f"""# Contributing to {repo_name}

Thank you for your interest in contributing to {repo_name}! We welcome contributions from the community.

## Getting Started

1. Fork the repository
2. Create a new branch for your feature or bug fix
3. Make your changes
4. Write tests for your changes
5. Ensure all tests pass
6. Submit a pull request

## Code Style

Please follow the existing code style in the project. We use PEP 8 for Python code.

## Reporting Issues

Please use the GitHub issue tracker to report bugs or suggest features.

## Pull Request Process

1. Ensure any install or build dependencies are removed before the end of the layer when doing a build.
2. Update the README.md with details of changes to the interface, this includes new environment variables, exposed ports, useful file locations and container parameters.
3. Increase the version numbers in any examples files and the README.md to the new version that this Pull Request would represent.
4. You may merge the Pull Request in once you have the sign-off of two other developers, or if you do not have permission to do that, you may request the second reviewer to merge it for you.

## Code of Conduct

This project adheres to a Code of Conduct. By participating, you are expected to uphold this code.
"""
            self.github_service.create_or_update_file(
                repo_name, 
                "CONTRIBUTING.md", 
                contributing_content, 
                "Add contributing guidelines"
            )
            
            # Create CODE_OF_CONDUCT.md
            coc_content = "# Code of Conduct\n\n## Our Pledge\n\nIn the interest of fostering an open and welcoming environment, we as contributors and maintainers pledge to making participation in our project and our community a harassment-free experience for everyone, regardless of age, body size, disability, ethnicity, gender identity and expression, level of experience, nationality, personal appearance, race, religion, or sexual identity and orientation.\n\n## Our Standards\n\nExamples of behavior that contributes to creating a positive environment include:\n\n* Using welcoming and inclusive language\n* Being respectful of differing viewpoints and experiences\n* Gracefully accepting constructive criticism\n* Focusing on what is best for the community\n* Showing empathy towards other community members\n\nExamples of unacceptable behavior by participants include:\n\n* The use of sexualized language or imagery and unwelcome sexual attention or advances\n* Trolling, insulting/derogatory comments, and personal or political attacks\n* Public or private harassment\n* Publishing others' private information, such as a physical or electronic address, without explicit permission\n* Other conduct which could reasonably be considered inappropriate in a professional setting\n\n## Our Responsibilities\n\nProject maintainers are responsible for clarifying the standards of acceptable behavior and are expected to take appropriate and fair corrective action in response to any instances of unacceptable behavior.\n\nProject maintainers have the right and responsibility to remove, edit, or reject comments, commits, code, wiki edits, issues, and other contributions that are not aligned to this Code of Conduct, or to ban temporarily or permanently any contributor for other behaviors that they deem inappropriate, threatening, offensive, or harmful.\n\n## Scope\n\nThis Code of Conduct applies both within project spaces and in public spaces when an individual is representing the project or its community. Examples of representing a project or community include using an official project e-mail address, posting via an official social media account, or acting as an appointed representative at an online or offline event. Representation of a project may be further defined and clarified by project maintainers.\n\n## Enforcement\n\nInstances of abusive, harassing, or otherwise unacceptable behavior may be reported by contacting the project team. All complaints will be reviewed and investigated and will result in a response that is deemed necessary and appropriate to the circumstances. The project team is obligated to maintain confidentiality with regard to the reporter of an incident. Further details of specific enforcement policies may be posted separately.\n\nProject maintainers who do not follow or enforce the Code of Conduct in good faith may face temporary or permanent repercussions as determined by other members of the project's leadership.\n\n## Attribution\n\nThis Code of Conduct is adapted from the [Contributor Covenant][homepage], version 1.4, available at [http://contributor-covenant.org/version/1/4][version]\n\n[homepage]: http://contributor-covenant.org\n[version]: http://contributor-covenant.org/version/1/4/\n"
            self.github_service.create_or_update_file(
                repo_name, 
                "CODE_OF_CONDUCT.md", 
                coc_content, 
                "Add code of conduct"
            )
            
            self.logger.info(f"[CreatorAgent] Successfully scaffolded complete project for {repo_name}")
            
        except Exception as e:
            self.logger.error(f"[CreatorAgent] Error scaffolding complete project for {repo_name}: {e}")

    def _open_starter_issues(self, repo_name: str, roadmap: list, project_board_number: int = None):
        """Open starter issues based on roadmap and add them to project board."""
        try:
            # Create issues for roadmap items
            for i, step in enumerate(roadmap[:5]):  # Limit to first 5 steps
                issue_title = f"[feature] {step}"
                issue_body = f"""## Feature Description

Implement the following roadmap item:
{step}

## Implementation Steps

1. Plan the implementation
2. Write tests
3. Implement the feature
4. Document the changes
5. Submit a pull request

## Acceptance Criteria

- [ ] Feature is implemented
- [ ] Tests are passing
- [ ] Documentation is updated
- [ ] Code follows project standards
"""
                issue = self.github_service.create_issue(
                    repo_name, 
                    title=issue_title, 
                    body=issue_body, 
                    labels=["enhancement", "good first issue", "roadmap"]
                )
                
                # Add to project board if available
                if project_board_number:
                    try:
                        self.github_service.add_item_to_project_board(
                            repo_name,
                            project_board_number,
                            issue_title,
                            f"Implementation of: {step}",
                            "To Do"
                        )
                    except Exception as e:
                        self.logger.warning(f"[CreatorAgent] Could not add issue to project board: {e}")
            
            # Add some general issues
            general_issues = [
                {
                    "title": "[docs] Improve documentation",
                    "body": "Enhance the existing documentation with more examples and better explanations.",
                    "labels": ["documentation"]
                },
                {
                    "title": "[test] Add more test coverage",
                    "body": "Increase test coverage to at least 80% for all modules.",
                    "labels": ["testing"]
                },
                {
                    "title": "[refactor] Code quality improvements",
                    "body": "Review the codebase for potential improvements in structure, performance, and maintainability.",
                    "labels": ["refactoring"]
                },
                {
                    "title": "[security] Security audit",
                    "body": "Perform a security audit of the codebase and dependencies.",
                    "labels": ["security"]
                },
                {
                    "title": "[performance] Performance optimization",
                    "body": "Identify and optimize performance bottlenecks in the application.",
                    "labels": ["performance"]
                }
            ]
            
            for issue in general_issues:
                created_issue = self.github_service.create_issue(
                    repo_name,
                    title=issue["title"],
                    body=issue["body"],
                    labels=issue["labels"]
                )
                
                # Add to project board if available
                if project_board_number:
                    try:
                        self.github_service.add_item_to_project_board(
                            repo_name,
                            project_board_number,
                            issue["title"],
                            issue["body"],
                            "To Do"
                        )
                    except Exception as e:
                        self.logger.warning(f"[CreatorAgent] Could not add issue to project board: {e}")
                
            self.logger.info(f"[CreatorAgent] Opened starter issues for {repo_name}")
            
        except Exception as e:
            self.logger.error(f"[CreatorAgent] Error opening starter issues for {repo_name}: {e}")

    def _generate_source_code(self, repo_name: str, tech_stack: list, idea: Dict[str, Any]) -> str:
        """Generate source code based on tech stack and idea."""
        if "FastAPI" in tech_stack:
            return f'''"""
{repo_name} - {idea.get("description", "Auto-generated project")}
"""

from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import uvicorn

app = FastAPI(title="{repo_name}", description="{idea.get("description", "Auto-generated project")}")

class Item(BaseModel):
    id: int
    name: str
    description: str = None

# In-memory storage
items: List[Item] = []

@app.get("/")
async def root():
    return {{"message": "Welcome to {repo_name} API"}}

@app.get("/items/", response_model=List[Item])
async def get_items():
    return items

@app.get("/items/{{item_id}}", response_model=Item)
async def get_item(item_id: int):
    for item in items:
        if item.id == item_id:
            return item
    return {{"error": "Item not found"}}

@app.post("/items/", response_model=Item)
async def create_item(item: Item):
    items.append(item)
    return item

@app.put("/items/{{item_id}}", response_model=Item)
async def update_item(item_id: int, updated_item: Item):
    for i, item in enumerate(items):
        if item.id == item_id:
            items[i] = updated_item
            return updated_item
    return {{"error": "Item not found"}}

@app.delete("/items/{{item_id}}")
async def delete_item(item_id: int):
    for i, item in enumerate(items):
        if item.id == item_id:
            items.pop(i)
            return {{"message": "Item deleted"}}
    return {{"error": "Item not found"}}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''
        elif "Flask" in tech_stack:
            return f'''"""
{repo_name} - {idea.get("description", "Auto-generated project")}
"""

from flask import Flask, jsonify, request
from typing import List

app = Flask(__name__)

class Item:
    def __init__(self, id: int, name: str, description: str = None):
        self.id = id
        self.name = name
        self.description = description

# In-memory storage
items: List[Item] = []

@app.route("/")
def root():
    return jsonify({{"message": "Welcome to {repo_name} API"}})

@app.route("/items/", methods=["GET"])
def get_items():
    return jsonify([{{"id": item.id, "name": item.name, "description": item.description}} for item in items])

@app.route("/items/<int:item_id>", methods=["GET"])
def get_item(item_id: int):
    for item in items:
        if item.id == item_id:
            return jsonify({{"id": item.id, "name": item.name, "description": item.description}})
    return jsonify({{"error": "Item not found"}}), 404

@app.route("/items/", methods=["POST"])
def create_item():
    data = request.get_json()
    item = Item(data["id"], data["name"], data.get("description"))
    items.append(item)
    return jsonify({{"id": item.id, "name": item.name, "description": item.description}}), 201

@app.route("/items/<int:item_id>", methods=["PUT"])
def update_item(item_id: int):
    data = request.get_json()
    for i, item in enumerate(items):
        if item.id == item_id:
            items[i] = Item(data["id"], data["name"], data.get("description"))
            return jsonify({{"id": items[i].id, "name": items[i].name, "description": items[i].description}})
    return jsonify({{"error": "Item not found"}}), 404

@app.route("/items/<int:item_id>", methods=["DELETE"])
def delete_item(item_id: int):
    for i, item in enumerate(items):
        if item.id == item_id:
            items.pop(i)
            return jsonify({{"message": "Item deleted"}})
    return jsonify({{"error": "Item not found"}}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
'''
        else:
            # Default to a simple Python script
            return f'''"""
{repo_name} - {idea.get("description", "Auto-generated project")}
"""

def main():
    print("Welcome to {repo_name}!")
    print("{idea.get("description", "Auto-generated project")}")
    
    # TODO: Implement your project logic here
    print("This is a placeholder. Implement your logic here.")

if __name__ == "__main__":
    main()
'''

    def _generate_requirements(self, tech_stack: list) -> str:
        """Generate requirements.txt based on tech stack."""
        requirements = ["requests"]
        
        if "FastAPI" in tech_stack:
            requirements.extend(["fastapi", "uvicorn[standard]", "pydantic"])
        if "Flask" in tech_stack:
            requirements.append("flask")
        if "Django" in tech_stack:
            requirements.append("django")
            
        requirements.extend(["pytest", "httpx"])
        
        return "\n".join(requirements)

    def _generate_readme(self, repo_name: str, description: str, tech_stack: list, roadmap: list) -> str:
        """Generate README.md content."""
        tech_list = "\n".join([f"- {tech}" for tech in tech_stack]) if tech_stack else "None specified"
        roadmap_list = "\n".join([f"- {step}" for step in roadmap]) if roadmap else "To be determined"
        
        return f'''# {repo_name}

{description}

## Tech Stack
{tech_list}

## Features
- RESTful API endpoints
- Data persistence (in-memory for demo)
- Comprehensive test suite
- CI/CD pipeline
- Documentation

## Roadmap
{roadmap_list}

## Installation

```bash
pip install -r requirements.txt
```

## Usage

For FastAPI:
```bash
uvicorn src.main:app --reload
```

For Flask:
```bash
python src/main.py
```

For basic Python script:
```bash
python src/main.py
```

## API Endpoints

- `GET /` - Welcome message
- `GET /items/` - Get all items
- `GET /items/{{id}}` - Get specific item
- `POST /items/` - Create new item
- `PUT /items/{{id}}` - Update existing item
- `DELETE /items/{{id}}` - Delete item

## Testing

```bash
pytest
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a pull request

## License

MIT
'''

    def _generate_test_code(self, repo_name: str, tech_stack: list) -> str:
        """Generate test code."""
        if "FastAPI" in tech_stack:
            return f'''"""
Tests for {repo_name}
"""

from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()

def test_create_and_get_item():
    # Create an item
    item_data = {{"id": 1, "name": "Test Item", "description": "A test item"}}
    response = client.post("/items/", json=item_data)
    assert response.status_code == 200
    assert response.json()["id"] == 1
    
    # Get the item
    response = client.get("/items/1")
    assert response.status_code == 200
    assert response.json()["name"] == "Test Item"

def test_update_item():
    # Update the item
    updated_data = {{"id": 1, "name": "Updated Item", "description": "An updated item"}}
    response = client.put("/items/1", json=updated_data)
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Item"

def test_delete_item():
    # Delete the item
    response = client.delete("/items/1")
    assert response.status_code == 200
    assert "message" in response.json()
    
    # Try to get the deleted item
    response = client.get("/items/1")
    assert response.status_code == 404
'''
        elif "Flask" in tech_stack:
            return f'''"""
Tests for {repo_name}
"""

import unittest
import json
from src.main import app

class {repo_name.replace('-', '').replace('_', '').title()}TestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_root(self):
        result = self.app.get('/')
        self.assertEqual(result.status_code, 200)
        data = json.loads(result.data)
        self.assertIn('message', data)

    def test_create_and_get_item(self):
        # Create an item
        item_data = {{"id": 1, "name": "Test Item", "description": "A test item"}}
        result = self.app.post('/items/', 
                              data=json.dumps(item_data),
                              content_type='application/json')
        self.assertEqual(result.status_code, 201)
        
        # Get the item
        result = self.app.get('/items/1')
        self.assertEqual(result.status_code, 200)
        data = json.loads(result.data)
        self.assertEqual(data['name'], 'Test Item')

    def test_update_item(self):
        # Update the item
        updated_data = {{"id": 1, "name": "Updated Item", "description": "An updated item"}}
        result = self.app.put('/items/1',
                             data=json.dumps(updated_data),
                             content_type='application/json')
        self.assertEqual(result.status_code, 200)
        data = json.loads(result.data)
        self.assertEqual(data['name'], 'Updated Item')

    def test_delete_item(self):
        # Delete the item
        result = self.app.delete('/items/1')
        self.assertEqual(result.status_code, 200)
        data = json.loads(result.data)
        self.assertIn('message', data)

if __name__ == '__main__':
    unittest.main()
'''
        else:
            return f'''"""
Tests for {repo_name}
"""

import unittest
from src.main import main

class Test{repo_name.replace('-', '').replace('_', '').title()}(unittest.TestCase):
    def test_main_function(self):
        # This is a placeholder test
        # In a real implementation, you would test actual functions
        self.assertTrue(True)

if __name__ == '__main__':
    unittest.main()
'''

    def _generate_docs(self, repo_name: str, description: str, tech_stack: list, roadmap: list) -> str:
        """Generate documentation."""
        tech_stack_str = "\n".join([f"- {tech}" for tech in tech_stack]) if tech_stack else "None specified"
        roadmap_str = "\n".join([f"- {step}" for step in roadmap]) if roadmap else "To be determined"
        return f"""# {repo_name} Documentation

## Overview

{description}

## Tech Stack

{tech_stack_str}

## Project Structure

```
{repo_name}/
├── src/
│   └── main.py          # Main application code
├── tests/
│   └── test_main.py     # Test suite
├── docs/
│   └── index.md         # Documentation
├── requirements.txt     # Python dependencies
├── README.md            # Project overview
└── .gitignore           # Git ignore rules
```

## API Reference

### Root Endpoint
- **URL**: `/`
- **Method**: `GET`
- **Description**: Returns a welcome message

### Items Endpoints
- **URL**: `/items/`
- **Methods**: `GET`, `POST`
- **Description**: Manage collection of items

- **URL**: `/items/{{id}}`
- **Methods**: `GET`, `PUT`, `DELETE`
- **Description**: Manage individual items

## Installation

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run the application: `python src/main.py`

## Testing

Run the test suite with: `pytest`

## Roadmap

{roadmap_str}

## Contributing

Please read CONTRIBUTING.md for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License.
"""

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
                tech_stack_text = chr(10).join([f"- {tech}" for tech in tech_stack])
                roadmap_text = chr(10).join([f"- {step}" for step in roadmap])
                doc_text = f"""# {repo_name} Documentation

{description}

## Tech Stack
{tech_stack_text}

## Project Idea
This project aims to solve important problems in the development space.

## Features
- Core functionality implementation
- RESTful API endpoints
- Comprehensive test suite
- Detailed documentation

## Roadmap
{roadmap_text}

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

    def _load_state(self):
        """Load agent state from file."""
        try:
            if os.path.exists("monsterrr_state.json"):
                with open("monsterrr_state.json", "r") as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading state: {e}")
        return {}

    def _save_state(self, state):
        """Save agent state to file."""
        try:
            with open("monsterrr_state.json", "w") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving state: {e}")

    def _load_state(self):
        """Load agent state from file."""
        try:
            if os.path.exists("monsterrr_state.json"):
                with open("monsterrr_state.json", "r") as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading state: {e}")
        return {}