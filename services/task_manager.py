# Task Assignment & Tracking Service

import json
import os

class TaskManager:
    def __init__(self, file_path="tasks.json"):
        self.file_path = file_path
        self.tasks = self._load_tasks()

    def _load_tasks(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def _save_tasks(self):
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.tasks, f)
        except Exception:
            pass

    def assign_task(self, user, task):
        self.tasks.append({'user': user, 'task': task, 'status': 'assigned'})
        self._save_tasks()

    def get_tasks(self, user=None):
        if user:
            return [t for t in self.tasks if t['user'] == user]
        return self.tasks
