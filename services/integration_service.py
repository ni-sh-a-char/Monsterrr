# Integration with Other Platforms Service

import json
import os

class IntegrationService:
    def __init__(self, file_path="integration_log.json"):
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

    def integrate(self, platform):
        entry = {'platform': platform, 'status': 'integrated'}
        self.log.append(entry)
        self._save_log()
        return f"Integrated with {platform}"
