# AI-Powered Code Review Service

import json
import os

class CodeReviewService:
    def __init__(self, file_path="code_review_log.json"):
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

    def review_pr(self, pr_path):
        # Basic code quality check: count TODOs and FIXME
        findings = []
        for root, dirs, files in os.walk(pr_path):
            for file in files:
                if file.endswith(('.py', '.js', '.ts')):
                    try:
                        with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                            content = f.read()
                        if 'TODO' in content:
                            findings.append(f"TODO found in {file}")
                        if 'FIXME' in content:
                            findings.append(f"FIXME found in {file}")
                    except Exception:
                        continue
        entry = {'pr': pr_path, 'findings': findings}
        self.log.append(entry)
        self._save_log()
        return f"Reviewed {pr_path}. Findings: {findings if findings else 'None'}"
