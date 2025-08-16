"""
Robust environment variable loading for Monsterrr using pydantic.BaseSettings.
"""

from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    DRY_RUN: bool = False
    MAX_AUTO_CREATIONS_PER_DAY: int = 3
    # Discord integration
    DISCORD_BOT_TOKEN: str
    DISCORD_GUILD_ID: str
    DISCORD_CHANNEL_ID: str
    def validate(self):
        missing = []
        for field in ["GROQ_API_KEY", "GITHUB_TOKEN", "GITHUB_ORG", "SMTP_HOST", "SMTP_USER", "SMTP_PASS", "DISCORD_BOT_TOKEN", "DISCORD_GUILD_ID", "DISCORD_CHANNEL_ID"]:
            if not getattr(self, field, None):
                missing.append(field)
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
    GROQ_API_KEY: str
    GITHUB_TOKEN: str
    GITHUB_ORG: str = "ni-sh-a-char"
    SMTP_HOST: str
    SMTP_PORT: int = 587
    SMTP_USER: str
    SMTP_PASS: str
    STATUS_REPORT_RECIPIENTS: str = ""
    GROQ_MODEL: str = "mixtral-8x7b"
    GROQ_TEMPERATURE: float = 0.2
    GROQ_MAX_TOKENS: int = 2048

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"

    @property
    def recipients(self) -> List[str]:
        return [e.strip() for e in self.STATUS_REPORT_RECIPIENTS.split(",") if e.strip()]
