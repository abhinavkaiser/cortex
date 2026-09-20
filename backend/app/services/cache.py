"""Semantic cache: before paying for a real Gemini call, check whether a
sufficiently similar prompt (same model/temperature) was already answered
recently. Cosine similarity over embeddings stored in SQLite -- see
core/config.py and models/semantic_cache.py for why this isn't a real
vector DB (pgvector/Milvus/Pinecone) at this scale.
"""

import math

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.semantic_cache import SemanticCacheEntry
from app.services import gemini_client
from datetime import datetime

settings = get_settings()


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def lookup(db: Session, prompt: str, model: str, temperature: float) -> SemanticCacheEntry | None:
    """Returns the best cache hit above the similarity threshold, or None.
    Scoped to the same model+temperature -- a cached response generated at
    temperature=1.5 is not a valid stand-in for a temperature=0.1 request
    even if the prompt text is nearly identical, since the whole point of
    that parameter is to change the output distribution."""
    candidates = (
        db.query(SemanticCacheEntry)
        .filter(SemanticCacheEntry.model == model, SemanticCacheEntry.temperature == temperature)
        .all()
    )
    if not candidates:
        return None

    query_embedding = gemini_client.embed(prompt)

    best_entry, best_score = None, 0.0
    for entry in candidates:
        score = _cosine_similarity(query_embedding, entry.prompt_embedding)
        if score > best_score:
            best_entry, best_score = entry, score

    if best_entry and best_score >= settings.semantic_cache_similarity_threshold:
        best_entry.hit_count += 1
        best_entry.last_hit_at = datetime.utcnow()
        db.commit()
        return best_entry
    return None


def store(db: Session, prompt: str, model: str, temperature: float, response_text: str, input_tokens: int, output_tokens: int) -> None:
    embedding = gemini_client.embed(prompt)
    entry = SemanticCacheEntry(
        prompt_text=prompt,
        prompt_embedding=embedding,
        model=model,
        temperature=temperature,
        response_text=response_text,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
    db.add(entry)
    db.commit()
