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
        ideas = state.get('ideas', {}).get('top_ideas', [])
        repos = state.get('repos', [])
        actions = state.get('actions', [])
        report = [f"Monsterrr {period.capitalize()} Report ({now.strftime('%Y-%m-%d')}):"]
        report.append(f"Ideas: {len(ideas)}")
        report.append(f"Repos created: {len(repos)}")
        report.append(f"Actions taken: {len(actions)}")
        if period == 'weekly':
            report.append("(Weekly summary)")
        elif period == 'monthly':
            report.append("(Monthly summary)")
        return '\n'.join(report)
