"""Token/cost estimation for the sandbox's cost-estimator UI and for
recording usage on PromptAttempt rows.

Running on a Claude subscription (see claude_client.py) means this is
NOT a real metered dollar amount -- a subscription is flat-rate. The
numbers below are Anthropic's real published per-token API pricing, used
here purely as an illustrative "what would this have cost on metered
billing" reference so the UI's cost meter still means something (which
prompts are relatively expensive) rather than showing a fake $0.00 that
would suggest cost never matters. Prices change over time -- check
anthropic.com/pricing before trusting this for anything that actually
involves money.
"""

PRICE_PER_1K_TOKENS = {
    "claude-haiku-4-5-20251001": {"input": 0.0008, "output": 0.004},
    "claude-sonnet-4-6": {"input": 0.003, "output": 0.015},
    "claude-opus-4-7": {"input": 0.015, "output": 0.075},
}
DEFAULT_PRICE = {"input": 0.003, "output": 0.015}


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    price = PRICE_PER_1K_TOKENS.get(model, DEFAULT_PRICE)
    return round((input_tokens / 1000) * price["input"] + (output_tokens / 1000) * price["output"], 6)


def rough_token_count(text: str) -> int:
    """Fallback estimator for the frontend's live token counter (updates on
    every keystroke -- calling the real CLI per keystroke would be wasteful
    and slow). ~4 chars/token is the standard rule-of-thumb for English text
    with these tokenizer families. The `claude` CLI doesn't report exact
    token counts on stdout either, so this same estimate is also what
    actually gets stored on PromptAttempt -- see claude_client.py -- not
    just a client-side preview the way it would be against a real API.
    """
    return max(1, round(len(text) / 4))
