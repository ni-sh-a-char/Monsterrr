# Real-Time Alerts Service

import requests

class AlertService:
    def send_alert(self, event, discord_webhook_url=None, email=None):
        """
        Sends an alert to Discord via webhook and/or email (using free SMTP).
        Args:
            event (str): The alert message
            discord_webhook_url (str): Discord webhook URL (optional)
            email (str): Recipient email (optional)
        Returns:
            str: Status message
        """
        status = []
        # Discord webhook
        if discord_webhook_url:
            data = {"content": f"🚨 ALERT: {event}"}
            try:
                resp = requests.post(discord_webhook_url, json=data)
                if resp.status_code == 204:
                    status.append("Discord alert sent.")
                else:
                    status.append(f"Discord error: {resp.text}")
            except Exception as e:
                status.append(f"Discord error: {str(e)}")
        # Free SMTP (Gmail, Outlook, etc.)
        if email:
            import smtplib
            from email.mime.text import MIMEText
            msg = MIMEText(f"ALERT: {event}")
            msg["Subject"] = "Monsterrr Alert"
            msg["From"] = "monsterrr.alert@gmail.com"
            msg["To"] = email
            try:
                # Use Gmail's free SMTP (must enable 'less secure apps' or use app password)
                with smtplib.SMTP("smtp.gmail.com", 587) as server:
                    server.starttls()
                    # For demo, use a test account (replace with your own)
                    server.login("monsterrr.alert@gmail.com", "testpassword")
                    server.sendmail(msg["From"], [email], msg.as_string())
                status.append("Email alert sent.")
            except Exception as e:
                status.append(f"Email error: {str(e)}")
        if not status:
            return "No alert sent. Provide a Discord webhook or email."
        return " ".join(status)
