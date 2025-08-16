# Auto-merge & Auto-close Rules Service

import json
import os

class MergeService:
    def __init__(self, file_path="merge_log.json"):
        self.file_path = file_path
        self.log = self._load_log()

    def _load_log(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def _save_log(self):
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.log, f)
        except Exception:
            pass

    def auto_merge(self, pr):
        entry = {'action': 'auto-merge', 'pr': pr}
        self.log.append(entry)
        self._save_log()
        return f"PR {pr} auto-merged"

    def auto_close(self, issue):
        entry = {'action': 'auto-close', 'issue': issue}
        self.log.append(entry)
        self._save_log()
        return f"Issue {issue} auto-closed"
