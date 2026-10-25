// Subscription allowances apply; no per-request API charge is measured.
export function TokenCostMeter({ prompt, maxOutputTokens }: { prompt: string; model: string; maxOutputTokens: number }) {
  const inputTokens = Math.max(1, Math.round(prompt.length / 4));
  return <div className="flex flex-wrap gap-4 rounded-lg border border-line px-4 py-2 text-xs text-ink-muted">
    <span>About {inputTokens} input tokens</span>
    <span>ChatGPT subscription usage · allowances apply</span>
    <span>Output length setting ({maxOutputTokens}) is illustrative; the CLI does not enforce it.</span>
  </div>;
}
