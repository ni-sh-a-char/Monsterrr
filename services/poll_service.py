# Idea Voting & Polls Service

import json
import os

class PollService:
    def __init__(self, file_path="polls.json"):
        self.file_path = file_path
        self.polls = self._load_polls()

    def _load_polls(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def _save_polls(self):
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.polls, f)
        except Exception:
            pass

    def create_poll(self, question, options):
        poll = {'question': question, 'options': list(options), 'votes': {}}
        self.polls.append(poll)
        self._save_polls()
        return poll

    def vote(self, poll_index, user, option):
        if 0 <= poll_index < len(self.polls):
            poll = self.polls[poll_index]
            if option in poll['options']:
                poll['votes'][user] = option
                self._save_polls()
                return f"Vote recorded for {user}: {option}"
            else:
                return "Invalid option."
        return "Invalid poll index."
