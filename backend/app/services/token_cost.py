"""Token/cost estimation for the sandbox's cost-estimator UI and for
recording real usage on PromptAttempt rows.

Pricing below is illustrative (Gemini 2.0 Flash-tier pricing as a
placeholder) -- Google's published rates change over time and vary by
context-window tier, so treat PRICE_PER_1K_TOKENS as something to update
from the live pricing page before this touches real billing decisions,
not a value to trust blindly.
"""

PRICE_PER_1K_TOKENS = {
    "gemini-2.0-flash": {"input": 0.000075, "output": 0.0003},
    "gemini-2.0-pro": {"input": 0.00125, "output": 0.005},
}
DEFAULT_PRICE = {"input": 0.0001, "output": 0.0004}


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    price = PRICE_PER_1K_TOKENS.get(model, DEFAULT_PRICE)
    return round((input_tokens / 1000) * price["input"] + (output_tokens / 1000) * price["output"], 6)


def rough_token_count(text: str) -> int:
    """Fallback estimator for the frontend's live token counter (updates on
    every keystroke -- calling the real API per keystroke would be wasteful
    and slow). ~4 chars/token is the standard rule-of-thumb for English text
    with these tokenizer families; the real count from the API response
    (usage_metadata) is always what actually gets stored on PromptAttempt,
    this is only ever a client-side preview."""
    return max(1, round(len(text) / 4))
