// Mirrors backend/app/services/token_cost.py's estimator and pricing table
// -- this is a live, client-side PREVIEW only (updates on every keystroke,
// before any CLI call happens). Running on a Claude subscription (not a
// metered API key -- see claude_client.py), so this is illustrative "what
// this would cost on metered billing" using Anthropic's published API
// pricing, not a real charge. The number recorded on the actual attempt
// (via /api/sandbox/execute -- see SandboxResult in lib/types.ts) uses the
// same ~4-chars/token estimate, since the CLI doesn't report exact counts.

const PRICE_PER_1K_TOKENS: Record<string, { input: number; output: number }> = {
  "claude-haiku-4-5-20251001": { input: 0.0008, output: 0.004 },
  "claude-sonnet-4-6": { input: 0.003, output: 0.015 },
  "claude-opus-4-7": { input: 0.015, output: 0.075 },
};

function roughTokenCount(text: string): number {
  return Math.max(1, Math.round(text.length / 4));
}

export function TokenCostMeter({ prompt, model, maxOutputTokens }: { prompt: string; model: string; maxOutputTokens: number }) {
  const inputTokens = roughTokenCount(prompt);
  const price = PRICE_PER_1K_TOKENS[model] ?? { input: 0.003, output: 0.015 };

  // Worst-case cost assumes the model uses its full max_output_tokens
  // budget -- a ceiling, not a prediction, since real output length varies.
  const worstCaseCost = (inputTokens / 1000) * price.input + (maxOutputTokens / 1000) * price.output;

  return (
    <div className="flex items-center gap-4 rounded-lg border border-line px-4 py-2 text-xs text-ink-muted">
      <span>
        ~<span className="text-ink">{inputTokens}</span> input tokens
      </span>
      <span className="text-ink">|</span>
      <span>
        up to <span className="text-ink">${worstCaseCost.toFixed(5)}</span> equivalent (flat-rate subscription, not billed)
      </span>
    </div>
  );
}
