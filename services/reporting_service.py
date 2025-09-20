"""
Reporting Service for Monsterrr.
Handles comprehensive status reporting via email and Discord.
"""

import os
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from typing import Dict, Any, List

class ReportingService:
    """Service for generating and sending comprehensive reports."""
    
    def __init__(self, smtp_host: str = None, smtp_port: int = None, 
                 smtp_user: str = None, smtp_pass: str = None,
                 discord_channel = None, logger = None):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_pass = smtp_pass
        self.discord_channel = discord_channel
        self.logger = logger
        
    def generate_comprehensive_report(self) -> Dict[str, Any]:
        """Generate a comprehensive status report."""
        try:
            state = {}
            if os.path.exists("monsterrr_state.json"):
                with open("monsterrr_state.json", "r", encoding="utf-8") as f:
                    state = json.load(f)
            
            # Get repository information
            repos = state.get("repos", [])
            repo_count = len(repos)
            
            # Get idea information
            ideas = state.get("ideas", {}).get("top_ideas", [])
            idea_count = len(ideas)
            
            # Get action information
            actions = state.get("actions", [])
            action_count = len(actions)
            
            # Get branch information
            branches = state.get("branches", [])
            branch_count = len(branches)
            
            # Generate report data
            report = {
                "timestamp": datetime.utcnow().isoformat(),
                "summary": {
                    "repositories": repo_count,
                    "ideas": idea_count,
                    "actions": action_count,
                    "branches": branch_count
                },
                "repositories": repos,
                "ideas": ideas,
                "actions": actions,
                "branches": branches,
                "recent_activity": self._get_recent_activity(actions)
            }
            
            return report
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error generating report: {e}")
            return {"error": str(e)}
    
    def _get_recent_activity(self, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get recent activity from actions."""
        # Sort actions by timestamp and get the 5 most recent
        sorted_actions = sorted(actions, key=lambda x: x.get("timestamp", ""), reverse=True)
        return sorted_actions[:5]
    
    def send_email_report(self, recipients: List[str], report: Dict[str, Any]) -> bool:
        """Send a comprehensive email report."""
        if not self.smtp_host or not self.smtp_user or not self.smtp_pass:
            if self.logger:
                self.logger.warning("SMTP not configured. Skipping email report.")
            return False
            
        try:
            subject = f"Monsterrr Status Report - {datetime.utcnow().strftime('%Y-%m-%d')}"
            
            # Generate HTML content
            html_content = self._generate_html_report(report)
            
            # Generate text content
            text_content = self._generate_text_report(report)
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.smtp_user
            msg['To'] = ", ".join(recipients)
            
            # Add parts to message
            msg.attach(MIMEText(text_content, 'plain'))
            msg.attach(MIMEText(html_content, 'html'))
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_pass)
                server.sendmail(self.smtp_user, recipients, msg.as_string())
            
            if self.logger:
                self.logger.info(f"Email report sent to {recipients}")
            return True
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error sending email report: {e}")
            return False
    
    def send_discord_report(self, report: Dict[str, Any]) -> bool:
        """Send a report to Discord."""
        if not self.discord_channel:
            if self.logger:
                self.logger.warning("Discord channel not configured. Skipping Discord report.")
            return False
            
        try:
            # Generate Discord-friendly content
            content = self._generate_discord_report(report)
            
            # Send to Discord (this would require implementing Discord webhook logic)
            # For now, we'll just log that we would send it
            if self.logger:
                self.logger.info(f"Discord report content: {content}")
            
            return True
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error sending Discord report: {e}")
            return False
    
    def _generate_html_report(self, report: Dict[str, Any]) -> str:
        """Generate HTML report content."""
        summary = report.get("summary", {})
        repos = report.get("repositories", [])
        ideas = report.get("ideas", [])
        actions = report.get("actions", [])
        
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .header {{ background-color: #2d7ff9; color: white; padding: 20px; }}
                .section {{ margin: 20px 0; }}
                .summary-item {{ display: inline-block; margin-right: 30px; }}
                .summary-value {{ font-size: 24px; font-weight: bold; }}
                .summary-label {{ font-size: 14px; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Monsterrr Status Report</h1>
                <p>Generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
            </div>
            
            <div class="section">
                <h2>Summary</h2>
                <div class="summary-item">
                    <div class="summary-value">{summary.get('repositories', 0)}</div>
                    <div class="summary-label">Repositories</div>
                </div>
                <div class="summary-item">
                    <div class="summary-value">{summary.get('ideas', 0)}</div>
                    <div class="summary-label">Ideas</div>
                </div>
                <div class="summary-item">
                    <div class="summary-value">{summary.get('actions', 0)}</div>
                    <div class="summary-label">Actions</div>
                </div>
                <div class="summary-item">
                    <div class="summary-value">{summary.get('branches', 0)}</div>
                    <div class="summary-label">Branches</div>
                </div>
            </div>
            
            <div class="section">
                <h2>Recent Repositories</h2>
                <table>
                    <tr>
                        <th>Name</th>
                        <th>Description</th>
                        <th>Tech Stack</th>
                    </tr>
        """
        
        for repo in repos[:5]:  # Show only top 5
            html += f"""
                    <tr>
                        <td>{repo.get('name', 'N/A')}</td>
                        <td>{repo.get('description', 'N/A')}</td>
                        <td>{', '.join(repo.get('tech_stack', []))}</td>
                    </tr>
            """
        
        html += """
                </table>
            </div>
            
            <div class="section">
                <h2>Top Ideas</h2>
                <table>
                    <tr>
                        <th>Name</th>
                        <th>Description</th>
                        <th>Difficulty</th>
                    </tr>
        """
        
        for idea in ideas[:5]:  # Show only top 5
            html += f"""
                    <tr>
                        <td>{idea.get('name', 'N/A')}</td>
                        <td>{idea.get('description', 'N/A')}</td>
                        <td>{idea.get('difficulty', 'N/A')}</td>
                    </tr>
            """
        
        html += """
                </table>
            </div>
            
            <div class="section">
                <h2>Recent Actions</h2>
                <table>
                    <tr>
                        <th>Timestamp</th>
                        <th>Type</th>
                        <th>Details</th>
                    </tr>
        """
        
        for action in actions[:10]:  # Show only top 10
            html += f"""
                    <tr>
                        <td>{action.get('timestamp', 'N/A')}</td>
                        <td>{action.get('type', 'N/A')}</td>
                        <td>{str(action.get('details', 'N/A'))[:100]}...</td>
                    </tr>
            """
        
        html += """
                </table>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _generate_text_report(self, report: Dict[str, Any]) -> str:
        """Generate plain text report content."""
        summary = report.get("summary", {})
        repos = report.get("repositories", [])
        ideas = report.get("ideas", [])
        actions = report.get("actions", [])
        
        text = f"""
Monsterrr Status Report
Generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

SUMMARY
=======
Repositories: {summary.get('repositories', 0)}
Ideas: {summary.get('ideas', 0)}
Actions: {summary.get('actions', 0)}
Branches: {summary.get('branches', 0)}

RECENT REPOSITORIES
==================
        """
        
        for repo in repos[:5]:  # Show only top 5
            text += f"""
Name: {repo.get('name', 'N/A')}
Description: {repo.get('description', 'N/A')}
Tech Stack: {', '.join(repo.get('tech_stack', []))}
---
        """
        
        text += f"""
TOP IDEAS
=========
        """
        
        for idea in ideas[:5]:  # Show only top 5
            text += f"""
Name: {idea.get('name', 'N/A')}
Description: {idea.get('description', 'N/A')}
Difficulty: {idea.get('difficulty', 'N/A')}
---
        """
        
        text += f"""
RECENT ACTIONS
==============
        """
        
        for action in actions[:10]:  # Show only top 10
            text += f"""
Timestamp: {action.get('timestamp', 'N/A')}
Type: {action.get('type', 'N/A')}
Details: {str(action.get('details', 'N/A'))}
---
        """
        
        return text
    
    def _generate_discord_report(self, report: Dict[str, Any]) -> str:
        """Generate Discord-friendly report content."""
        summary = report.get("summary", {})
        
        discord_content = f"""
**Monsterrr Status Report** - {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

**Summary:**
- Repositories: {summary.get('repositories', 0)}
- Ideas: {summary.get('ideas', 0)}
- Actions: {summary.get('actions', 0)}
- Branches: {summary.get('branches', 0)}

Use `!status` for detailed information.
        """
        
        return discord_content