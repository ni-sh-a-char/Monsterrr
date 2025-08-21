# Executive Report Service

import json
import os
from datetime import datetime, timedelta

class ReportService:
    def __init__(self, state_file="monsterrr_state.json"):
        self.state_file = state_file

    def _load_state(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def generate_report(self, period='daily'):
        state = self._load_state()
        now = datetime.utcnow()
        report = [f"Monsterrr {period.capitalize()} Report ({now.strftime('%Y-%m-%d')}):"]

        # System status
        startup = state.get('startup', 'N/A')
        uptime = state.get('uptime', 'N/A')
        model = state.get('model', 'N/A')
        guilds = state.get('guilds', 'N/A')
        members = state.get('members', 'N/A')
        total_messages = state.get('total_messages', 'N/A')
        report.append(f"System Status:\n  Startup: {startup}\n  Uptime: {uptime}\n  Model: {model}\n  Guilds: {guilds}\n  Members: {members}\n  Total messages: {total_messages}")

        # Top ideas
        ideas = state.get('ideas', {}).get('top_ideas', [])
        report.append(f"\nTop Ideas ({len(ideas)}):")
        for idea in ideas:
            report.append(f"  - {idea.get('name','')}: {idea.get('description','')}")

        # Active repositories
        repos = state.get('repos', [])
        report.append(f"\nActive Repositories ({len(repos)}):")
        for repo in repos:
            report.append(f"  - {repo.get('name','')}: {repo.get('description','')} ({repo.get('url','')})")

        # Branches
        branches = state.get('branches', [])
        if branches:
            report.append(f"\nBranches ({len(branches)}):")
            for branch in branches:
                report.append(f"  - {branch.get('name','')} in {branch.get('repo','')}: {branch.get('description','')}")

        # Pull requests
        pr = state.get('pull_requests', {})
        if pr:
            report.append(f"\nPull Requests: {pr.get('count','N/A')} (avg age: {pr.get('avg_age_days','N/A')} days)")

        # Issues
        issues = state.get('issues', {})
        if issues:
            report.append(f"\nIssues: {issues.get('count','N/A')} (critical: {issues.get('critical',0)}, high: {issues.get('high',0)}, medium: {issues.get('medium',0)}, low: {issues.get('low',0)})")

        # CI status
        ci = state.get('ci', {})
        if ci:
            report.append(f"\nCI Pipeline: {ci.get('status','N/A')} (avg duration: {ci.get('avg_duration','N/A')})")

        # Security alerts
        sec = state.get('security', {})
        if sec:
            report.append(f"\nSecurity Alerts: {sec.get('critical_alerts',0)} critical, {sec.get('warnings',0)} warnings")

        # Automation bots
        bots = state.get('automation_bots', {})
        if bots:
            report.append(f"\nAutomation Bots:")
            for bot_name, bot_info in bots.items():
                report.append(f"  - {bot_name}: {bot_info}")

        # Queue
        queue = state.get('queue', [])
        if queue:
            report.append(f"\nActive Queue:")
            for task in queue:
                report.append(f"  - {task}")

        # Analytics
        analytics = state.get('analytics', {})
        if analytics:
            report.append(f"\nAnalytics:")
            for k, v in analytics.items():
                report.append(f"  - {k.replace('_',' ').title()}: {v}")

        # Tasks
        tasks = state.get('tasks', {})
        if tasks:
            report.append(f"\nTasks:")
            for user, tlist in tasks.items():
                report.append(f"  - {user}: {', '.join(tlist)}")

        # Recent user activity (if available)
        recent_msgs = state.get('recent_msgs', [])
        if recent_msgs:
            report.append(f"\nRecent User Activity:")
            for msg in recent_msgs:
                report.append(f"  - {msg}")

        # Next actions
        next_actions = state.get('next_actions', [])
        if next_actions:
            report.append(f"\nWhat I can do next:")
            for action in next_actions:
                report.append(f"  - {action}")

        # All actions performed today
        actions = state.get('actions', [])
        if actions:
            report.append("\nActions performed today:")
            today = now.date()
            for a in actions:
                try:
                    ts = a.get("timestamp")
                    ts_date = datetime.fromisoformat(ts).date() if ts else None
                    if ts_date == today:
                        action_type = a.get("type", "action")
                        details = a.get("details", {})
                        if action_type == "ideas_fetched":
                            report.append(f"- Fetched and ranked {details.get('count',0)} ideas: {', '.join(details.get('ideas', []))}")
                        elif action_type == "daily_plan":
                            plan = details.get('plan', [])
                            plan_str = '; '.join(str(p) for p in plan)
                            report.append(f"- Planned daily contributions: {plan_str}")
                        elif action_type == "plan_executed":
                            plan = details.get('plan', [])
                            plan_str = '; '.join(str(p) for p in plan)
                            report.append(f"- Executed daily plan: {plan_str}")
                        elif action_type == "maintenance":
                            report.append("- Performed repository maintenance.")
                        else:
                            report.append(f"- {action_type}: {details}")
                except Exception:
                    continue
        else:
            report.append("No actions recorded today.")

        if period == 'weekly':
            report.append("(Weekly summary)")
        elif period == 'monthly':
            report.append("(Monthly summary)")
        return '\n'.join(report)
