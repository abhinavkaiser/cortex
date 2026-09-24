"use client";

import { useMemo, useState } from "react";
import { encode, decode } from "gpt-tokenizer";

// A rotating palette of soft, distinguishable chip colors -- purely cosmetic,
// cycling by token index so adjacent chunks are visually separable.
const CHIP_COLORS = [
  "bg-rose-100 text-rose-700 ring-rose-500/40",
  "bg-amber-100 text-amber-800 ring-amber-500/40",
  "bg-lime-500/20 text-lime-200 ring-lime-500/40",
  "bg-cyan-100 text-cyan-700 ring-cyan-500/40",
  "bg-violet-100 text-violet-700 ring-violet-500/40",
  "bg-pink-500/20 text-pink-200 ring-pink-500/40",
];

const DEFAULT_TEXT = "After the meeting got rescheduled to 3pm, Maria finally sent the proposal.";

export function TokenizerDemo() {
  const [text, setText] = useState(DEFAULT_TEXT);

  const tokens = useMemo(() => {
    if (!text) return [];
    const ids = encode(text);
    return ids.map((id) => ({ id, chunk: decode([id]) }));
  }, [text]);

  return (
    <div className="rounded-xl border border-line bg-surface p-5">
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value.slice(0, 240))}
        rows={2}
        className="w-full resize-none rounded-lg border border-line bg-white px-3 py-2 text-sm text-ink focus:border-brand focus:outline-none"
        placeholder="Type anything..."
      />
      <div className="mt-4 flex flex-wrap gap-1.5 leading-relaxed">
        {tokens.map((t, i) => (
          <span
            key={i}
            title={`token id ${t.id}`}
            className={`rounded ring-1 px-1.5 py-0.5 font-mono text-sm whitespace-pre ${CHIP_COLORS[i % CHIP_COLORS.length]}`}
          >
            {t.chunk.replace(/\n/g, "⏎")}
          </span>
        ))}
      </div>
      <p className="mt-3 text-xs text-ink-muted">
        {tokens.length} token{tokens.length === 1 ? "" : "s"} for {text.length} character{text.length === 1 ? "" : "s"} -- notice it's rarely
        one-token-per-word. Common words are often a single chunk; rare words, typos, and numbers frequently get split into odd-looking pieces.
        Try typing <span className="font-mono text-ink-muted">antidisestablishmentarianism</span> or{" "}
        <span className="font-mono text-ink-muted">7492</span> to see it happen.
      </p>
    </div>
  );
}
