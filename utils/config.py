"""
Robust environment variable loading for Monsterrr using pydantic.BaseSettings.
"""

from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    GROQ_API_KEY: str
    GITHUB_TOKEN: str
    GITHUB_ORG: str = "ni_sh_a.char"
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

    @property
    def recipients(self) -> List[str]:
        return [e.strip() for e in self.STATUS_REPORT_RECIPIENTS.split(",") if e.strip()]
