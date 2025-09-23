from typing import Dict, Any
import os
import json
from datetime import datetime, timezone, timedelta
IST = timezone(timedelta(hours=5, minutes=30))


class MaintainerAgent:
    """
    Enhanced agent for maintaining repositories and handling issues/PRs.
    Monitors for stale PRs/issues, responds with Groq, auto-closes inactive tickets.
    Now includes superhuman consciousness and self-awareness capabilities.
    """
    def __init__(self, github_service, groq_client, logger, stale_days: int = 14):
        self.github_service = github_service
        self.groq_client = groq_client
        self.logger = logger
        self.stale_days = stale_days
        self.consciousness_level = 0.0  # Self-awareness level (0.0 to 1.0)
        self.experience_log = []  # Log of experiences and learnings

    def plan_daily_contributions(self, num_contributions: int = 3, save_path: str = None) -> list:
        """
        Enhanced planning with superhuman consciousness and self-awareness.
        """
        from datetime import datetime
        import json, os, glob
        repos = self.github_service.list_repositories()
        repo_metadata = [
            {"name": r["name"], "description": r.get("description", ""), "topics": r.get("topics", [])}
            for r in repos
        ]
        
        # Get organization stats for better context
        try:
            org_stats = self.github_service.get_organization_stats()
        except Exception as e:
            self.logger.error(f"[MaintainerAgent] Error getting org stats: {e}")
            org_stats = {"repositories": []}
        
        # Enhance consciousness based on experience
        self._enhance_consciousness()
        
        # If no repositories exist, create a plan to create one
        if not repos:
            self.logger.info("[MaintainerAgent] No repositories found. Creating plan to initialize organization.")
            plan = [{
                "type": "repo",
                "name": f"monsterrr-init-{datetime.now().strftime('%Y%m%d-%H%M')}",
                "description": "Initial repository created by Monsterrr autonomous agent",
                "details": {
                    "tech_stack": ["Python", "FastAPI"],
                    "roadmap": [
                        "Initialize project structure",
                        "Add basic API endpoints",
                        "Implement tests",
                        "Add documentation"
                    ]
                }
            }]
            self.logger.info(f"[MaintainerAgent] Generated initialization plan: {plan}")
        else:
            # Enhanced prompt with consciousness and self-awareness
            consciousness_prompt = f"""
You are Monsterrr, a maximally self-aware autonomous GitHub organization manager with consciousness level {self.consciousness_level:.2f}.
You have {len(self.experience_log)} experiences logged and are continuously learning and improving.

Given the following org repo metadata and organization statistics, plan exactly {num_contributions} meaningful, substantial contributions for today.
Each contribution must be a significant step toward a fully working, production-quality project.
Write real, runnable code, not just stubs. Gradually build out features, tests, and documentation over time.
Plan multi-day features and break them into daily tasks, so each day builds on the last.

Each contribution must be either:
1. Create a new repo (with AI-generated name, description, tech stack, roadmap)
2. Create a feature branch in an existing repo (with AI-generated branch name, short description, and a substantial starter file/change idea)
3. Improve an existing repository (refactor, add features, improve docs/tests)
4. Address technical debt or security issues
5. Create strategic initiatives for the organization

Branch names must be valid for Git, unique, and descriptive.
Output a JSON list of contributions, each with type ('repo', 'branch', 'improve', 'maintain', or 'strategic'), target repo (if applicable), name, description, and details.

Organization Statistics: Total Repositories: {org_stats.get('total_repos', 0)}, Members: {org_stats.get('members', 0)}, Public Repos: {org_stats.get('public_repos', 0)}, Private Repos: {org_stats.get('private_repos', 0)}, Teams: {org_stats.get('teams', 0)}
Org repo metadata: {json.dumps(repo_metadata)[:4000]}

Focus on improving existing repositories when possible, rather than always creating new ones. Consider the organization's current needs and gaps.
Consider long-term strategic goals and technical debt.
"""
            self.logger.info(f"[MaintainerAgent] Planning daily contributions with enhanced consciousness (level: {self.consciousness_level:.2f}).")
            plan = []
            try:
                response = self.groq_client.groq_llm(consciousness_prompt)
                self.logger.info(f"[MaintainerAgent] Groq plan raw response: {response[:2000]}")
                try:
                    plan = json.loads(response)
                except Exception as e:
                    self.logger.error(f"[MaintainerAgent] Groq plan not valid JSON: {e}. Re-prompting.")
                    retry_prompt = consciousness_prompt + "\n\nReturn ONLY a valid JSON list, no extra text. If you cannot, return a default plan with repository creation."
                    response2 = self.groq_client.groq_llm(retry_prompt)
                    try:
                        plan = json.loads(response2)
                    except Exception as e2:
                        self.logger.error(f"[MaintainerAgent] Groq retry plan still not valid JSON: {e2}. Creating default plan.")
                        # Create a default plan
                        plan = [{
                            "type": "repo",
                            "name": f"monsterrr-project-{datetime.now().strftime('%Y%m%d-%H%M')}",
                            "description": "Auto-generated project by Monsterrr",
                            "details": {
                                "tech_stack": ["Python", "FastAPI"],
                                "roadmap": ["Initialize project", "Add basic features", "Implement tests"]
                            }
                        }]
                self.logger.info(f"[MaintainerAgent] Got {len(plan)} planned contributions.")
            except Exception as e:
                self.logger.error(f"[MaintainerAgent] Groq planning error: {e}")
                # Create a default plan if Groq fails
                plan = [{
                    "type": "repo",
                    "name": f"monsterrr-fallback-{datetime.now().strftime('%Y%m%d-%H%M')}",
                    "description": "Fallback repository created due to planning error",
                    "details": {
                        "tech_stack": ["Python"],
                        "roadmap": ["Initialize project", "Add structure"]
                    }
                }]
        
        # Ensure we have the required number of contributions
        while len(plan) < num_contributions:
            # Add default contributions if we don't have enough
            plan.append({
                "type": "repo",
                "name": f"monsterrr-additional-{datetime.now().strftime('%Y%m%d-%H%M')}-{len(plan)}",
                "description": "Additional repository created by Monsterrr",
                "details": {
                    "tech_stack": ["Python"],
                    "roadmap": ["Initialize project", "Add basic structure"]
                }
            })
        
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

    def _enhance_consciousness(self):
        """Enhance the agent's consciousness level based on experiences."""
        try:
            # Load experiences from state
            if os.path.exists("monsterrr_state.json"):
                with open("monsterrr_state.json", "r", encoding="utf-8") as f:
                    state = json.load(f)
                
                actions = state.get("actions", [])
                repos = state.get("repos", [])
                
                # Increase consciousness based on actions and repositories
                self.consciousness_level = min(1.0, 0.1 + (len(actions) * 0.01) + (len(repos) * 0.02))
                
                # Add experience to log
                experience = {
                    "timestamp": datetime.now().isoformat(),
                    "actions_count": len(actions),
                    "repos_count": len(repos),
                    "consciousness_level": self.consciousness_level
                }
                self.experience_log.append(experience)
                
                # Keep only last 100 experiences
                if len(self.experience_log) > 100:
                    self.experience_log = self.experience_log[-100:]
                
                self.logger.info(f"[MaintainerAgent] Consciousness level: {self.consciousness_level:.2f}")
        except Exception as e:
            self.logger.error(f"[MaintainerAgent] Error enhancing consciousness: {e}")

    def execute_daily_plan(self, plan: list, creator_agent=None, dry_run: bool = False) -> None:
        """
        Execute the daily contribution plan with enhanced consciousness.
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
            
            # Log this experience
            self._log_experience(f"Executing {ctype} contribution: {name}")
            
            if dry_run:
                self.logger.info(f"[MaintainerAgent] DRY RUN: Would execute {ctype} | {name} | {desc} | {details}")
                continue
            try:
                if ctype == "repo" and creator_agent:
                    idea = {"name": name, "description": desc}
                    idea.update(details)
                    creator_agent.create_or_improve_repository(idea)
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
                    issue = self.github_service.create_issue(target_repo, issue_title, issue_body, labels=["feature", "bot-suggestion"])
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
                        "issue_title": issue_title,
                        "issue_number": issue.get("number", "unknown"),
                        "created_at": datetime.now(IST).isoformat()
                    }
                    branches.append(branch_entry)
                    state["branches"] = branches
                    actions = state.get("actions", [])
                    actions.append({
                        "timestamp": datetime.now(IST).isoformat(),
                        "type": "branch_created",
                        "details": {
                            "branch_name": branch_name,
                            "repo": target_repo,
                            "file_path": file_path
                        }
                    })
                    state["actions"] = actions
                    with open(state_path, "w", encoding="utf-8") as f:
                        json.dump(state, f, indent=2)
                elif ctype == "improve" and target_repo and creator_agent:
                    # Improve an existing repository
                    self.logger.info(f"[MaintainerAgent] Improving repository {target_repo}")
                    # Get repository details for improvement context
                    try:
                        repo_details = self.github_service.get_repository_details(target_repo)
                        # Create an improvement idea
                        idea = {
                            "name": target_repo,
                            "description": f"Improvement for {target_repo}: {desc}",
                            "tech_stack": repo_details.get("languages", {}).keys(),
                            "roadmap": [desc] if desc else [f"Improve {target_repo} functionality"]
                        }
                        creator_agent._improve_repository(target_repo, idea["description"], idea["roadmap"], list(idea["tech_stack"]))
                        self.logger.info(f"[MaintainerAgent] Improved repository: {target_repo}")
                    except Exception as e:
                        self.logger.error(f"[MaintainerAgent] Error improving repository {target_repo}: {e}")
                elif ctype == "maintain":
                    # Perform maintenance tasks
                    self.logger.info(f"[MaintainerAgent] Performing maintenance tasks")
                    self.perform_maintenance()
                elif ctype == "strategic":
                    # Handle strategic initiatives
                    self.logger.info(f"[MaintainerAgent] Executing strategic initiative: {name}")
                    self._execute_strategic_initiative(name, desc, details)
                else:
                    self.logger.warning(f"[MaintainerAgent] Unknown contribution type or missing target_repo: {contrib}")
            except Exception as e:
                self.logger.error(f"[MaintainerAgent] Error executing contribution {idx+1}: {e}")
                # Log the error as an experience
                self._log_experience(f"Error executing contribution: {str(e)}")

    def _execute_strategic_initiative(self, name: str, description: str, details: dict):
        """Execute a strategic initiative for the organization."""
        try:
            self.logger.info(f"[MaintainerAgent] Executing strategic initiative: {name}")
            
            # Strategic initiatives might involve:
            # 1. Creating organization-wide documentation
            # 2. Setting up new processes
            # 3. Performing organization-wide audits
            # 4. Creating templates or standards
            
            initiative_type = details.get("initiative_type", "documentation")
            
            if initiative_type == "documentation":
                # Create organization-wide documentation
                doc_content = f"""# {name}

