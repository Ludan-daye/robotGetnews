from typing import Optional, List
from pydantic import field_validator
from pydantic_settings import BaseSettings
import os


class Settings(BaseSettings):
    # Application
    app_name: str = "GitHub Bot WebUI"
    app_version: str = "1.0.0"
    debug: bool = False
    secret_key: str
    cors_origins: str = "http://localhost:3000"

    # Database
    database_url: str = "sqlite:///./database/githubbot.db"
    database_echo: bool = False

    # GitHub API
    github_token: str
    github_api_base_url: str = "https://api.github.com"
    github_api_rate_limit: int = 5000
    github_api_rate_window: int = 3600

    # Time Zone
    default_timezone: str = "Asia/Singapore"

    # SMTP Configuration
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_tls: bool = True
    email_from: Optional[str] = None

    # Telegram
    telegram_bot_token: Optional[str] = None
    telegram_api_url: str = "https://api.telegram.org/bot"

    # WeChat Work
    wechat_webhook_url: Optional[str] = None

    # Slack
    slack_webhook_url: Optional[str] = None

    # Scheduler
    scheduler_timezone: str = "Asia/Singapore"
    default_schedule_hour: int = 9
    default_schedule_minute: int = 0

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # Cache
    redis_url: Optional[str] = None
    cache_ttl: int = 3600

    @property
    def cors_origins_list(self) -> List[str]:
        if isinstance(self.cors_origins, str):
            return [i.strip() for i in self.cors_origins.split(",")]
        return self.cors_origins

    model_config = {
        "env_file": ".env",
        "case_sensitive": False
    }


def get_settings() -> Settings:
    return Settings()


settings = get_settings()