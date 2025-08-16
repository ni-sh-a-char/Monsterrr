# Automated Documentation Updates Service

import os

class DocService:
    def update_docs(self, repo_path):
        # Update README.md and CHANGELOG.md in the repo_path
        readme_path = os.path.join(repo_path, "README.md")
        changelog_path = os.path.join(repo_path, "CHANGELOG.md")
        updated = []
        if os.path.exists(readme_path):
            with open(readme_path, "a", encoding="utf-8") as f:
                f.write("\n\nUpdated by Monsterrr AI.")
            updated.append("README.md")
        if os.path.exists(changelog_path):
            with open(changelog_path, "a", encoding="utf-8") as f:
                f.write("\n\nChange logged by Monsterrr AI.")
            updated.append("CHANGELOG.md")
        if updated:
            return f"Updated: {', '.join(updated)}"
        return "No docs found to update."
