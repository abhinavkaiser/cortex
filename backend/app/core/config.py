from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # SQLite by design (simplified from the original Postgres spec) -- a
    # single file, zero infra to stand up for local dev. Swapping back to
    # Postgres later is a one-line DATABASE_URL change since everything
    # goes through SQLAlchemy, not raw SQLite-specific SQL.
    database_url: str = "sqlite:///./ai_academy.db"

    # App-owned ChatGPT subscription session. No API key or Claude dependency.
    codex_bin: str = "/opt/cortex-codex/node_modules/.bin/codex"
    codex_model: str = "gpt-5.4"
    codex_fast_model: str = "gpt-5.4-mini"
    # Retained to tolerate the existing production .env during migration.
    claude_bin: str = "claude"
    claude_model: str = "sonnet"

    # Local embeddings (sentence-transformers), no API key either -- see
    # claude_client.py's embed().
    embedding_model: str = "all-MiniLM-L6-v2"
    semantic_cache_similarity_threshold: float = 0.92

    daily_pulse_rss_feeds: list[str] = [
        "https://techcrunch.com/category/artificial-intelligence/feed/",
        "https://www.technologyreview.com/feed/",
    ]

    # Only used by the image-generation MCP server (app/agents/image_mcp.py)
    # for lesson illustrations -- real, metered, billed APIs, unlike
    # everything else in this app. Optional: None until set in .env, and
    # nothing in the running app itself ever touches either key. Mirrors
    # the exact same DALL-E-first-then-Gemini-fallback pattern already
    # proven in xiot's imageGenService.js -- DALL-E 3 for quality, Gemini
    # 2.5 Flash Image (free tier) as a no-cost fallback.
    openai_api_key: str | None = None
    gemini_api_key: str | None = None

    jwt_secret: str = "change-me-in-.env"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