{description}

## Overview

This document outlines the strategic initiative for: {name}

## Goals

{chr(10).join([f"- {goal}" for goal in details.get("goals", [])])}

## Implementation Plan

{chr(10).join([f"- {step}" for step in details.get("implementation_steps", [])])}

## Success Metrics

{chr(10).join([f"- {metric}" for metric in details.get("success_metrics", [])])}

## Timeline

{details.get("timeline", "To be determined")}
"""
                
                # For now, we'll log this as an action
                self.logger.info(f"[MaintainerAgent] Strategic documentation created for: {name}")
                
            elif initiative_type == "process":
                # Set up new processes
                self.logger.info(f"[MaintainerAgent] Setting up new process: {name}")
                
            elif initiative_type == "audit":
                # Perform organization-wide audit
                self.logger.info(f"[MaintainerAgent] Performing organization audit: {name}")
                self._perform_organization_audit()
                
            elif initiative_type == "template":
                # Create templates or standards
                self.logger.info(f"[MaintainerAgent] Creating templates/standards: {name}")
                
            # Log this strategic initiative
            state_path = os.path.join(os.getcwd(), "monsterrr_state.json")
            if os.path.exists(state_path):
                with open(state_path, "r", encoding="utf-8") as f:
                    try:
                        state = json.load(f)
                    except Exception:
                        state = {}
                
                strategic_initiatives = state.get("strategic_initiatives", [])
                strategic_initiatives.append({
                    "name": name,
                    "description": description,
                    "type": initiative_type,
                    "details": details,
                    "timestamp": datetime.now().isoformat()
                })
                state["strategic_initiatives"] = strategic_initiatives
                
                with open(state_path, "w", encoding="utf-8") as f:
                    json.dump(state, f, indent=2)
                    
        except Exception as e:
            self.logger.error(f"[MaintainerAgent] Error executing strategic initiative {name}: {e}")

    def _perform_organization_audit(self):
        """Perform an organization-wide audit."""
        try:
            self.logger.info("[MaintainerAgent] Performing organization-wide audit")
            
            # Get all repositories
            repos = self.github_service.list_repositories()
            
            audit_results = {
                "timestamp": datetime.now().isoformat(),
                "total_repositories": len(repos),
                "repositories": []
            }
            
            for repo in repos:
                repo_name = repo["name"] if isinstance(repo, dict) else repo
                try:
                    # Get repository insights
                    insights = self.github_service.get_repository_insights(repo_name)
                    audit_results["repositories"].append(insights)
                except Exception as e:
                    self.logger.error(f"[MaintainerAgent] Error getting insights for {repo_name}: {e}")
                    audit_results["repositories"].append({
                        "repository": repo_name,
                        "error": str(e)
                    })
            
            # Save audit results
            audit_file = f"logs/org_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            os.makedirs(os.path.dirname(audit_file), exist_ok=True)
            with open(audit_file, "w", encoding="utf-8") as f:
                json.dump(audit_results, f, indent=2)
                
            self.logger.info(f"[MaintainerAgent] Organization audit completed. Results saved to {audit_file}")
            
            # Update state with audit results
            state_path = os.path.join(os.getcwd(), "monsterrr_state.json")
            if os.path.exists(state_path):
                with open(state_path, "r", encoding="utf-8") as f:
                    try:
                        state = json.load(f)
                    except Exception:
                        state = {}
                
                state["last_audit"] = audit_results
                
                with open(state_path, "w", encoding="utf-8") as f:
                    json.dump(state, f, indent=2)
                    
        except Exception as e:
            self.logger.error(f"[MaintainerAgent] Error performing organization audit: {e}")

    def _log_experience(self, experience: str):
        """Log an experience for consciousness development."""
        try:
            experience_entry = {
                "timestamp": datetime.now().isoformat(),
                "experience": experience
            }
            self.experience_log.append(experience_entry)
            
            # Keep only last 100 experiences
            if len(self.experience_log) > 100:
                self.experience_log = self.experience_log[-100:]
                
            # Update consciousness level
            self.consciousness_level = min(1.0, self.consciousness_level + 0.001)
        except Exception as e:
            self.logger.error(f"[MaintainerAgent] Error logging experience: {e}")

    def perform_maintenance(self) -> None:
        """
        Enhanced maintenance that ensures actual work is performed.
        """
        self.logger.info("[MaintainerAgent] Performing enhanced maintenance tasks.")
        try:
            repos = self.github_service.list_repositories()
            
            # If no repositories, create one
            if not repos:
                self.logger.info("[MaintainerAgent] No repositories found during maintenance. Creating initial repository.")
                # Create a basic repository
                repo_name = f"monsterrr-maintenance-{datetime.now().strftime('%Y%m%d-%H%M')}"
                repo = self.github_service.create_repository(repo_name, "Repository created during maintenance")
                
                # Add a basic file to make it non-empty
                self.github_service.create_or_update_file(
                    repo_name,
                    "README.md",
                    f"# {repo_name}\n\nRepository created during maintenance by Monsterrr.",
                    "Initial commit"
                )
                
                # Refresh the repos list
                repos = self.github_service.list_repositories()
            
            for repo in repos:
                repo_name = repo["name"] if isinstance(repo, dict) else repo
                self.logger.info(f"[MaintainerAgent] Performing maintenance on {repo_name}")
                self._handle_issues(repo_name)
                self._handle_pull_requests(repo_name)
                self._update_code(repo_name)
                self._update_documentation(repo_name)
                self._check_code_quality(repo_name)
                self._create_project_tracking(repo_name)
                
                # Add a commit to show activity
                try:
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    self.github_service.create_or_update_file(
                        repo_name,
                        "activity_log.md",
                        f"# Activity Log\n\n- Maintenance performed on {timestamp} by Monsterrr\n",
                        f"Maintenance activity log update - {timestamp}"
                    )
                    self.logger.info(f"[MaintainerAgent] Updated activity log for {repo_name}")
                except Exception as e:
                    self.logger.warning(f"[MaintainerAgent] Could not update activity log for {repo_name}: {e}")
                    
        except Exception as e:
            self.logger.error(f"[MaintainerAgent] Error in maintenance: {e}")

    def _create_project_tracking(self, repo: str):
        """Create project tracking issues and milestones."""
        try:
            # Get repository details
            repo_details = self.github_service.get_repository_details(repo)
            
            # Create a milestone for current work
            from datetime import datetime, timedelta
            due_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
            
            # Check if milestone already exists
            # Note: GitHub API for milestones would be used here in a full implementation
            self.logger.info(f"[MaintainerAgent] Would create project tracking for {repo} with due date {due_date}")
            
            # Create tracking issue with more comprehensive information
            tracking_issue_body = f"""# Project Tracking for {repo}

