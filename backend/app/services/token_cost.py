"""Compatibility helpers for stored sandbox estimates.

Codex uses a ChatGPT subscription; no per-request API charge is measured.
The legacy numeric cost field remains zero for new subscription attempts.
This is not a statement that the subscription or its usage is unlimited/free.
"""


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    return 0.0


def rough_token_count(text: str) -> int:
    return max(1, round(len(text) / 4))
