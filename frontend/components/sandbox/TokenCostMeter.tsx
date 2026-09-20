// Mirrors backend/app/services/token_cost.py's rough estimator and pricing
// table -- this is a live, client-side PREVIEW only (updates on every
// keystroke, before any API call happens). The number that actually gets
// billed/recorded always comes from the real API response's usage_metadata,
// via /api/sandbox/execute -- see SandboxResult in lib/types.ts.

const PRICE_PER_1K_TOKENS: Record<string, { input: number; output: number }> = {
  "gemini-2.0-flash": { input: 0.000075, output: 0.0003 },
  "gemini-2.0-pro": { input: 0.00125, output: 0.005 },
};

function roughTokenCount(text: string): number {
  return Math.max(1, Math.round(text.length / 4));
}

export function TokenCostMeter({ prompt, model, maxOutputTokens }: { prompt: string; model: string; maxOutputTokens: number }) {
  const inputTokens = roughTokenCount(prompt);
  const price = PRICE_PER_1K_TOKENS[model] ?? { input: 0.0001, output: 0.0004 };

  // Worst-case cost assumes the model uses its full max_output_tokens
  // budget -- a ceiling, not a prediction, since real output length varies.
  const worstCaseCost = (inputTokens / 1000) * price.input + (maxOutputTokens / 1000) * price.output;

  return (
    <div className="flex items-center gap-4 rounded-lg border border-slate-800 px-4 py-2 text-xs text-slate-400">
      <span>
        ~<span className="text-slate-200">{inputTokens}</span> input tokens
      </span>
      <span className="text-slate-700">|</span>
      <span>
        up to <span className="text-slate-200">${worstCaseCost.toFixed(5)}</span> this call
      </span>
    </div>
  );
}
