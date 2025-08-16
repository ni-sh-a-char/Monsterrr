import smtplib
from email.mime.text import MIMEText
from utils.config import Settings
settings = Settings()

def send_instant_email(subject, body):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = settings.SMTP_SENDER
    msg['To'] = settings.SMTP_RECIPIENT
    with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.sendmail(settings.SMTP_SENDER, [settings.SMTP_RECIPIENT], msg.as_string())

def send_slack_notification(message):
    pass