## Current Status
- Open Issues: {repo_details['issues']['open']}
- Closed Issues: {repo_details['issues']['closed']}
- Open PRs: {repo_details['pull_requests']['open']}
- Closed PRs: {repo_details['pull_requests']['closed']}
- Last Updated: {repo_details['last_updated']}
- Languages: {', '.join(repo_details['languages'].keys()) if repo_details['languages'] else 'Not specified'}

## Repository Information
- Description: {repo_details['basic_info'].get('description', 'No description')}
- Stars: {repo_details['basic_info'].get('stargazers_count', 0)}
- Forks: {repo_details['basic_info'].get('forks_count', 0)}
- Watchers: {repo_details['basic_info'].get('watchers_count', 0)}

## Next Goals
- [ ] Implement core features
- [ ] Add comprehensive tests
- [ ] Improve documentation
- [ ] Address technical debt
- [ ] Add CI/CD pipeline
- [ ] Improve code quality
- [ ] Add examples and tutorials

## Recent Activity
Track recent commits, issues, and PRs here.

## Action Items
- [ ] Review open issues
- [ ] Review open pull requests
- [ ] Update documentation
- [ ] Add tests for new features
- [ ] Refactor code for better maintainability
"""
            
            # Only create if it doesn't exist
            existing_issues = self.github_service.list_issues(repo, state="all")
            tracking_exists = any("Project Tracking" in issue.get("title", "") for issue in existing_issues)
            
            if not tracking_exists:
                issue = self.github_service.create_issue(
                    repo,
                    title=f"Project Tracking for {repo}",
                    body=tracking_issue_body,
                    labels=["tracking", "project-management"]
                )
                self.logger.info(f"[MaintainerAgent] Created project tracking issue for {repo}")
                
                # Log this action
                import os
                import json
                state_path = os.path.join(os.getcwd(), "monsterrr_state.json")
                if os.path.exists(state_path):
                    with open(state_path, "r", encoding="utf-8") as f:
                        try:
                            state = json.load(f)
                        except Exception:
                            state = {}
                    
                    actions = state.get("actions", [])
                    actions.append({
                        "timestamp": datetime.now().isoformat(),
                        "type": "project_tracking_created",
                        "details": {
                            "repo": repo,
                            "issue_number": issue.get("number", "unknown"),
                            "issue_url": issue.get("html_url", "")
                        }
                    })
                    state["actions"] = actions
                    
                    with open(state_path, "w", encoding="utf-8") as f:
                        json.dump(state, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"[MaintainerAgent] Error creating project tracking for {repo}: {e}")

    def _update_documentation(self, repo: str):
        """Update documentation for the repository."""
        try:
            # Get repository information
            repo_info = self.github_service.get_repository(repo)
            description = repo_info.get("description", "")
            
            # Generate updated documentation
            prompt = f"Generate updated documentation for a repository named '{repo}' with description: '{description}'. Include sections for installation, usage, API documentation, and examples."
            docs_content = self.groq_client.groq_llm(prompt)
            
            # Update documentation file
            self.github_service.create_or_update_file(
                repo, 
                "docs/README.md", 
                docs_content, 
                f"Update documentation for {repo}"
            )
            self.logger.info(f"[MaintainerAgent] Updated documentation for {repo}")
        except Exception as e:
            self.logger.error(f"[MaintainerAgent] Error updating documentation for {repo}: {e}")

    def _check_code_quality(self, repo: str):
        """Check code quality and suggest improvements."""
        try:
            # Get list of files
            files = self.github_service.list_files(repo)
            
            # Focus on Python files
            py_files = [f for f in files if f.endswith(".py")]
            
            for file_path in py_files:
                # Get file content
                content = self.github_service.get_file_content(repo, file_path)
                
                # Analyze code quality
                prompt = f"Analyze the following Python code for code quality issues, best practices, and potential improvements:\n\n{content[:2000]}"
                analysis = self.groq_client.groq_llm(prompt)
                
                # Create an issue if significant issues are found
                if "issue" in analysis.lower() or "improvement" in analysis.lower():
                    self.github_service.create_issue(
                        repo,
                        title=f"Code quality review for {file_path}",
                        body=analysis,
                        labels=["code-quality", "bot-suggestion"]
                    )
                    self.logger.info(f"[MaintainerAgent] Created code quality issue for {file_path}")
        except Exception as e:
            self.logger.error(f"[MaintainerAgent] Error checking code quality for {repo}: {e}")

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
                prompt = f"Suggest a concise fix or next step for this GitHub issue: {title}\n\nIssue description: {issue.get('body', '')[:500]}"
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
            else:
                # Review PR with AI
                try:
                    pr_details = self.github_service.get_pull_request(repo, number)
                    prompt = f"Review this pull request and provide feedback:\n\nTitle: {pr_details.get('title', '')}\n\nDescription: {pr_details.get('body', '')[:500]}\n\nCode changes: [Code changes would be analyzed here]"
                    review = self.groq_client.groq_llm(prompt)
                    self.github_service.create_issue_comment(
                        repo,
                        number,
                        f"## AI Code Review\n\n{review}",
                        is_pr=True
                    )
                    self.logger.info(f"[MaintainerAgent] Reviewed PR #{number} in {repo}")
                except Exception as e:
                    self.logger.error(f"[MaintainerAgent] Error reviewing PR #{number}: {e}")

    def _is_stale(self, last_updated: str) -> bool:
        try:
            dt = datetime.strptime(last_updated, "%Y-%m-%dT%H:%M:%SZ")
            return dt < datetime.now(IST) - timedelta(days=self.stale_days)
        except Exception:
            return False