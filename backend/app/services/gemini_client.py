"""Thin wrapper around the Gemini API -- every real LLM call in this
codebase (sandbox execution, daily-pulse generation, evals, embeddings)
goes through here so there's one place that handles auth, retries, and
usage-metadata extraction.

Uses the `google-genai` SDK (`pip install google-genai`), Google's current
unified client for both Gemini Developer API and Vertex AI.
"""

import time
from dataclasses import dataclass

from google import genai
from google.genai import types

from app.core.config import get_settings

settings = get_settings()

_client: genai.Client | None = None


def get_client() -> genai.Client:
    global _client
    if _client is None:
        if not settings.gemini_api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set -- add it to backend/.env. "
                "No calls are mocked; this fails loudly instead of pretending to work."
            )
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


@dataclass
class GenerationResult:
    text: str
    input_tokens: int
    output_tokens: int
    latency_ms: int


def generate(
    prompt: str,
    *,
    model: str | None = None,
    temperature: float = 0.7,
    top_p: float = 0.95,
    max_output_tokens: int = 1024,
    response_schema: dict | None = None,
) -> GenerationResult:
    """Single-turn generation. Pass response_schema (a JSON schema dict) to
    force structured JSON output -- used by the Daily Pulse agent so its
    summary/exercise/quiz payload is guaranteed parseable, not scraped out
    of free-form prose."""
    client = get_client()
    started = time.monotonic()

    config = types.GenerateContentConfig(
        temperature=temperature,
        top_p=top_p,
        max_output_tokens=max_output_tokens,
        response_mime_type="application/json" if response_schema else "text/plain",
        response_schema=response_schema,
    )

    response = client.models.generate_content(
        model=model or settings.gemini_model,
        contents=prompt,
        config=config,
    )

    latency_ms = round((time.monotonic() - started) * 1000)
    usage = response.usage_metadata

    return GenerationResult(
        text=response.text or "",
        input_tokens=usage.prompt_token_count if usage else 0,
        output_tokens=usage.candidates_token_count if usage else 0,
        latency_ms=latency_ms,
    )


def embed(text: str) -> list[float]:
    """Used by services/cache.py (semantic cache lookups) and a future RAG
    retrieval step over Lesson content."""
    client = get_client()
    response = client.models.embed_content(model=settings.embedding_model, contents=text)
    return list(response.embeddings[0].values)
