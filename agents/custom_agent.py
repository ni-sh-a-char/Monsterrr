# Customizable AI Agent

import json
import os

class CustomAgent:
    def __init__(self, name, file_path="custom_agent_log.json"):
        self.name = name
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

    def act(self, instruction):
        entry = {'agent': self.name, 'instruction': instruction}
        self.log.append(entry)
        self._save_log()
        return f"{self.name} executed: {instruction}"
