"""Application configuration using pydantic-settings."""

from pathlib import Path
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Reddit API (optional - if not provided, uses JSON endpoint without auth)
    # To upgrade to PRAW mode: create "script" app at https://www.reddit.com/prefs/apps
    reddit_client_id: Optional[str] = None
    reddit_client_secret: Optional[str] = None
    reddit_user_agent: str = "reddit-analyzer/1.0"

    # Anthropic API
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-haiku-4-5-20251001"

    # Target subreddits (comma-separated in .env)
    subreddits: str = "ClaudeAI,Claude,ClaudeCode,ClaudeExplorers"

    # Behavior
    default_batch_size: int = 20  # Posts per Claude API request
    cache_ttl_hours: int = 24

    # Paths
    output_dir: Path = Path("outputs")
    cache_dir: Path = Path("outputs/cache")
    classifications_dir: Path = Path("outputs/classifications")
    reports_dir: Path = Path("outputs/reports")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    def is_reddit_authenticated(self) -> bool:
        """Check if Reddit credentials are configured."""
        return bool(self.reddit_client_id and self.reddit_client_secret)

    def get_subreddit_list(self) -> List[str]:
        """Parse and return list of subreddits from comma-separated string."""
        return [s.strip() for s in self.subreddits.split(",") if s.strip()]

    def ensure_directories(self) -> None:
        """Create output directories if they don't exist."""
        self.output_dir.mkdir(exist_ok=True)
        self.cache_dir.mkdir(exist_ok=True)
        self.classifications_dir.mkdir(exist_ok=True)
        self.reports_dir.mkdir(exist_ok=True)


# Global settings instance
settings = Settings()
