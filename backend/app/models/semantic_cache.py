from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class SemanticCacheEntry(Base):
    """Backs services/cache.py. Embeddings stored as a JSON array of floats
    rather than a native vector column -- see core/config.py's note on why
    there's no pgvector/Milvus/Pinecone here. Fine at cache-table scale
    (hundreds to low thousands of rows); a real vector index is the first
    thing to add back if this ever needs to scale past brute-force cosine
    similarity in Python."""

    __tablename__ = "semantic_cache_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_embedding: Mapped[list[float]] = mapped_column(JSON, nullable=False)

    model: Mapped[str] = mapped_column(String(100), nullable=False)
    temperature: Mapped[float] = mapped_column(Float, default=0.7)

    response_text: Mapped[str] = mapped_column(Text, nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)

    hit_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_hit_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
