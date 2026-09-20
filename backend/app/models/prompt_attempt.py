from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class PromptAttempt(Base):
    """One execution in the Prompt Playground sandbox -- captures exactly
    what the token-counter / cost-estimator UI needs to render, and doubles
    as the eval/analytics trail for which parameter combos users actually
    try."""

    __tablename__ = "prompt_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    user: Mapped["User"] = relationship(back_populates="prompt_attempts")

    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    response_text: Mapped[str] = mapped_column(Text, default="")

    model: Mapped[str] = mapped_column(default="claude-sonnet-4-6")
    temperature: Mapped[float] = mapped_column(Float, default=0.7)
    top_p: Mapped[float] = mapped_column(Float, default=0.95)
    max_output_tokens: Mapped[int] = mapped_column(Integer, default=1024)
    # Free-form bag for anything else a future parameter control adds
    # (top_k, stop sequences, ...) without a migration every time.
    extra_params: Mapped[dict] = mapped_column(JSON, default=dict)

    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)

    # Set when a semantic-cache hit served the response instead of a real
    # API call (see services/cache.py) -- surfaced in the UI so a user can
    # tell "this was instant because it was cached" from "this was slow".
    served_from_cache: Mapped[bool] = mapped_column(default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
