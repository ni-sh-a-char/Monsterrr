# Advanced Analytics Dashboard Service

import json
import os

class AnalyticsService:
    def __init__(self, file_path="analytics_dashboard.json"):
        self.file_path = file_path
        self.dashboard = self._load_dashboard()

    def _load_dashboard(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_dashboard(self):
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.dashboard, f)
        except Exception:
            pass

    def get_dashboard(self):
        return self.dashboard if self.dashboard else "No analytics data available."
