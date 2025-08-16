# Security & Compliance Monitoring Service

import os
import json
import re

class SecurityService:
    def __init__(self, file_path="security_scan_log.json"):
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

    def scan_repo(self, repo_path):
        # Scan for secrets in .env and source files
        findings = []
        for root, dirs, files in os.walk(repo_path):
            for file in files:
                if file.endswith(('.env', '.py', '.js', '.ts')):
                    try:
                        with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                            content = f.read()
                        # Simple regex for secrets
                        if re.search(r'(api[_-]?key|token|password|secret)[\s:=]+[\w\d\-]+', content, re.IGNORECASE):
                            findings.append(f"Potential secret in {file}")
                    except Exception:
                        continue
        entry = {'repo': repo_path, 'findings': findings}
        self.log.append(entry)
        self._save_log()
        return f"Scanned {repo_path}. Findings: {findings if findings else 'None'}"
