# Issue & PR Triage Service

class TriageService:
    def triage_issue(self, issue_text):
        # Simple keyword-based triage (replace with ML if desired)
        issue_text = issue_text.lower()
        if "security" in issue_text or "vulnerability" in issue_text:
            label = "security"
            priority = "critical"
        elif "bug" in issue_text or "error" in issue_text:
            label = "bug"
            priority = "high"
        elif "feature" in issue_text or "enhancement" in issue_text:
            label = "enhancement"
            priority = "medium"
        else:
            label = "other"
            priority = "low"
        return {'label': label, 'priority': priority, 'assignee': 'auto'}

    def triage_pr(self, pr_text):
        pr_text = pr_text.lower()
        if "refactor" in pr_text:
            label = "refactor"
            priority = "medium"
        elif "fix" in pr_text:
            label = "bugfix"
            priority = "high"
        elif "feature" in pr_text:
            label = "feature"
            priority = "medium"
        else:
            label = "other"
            priority = "low"
        return {'label': label, 'priority': priority, 'assignee': 'auto'}
