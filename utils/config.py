
"""
Robust environment variable loading for Monsterrr using pydantic.BaseSettings.
"""

from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    # General
    DRY_RUN: bool = False
    MAX_AUTO_CREATIONS_PER_DAY: int = 3

    # Discord integration
    DISCORD_BOT_TOKEN: str
    DISCORD_GUILD_ID: int
    DISCORD_CHANNEL_ID: int

    # SMTP (optional)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASS: Optional[str] = None

    # Groq / AI (optional)
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: Optional[str] = None
    GROQ_TEMPERATURE: float = 0.2
    GROQ_MAX_TOKENS: int = 2048

    # GitHub (optional)
    GITHUB_TOKEN: Optional[str] = None
    GITHUB_ORG: Optional[str] = None

    # Status reporting
    STATUS_REPORT_RECIPIENTS: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"

    @property
    def recipients(self) -> List[str]:
        return [e.strip() for e in self.STATUS_REPORT_RECIPIENTS.split(",") if e.strip()]

    def validate(self):
        """Check only required fields for Discord bot to run."""
        required = ["DISCORD_BOT_TOKEN", "DISCORD_GUILD_ID", "DISCORD_CHANNEL_ID"]
        missing = [f for f in required if not getattr(self, f, None)]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
