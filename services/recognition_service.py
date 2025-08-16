# Contributor Recognition Service

import json
import os

class RecognitionService:
    def __init__(self, file_path="recognition_log.json"):
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

    def recognize(self, user):
        msg = f"Thank you, {user}, for your contributions!"
        self.log.append({'user': user, 'message': msg})
        self._save_log()
        return msg
