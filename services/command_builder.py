# Custom Command Builder Service

import json
import os

class CommandBuilder:
    def __init__(self, file_path="custom_commands.json"):
        self.file_path = file_path
        self.commands = self._load_commands()

    def _load_commands(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def _save_commands(self):
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.commands, f)
        except Exception:
            pass

    def create_command(self, name, action):
        entry = {'name': name, 'action': action}
        self.commands.append(entry)
        self._save_commands()
        return f"Command {name} created to {action}"
