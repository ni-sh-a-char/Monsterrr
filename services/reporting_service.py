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
            
            # Get organization stats if available
            org_stats = state.get("organization_stats", {})
            
            # Get ideas information
            ideas_data = state.get("ideas", {})
            ideas_count = len(ideas_data.get("top_ideas", [])) if isinstance(ideas_data, dict) else 0
            
            # Get actions information
            actions = state.get("actions", [])
            actions_count = len(actions)
            
            # Get branches information (from actions)
            branches_count = sum(1 for action in actions if action.get("type") == "branch_created")
            
            # Get members count
            members_count = org_stats.get("members", 0) if org_stats else 0
            
            report = {
                "timestamp": datetime.utcnow().isoformat(),
                "summary": {
                    "repositories": repo_count,
                    "ideas": ideas_count,
                    "actions": actions_count,
                    "branches": branches_count,
                    "members": members_count
                },
                "repositories": repos,
                "organization_stats": org_stats,
                "ideas": ideas_data.get("top_ideas", []) if isinstance(ideas_data, dict) else [],
                "actions": actions,
                "branches": branches_count,
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
            
        if not recipients:
            if self.logger:
                self.logger.warning("No recipients specified. Skipping email report.")
            return False
            
        try:
            subject = f"Monsterrr Status Report - {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
            
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
                self.logger.info(f"Email report sent successfully to {recipients}")
            return True
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error sending email report: {e}")
            return False
    
    def _generate_html_report(self, report: Dict[str, Any]) -> str:
        """Generate HTML report content."""
        summary = report.get("summary", {})
        repos = report.get("repositories", [])
        ideas = report.get("ideas", [])
        actions = report.get("actions", [])
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Monsterrr Status Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
        .header {{ background: #2d7ff9; color: white; padding: 20px; border-radius: 8px 8px 0 0; margin: -30px -30px 20px -30px; }}
        .section {{ margin: 20px 0; }}
        .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin: 20px 0; }}
        .summary-item {{ background: #f0f8ff; padding: 15px; border-radius: 8px; text-align: center; }}
        .summary-value {{ font-size: 24px; font-weight: bold; color: #2d7ff9; }}
        .summary-label {{ font-size: 14px; color: #666; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Monsterrr Status Report</h1>
            <p>Generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
        </div>
        
        <div class="section">
            <h2>Summary</h2>
            <div class="summary-grid">
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
                <div class="summary-item">
                    <div class="summary-value">{summary.get('members', 0)}</div>
                    <div class="summary-label">Members</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2>Recent Activity</h2>
            <table>
                <thead>
                    <tr>
                        <th>Time</th>
                        <th>Action</th>
                        <th>Details</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for action in report.get("recent_activity", [])[:10]:  # Show only top 10
            html += f"""
                    <tr>
                        <td>{action.get('timestamp', 'N/A')[:19]}</td>
                        <td>{action.get('type', 'N/A')}</td>
                        <td>{str(action.get('details', 'N/A'))[:100]}...</td>
                    </tr>
            """
        
        html += """
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2>Top Ideas</h2>
            <table>
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Description</th>
                        <th>Tech Stack</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for idea in ideas[:5]:  # Show only top 5
            html += f"""
                    <tr>
                        <td>{idea.get('name', 'N/A')}</td>
                        <td>{idea.get('description', 'N/A')[:100]}...</td>
                        <td>{', '.join(idea.get('tech_stack', []))[:50]}...</td>
                    </tr>
            """
        
        html += """
                </tbody>
            </table>
        </div>
        
        <div class="footer">
            <p>This is an automated report from Monsterrr, your autonomous GitHub organization manager.</p>
            <p>Report generated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
        </div>
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
Members: {summary.get('members', 0)}

RECENT ACTIVITY
===============
        """
        
        for action in report.get("recent_activity", [])[:10]:  # Show only top 10
            text += f"""
{action.get('timestamp', 'N/A')[:19]} - {action.get('type', 'N/A')}
  Details: {str(action.get('details', 'N/A'))[:100]}...
            """
        
        text += f"""

TOP IDEAS
=========
        """
        
        for idea in ideas[:5]:  # Show only top 5
            text += f"""
Name: {idea.get('name', 'N/A')}
Description: {idea.get('description', 'N/A')[:100]}...
Tech Stack: {', '.join(idea.get('tech_stack', []))}
            """
        
        text += f"""

--
This is an automated report from Monsterrr, your autonomous GitHub organization manager.
Report generated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
        """
        
        return text
    
    def send_discord_report(self, report: Dict[str, Any]) -> bool:
        """Send a report to Discord."""
        if not self.discord_channel:
            return False
            
        # Implementation would go here
        return True