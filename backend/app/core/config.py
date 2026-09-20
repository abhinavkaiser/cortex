from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # SQLite by design (simplified from the original Postgres spec) -- a
    # single file, zero infra to stand up for local dev. Swapping back to
    # Postgres later is a one-line DATABASE_URL change since everything
    # goes through SQLAlchemy, not raw SQLite-specific SQL.
    database_url: str = "sqlite:///./ai_academy.db"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    # Semantic cache + RAG over lesson content: no pgvector/Milvus/Pinecone
    # here (see services/vector_store.py) -- embeddings are stored as JSON
    # blobs in SQLite and compared in Python. Fine at this scale; swap for a
    # real vector DB if the lesson corpus or cache grows large enough that
    # brute-force cosine similarity in Python becomes the bottleneck.
    embedding_model: str = "text-embedding-004"
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
