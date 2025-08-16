# Scheduled Q&A Sessions Service

import json
import os

class QAService:
    def __init__(self, file_path="qa_sessions.json"):
        self.file_path = file_path
        self.sessions = self._load_sessions()

    def _load_sessions(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def _save_sessions(self):
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.sessions, f)
        except Exception:
            pass

    def schedule_qa(self, time):
        entry = {'time': time, 'status': 'scheduled'}
        self.sessions.append(entry)
        self._save_sessions()
        return f"Q&A scheduled at {time}"
