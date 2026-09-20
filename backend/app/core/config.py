from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # SQLite by design (simplified from the original Postgres spec) -- a
    # single file, zero infra to stand up for local dev. Swapping back to
    # Postgres later is a one-line DATABASE_URL change since everything
    # goes through SQLAlchemy, not raw SQLite-specific SQL.
    database_url: str = "sqlite:///./ai_academy.db"

    # Runs on the local Claude subscription via the `claude` CLI -- see
    # services/claude_client.py -- not a billed API key. `claude_bin` only
    # needs overriding if the CLI isn't on PATH under that exact name.
    claude_bin: str = "claude"
    claude_model: str = "claude-sonnet-4-6"

    # Local embeddings (sentence-transformers), no API key either -- see
    # claude_client.py's embed().
    embedding_model: str = "all-MiniLM-L6-v2"
    semantic_cache_similarity_threshold: float = 0.92

    daily_pulse_rss_feeds: list[str] = [
        "https://techcrunch.com/category/artificial-intelligence/feed/",
        "https://www.technologyreview.com/feed/",
    ]

    jwt_secret: str = "change-me-in-.env"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
