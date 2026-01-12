"""Application configuration using pydantic-settings."""

from pathlib import Path
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings with environment variable support.
    It have defaults for all the settings but will replace them with values from a 
    env variable/env file as defined in model_config if present.
    preference order: 
    environment variable > .env file > default value in this class
"""

    # Reddit API (optional - if not provided, uses JSON endpoint without auth)
    # To upgrade to PRAW mode: create "script" app at https://www.reddit.com/prefs/apps
    reddit_client_id: Optional[str] = None
    reddit_client_secret: Optional[str] = None
    reddit_user_agent: str = "reddit-analyzer/1.0"

    # Anthropic API
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-haiku-4-5-20251001"

    # Target subreddits (comma-separated in .env)
    subreddits: str = ""

    # Content topic/focus (used for classification relevance filtering)
    topic: str = "AI and Large Language Models, particularly Claude and Claude Code related content"

    # HackerNews settings
    hn_default_keywords: str = "claude,anthropic,ai,artificial intelligence,llm"
    hn_fetch_limit: int = 100

    # MariaDB/MySQL (for caching classifications)
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = ""
    mysql_password: str = ""
    mysql_database: str = "reddit_analyzer"

    # Behavior
    default_batch_size: int = 20  # Posts per Claude API request
    cache_ttl_hours: int = 24
    max_lines_article: int = 5000  # Maximum characters for selftext/content
    debug: bool = False  # Enable SQL query logging

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

    def is_mysql_configured(self) -> bool:
        """Check if MySQL credentials are configured."""
        return bool(self.mysql_user and self.mysql_password)

    def get_subreddit_list(self) -> List[str]:
        """Parse and return list of subreddits from comma-separated string."""
        if not self.subreddits:
            return []
        return [s.strip() for s in self.subreddits.split(",") if s.strip()]

    def get_hn_keywords(self) -> List[str]:
        """Parse and return list of HackerNews keywords from comma-separated string."""
        if not self.hn_default_keywords:
            return []
        return [k.strip() for k in self.hn_default_keywords.split(",") if k.strip()]

    def ensure_directories(self) -> None:
        """Create output directories if they don't exist."""
        self.output_dir.mkdir(exist_ok=True)
        self.cache_dir.mkdir(exist_ok=True)
        self.classifications_dir.mkdir(exist_ok=True)
        self.reports_dir.mkdir(exist_ok=True)


# Global settings instance.
# this will read from env file as defuined in model_config all the variables 
# in the Settings class, and replace the defaults if found in said env file. 
settings = Settings()
