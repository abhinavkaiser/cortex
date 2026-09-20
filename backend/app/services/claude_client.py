"""Every real LLM call in this codebase (sandbox execution, daily-pulse
generation, evals) goes through here. Runs on the local Claude subscription
via the `claude` CLI (`claude --print`) -- flat-rate, no per-token API key,
no billing account to configure. This is the same pattern already proven
working elsewhere in this environment (xiot's aiService.js -- see that
file's own comment on why: one shared subscription session, not a metered
API key).

Structured JSON output is achieved by prompt instruction + parsing (the
`claude` CLI has no native --output-schema flag the way Codex's CLI does)
with one repair re-prompt if the first reply doesn't parse -- mirrors
xiot's generateJson/extractJson exactly, a pattern already proven to work
against this same CLI.

Token counts are estimates (~4 chars/token), not real usage_metadata --
`claude --print` doesn't report exact token counts on stdout. Since a
subscription is flat-rate, "cost" is illustrative here too (see
token_cost.py) rather than a real metered dollar amount -- useful for
showing which prompts are relatively more expensive, not for billing.
"""

import json
import re
import subprocess
import time
from dataclasses import dataclass

from app.core.config import get_settings

settings = get_settings()

CLAUDE_BIN = settings.claude_bin
DEFAULT_SYSTEM_PROMPT = "You are a helpful assistant. Answer the request directly and concisely."


def _spawn_claude(prompt: str, model: str | None, system_prompt: str = DEFAULT_SYSTEM_PROMPT, timeout: int = 250) -> str:
    args = [CLAUDE_BIN, "--print", "--dangerously-skip-permissions", "--system-prompt", system_prompt]
    if model:
        args += ["--model", model]

    result = subprocess.run(
        args,
        input=prompt,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or f"claude exited with code {result.returncode}").strip()
        raise RuntimeError(f"Claude CLI call failed: {detail[:500]}")
    return result.stdout.strip()


def _is_transient(message: str) -> bool:
    msg = message.lower()
    return any(s in msg for s in ["load failed", "network", "econnrefused", "timeout", "overloaded", "529"]) or re.match(
        r"claude cli call failed: claude exited with code \d+", msg
    )


def _rough_token_count(text: str) -> int:
    return max(1, round(len(text) / 4))


def _schema_example(schema: dict) -> dict:
    """Converts a flat JSON-Schema properties dict into a placeholder JSON
    *instance* for the prompt -- showing the model the raw schema document
    itself (with "type"/"properties"/"required" keys) is genuinely
    ambiguous: it's happened, live, that the model echoed the schema's own
    meta-structure back instead of producing an instance of it. An example
    with the real target keys at the top level has no such ambiguity. Only
    needs to handle the shapes this app's own schemas actually use (flat
    string/integer/array-of-string properties), not arbitrary JSON Schema."""
    example: dict = {}
    for key, spec in schema.get("properties", {}).items():
        t = spec.get("type")
        if t == "string":
            example[key] = spec.get("description", "...")
        elif t in ("integer", "number"):
            example[key] = 0
        elif t == "array":
            item_type = spec.get("items", {}).get("type", "string")
            example[key] = [f"<{item_type} 1>", f"<{item_type} 2>", "..."]
        else:
            example[key] = spec.get("description", "...")
    return example


def _extract_json(raw: str):
    obj_match = re.search(r"\{[\s\S]*\}", raw)
    arr_match = re.search(r"\[[\s\S]*\]", raw)
    for candidate in [m.group(0) if m else None for m in (obj_match, arr_match)]:
        if not candidate:
            continue
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    raise ValueError(f"No valid JSON found in response: {raw[:150]!r}")


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
    temperature: float = 0.7,  # accepted for API-shape compatibility -- the claude CLI's --print mode has no temperature flag, subscription usage doesn't expose sampling controls
    top_p: float = 0.95,  # same
    max_output_tokens: int = 1024,  # same -- not enforced client-side; a real cap would need a different (API-key-based) integration path
    response_schema: dict | None = None,
    retries: int = 3,  # a flat-rate subscription makes extra retries free, unlike a metered API -- lean generous here
) -> GenerationResult:
    """Single-turn generation. Pass response_schema (a JSON schema dict) to
    request structured JSON output -- enforced via prompt instruction +
    parse-and-retry, not a native API guarantee (see module docstring)."""
    effective_prompt = prompt
    if response_schema:
        required = response_schema.get("required", list(response_schema.get("properties", {}).keys()))
        example = _schema_example(response_schema)
        effective_prompt = (
            f"{prompt}\n\nRespond with ONLY a single JSON object -- no markdown code fences, no explanation "
            f"before or after, nothing but the JSON itself. It must have exactly these top-level keys: "
            f"{', '.join(required)}. Here is the shape to fill in with real content (the values below are "
            f"placeholders showing the expected type, not example output to imitate):\n{json.dumps(example, indent=2)}"
        )

    started = time.monotonic()
    last_err: Exception | None = None
    last_raw = ""

    for attempt in range(retries + 1):
        try:
            raw = _spawn_claude(effective_prompt, model)
        except Exception as err:  # noqa: BLE001 -- deliberately broad: CLI failures come as generic RuntimeError/TimeoutExpired
            last_err = err
            if attempt < retries and _is_transient(str(err)):
                time.sleep((attempt + 1) * 3)
                continue
            raise

        last_raw = raw
        if not response_schema:
            latency_ms = round((time.monotonic() - started) * 1000)
            return GenerationResult(
                text=raw,
                input_tokens=_rough_token_count(effective_prompt),
                output_tokens=_rough_token_count(raw),
                latency_ms=latency_ms,
            )

        try:
            parsed = _extract_json(raw)  # validate parseability + shape before returning; caller does the real parse
            missing = [k for k in required if not isinstance(parsed, dict) or k not in parsed]
            if missing:
                # Valid JSON, but not an instance of the requested shape --
                # this is exactly the failure mode that motivated
                # _schema_example: without this check, a schema-echo-back
                # (or any other wrong-shaped-but-valid JSON) would return
                # "successfully" here and crash the caller with a KeyError
                # instead of triggering a repair re-prompt.
                raise ValueError(f"missing required key(s) {missing}")
            latency_ms = round((time.monotonic() - started) * 1000)
            return GenerationResult(
                text=raw,
                input_tokens=_rough_token_count(effective_prompt),
                output_tokens=_rough_token_count(raw),
                latency_ms=latency_ms,
            )
        except ValueError as err:
            if attempt >= retries:
                raise ValueError(f"Model did not return valid JSON after retry: {raw[:150]!r} ({err})")
            effective_prompt = (
                f"{effective_prompt}\n\nYour previous reply was not usable ({err}) -- it began: {raw[:150]!r}. "
                f"Reply again with ONLY a JSON object containing exactly these keys: {', '.join(required)}."
            )

    raise last_err or ValueError(f"Model did not return valid JSON: {last_raw[:150]!r}")


_embedding_model = None


def embed(text: str) -> list[float]:
    """Local embeddings (sentence-transformers, all-MiniLM-L6-v2) -- no API
    key, no network call, runs entirely on-device. Same model already used
    elsewhere in this environment for embeddings (xiot's embeddingWorker.js,
    via the JS port of the same model) -- picked for consistency, not
    arbitrarily. Loaded once and cached at module scope since loading the
    model is the expensive part (~1-2s), not running it."""
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer

        _embedding_model = SentenceTransformer(settings.embedding_model)
    return _embedding_model.encode(text, normalize_embeddings=True).tolist()
