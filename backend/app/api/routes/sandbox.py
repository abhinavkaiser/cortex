import time

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.prompt_attempt import PromptAttempt
from app.models.user import User
from app.schemas.sandbox import SandboxExecuteRequest, SandboxExecuteResponse
from app.services import cache, claude_client, token_cost

router = APIRouter(prefix="/api/sandbox", tags=["sandbox"])


@router.post("/execute", response_model=SandboxExecuteResponse)
def execute_prompt(body: SandboxExecuteRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Powers the Prompt Playground. Checks the semantic cache first --
    identical/near-identical prompts at the same model+temperature reuse a
    prior real response instead of running another CLI call (cheap on a flat-rate subscription, but still slower than a cache hit)."""
    started = time.monotonic()

    cache_hit = cache.lookup(db, body.prompt, body.model, body.temperature)
    if cache_hit:
        attempt = PromptAttempt(
            user_id=user.id,
            prompt_text=body.prompt,
            response_text=cache_hit.response_text,
            model=body.model,
            temperature=body.temperature,
            top_p=body.top_p,
            max_output_tokens=body.max_output_tokens,
            input_tokens=cache_hit.input_tokens,
            output_tokens=cache_hit.output_tokens,
            estimated_cost_usd=0.0,  # a cache hit costs nothing -- that's the entire point
            latency_ms=round((time.monotonic() - started) * 1000),
            served_from_cache=True,
        )
        db.add(attempt)
        db.commit()
        db.refresh(attempt)
        return SandboxExecuteResponse(
            attempt_id=attempt.id,
            response_text=attempt.response_text,
            input_tokens=attempt.input_tokens,
            output_tokens=attempt.output_tokens,
            estimated_cost_usd=attempt.estimated_cost_usd,
            latency_ms=attempt.latency_ms,
            served_from_cache=True,
        )

    result = claude_client.generate(
        body.prompt,
        model=body.model,
        temperature=body.temperature,
        top_p=body.top_p,
        max_output_tokens=body.max_output_tokens,
    )
    cost = token_cost.estimate_cost_usd(body.model, result.input_tokens, result.output_tokens)

    attempt = PromptAttempt(
        user_id=user.id,
        prompt_text=body.prompt,
        response_text=result.text,
        model=body.model,
        temperature=body.temperature,
        top_p=body.top_p,
        max_output_tokens=body.max_output_tokens,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        estimated_cost_usd=cost,
        latency_ms=result.latency_ms,
        served_from_cache=False,
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    cache.store(db, body.prompt, body.model, body.temperature, result.text, result.input_tokens, result.output_tokens)

    return SandboxExecuteResponse(
        attempt_id=attempt.id,
        response_text=attempt.response_text,
        input_tokens=attempt.input_tokens,
        output_tokens=attempt.output_tokens,
        estimated_cost_usd=attempt.estimated_cost_usd,
        latency_ms=attempt.latency_ms,
        served_from_cache=False,
    )
