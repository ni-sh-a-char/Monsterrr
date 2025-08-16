# Conversation Memory Service

import json
import os

class ConversationMemory:
    def __init__(self, file_path="conversation_memory.json"):
        self.file_path = file_path
        self.memory = self._load_memory()

    def _load_memory(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_memory(self):
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.memory, f)
        except Exception:
            pass

    def remember(self, user_id, message):
        self.memory.setdefault(user_id, []).append(message)
        self._save_memory()

    def get_context(self, user_id):
        return self.memory.get(user_id, [])
