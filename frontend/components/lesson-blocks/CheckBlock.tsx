"use client";

import { useState } from "react";
import type { CheckBlock as CheckBlockType } from "@/lib/types";

export function CheckBlockView({ block }: { block: CheckBlockType }) {
  const [selected, setSelected] = useState<number | null>(null);

  return (
    <div className="rounded-lg border border-line bg-white p-4">
      <div className="text-xs font-medium uppercase tracking-wide text-ink-muted">Check your understanding</div>
      <p className="mt-2 text-sm font-medium text-ink">{block.question}</p>
      <div className="mt-3 space-y-1.5">
        {block.choices.map((choice, i) => {
          const isSelected = selected === i;
          const isCorrect = i === block.correct_index;
          let cls = "border-line hover:border-brand/40";
          if (selected !== null) {
            if (isCorrect) cls = "border-emerald-500 bg-emerald-50";
            else if (isSelected) cls = "border-rose-500 bg-rose-50";
            else cls = "border-line opacity-60";
          }
          return (
            <button
              key={i}
              onClick={() => selected === null && setSelected(i)}
              disabled={selected !== null}
              className={`block w-full rounded-lg border px-3 py-2 text-left text-sm text-ink transition-colors ${cls}`}
            >
              {choice}
            </button>
          );
        })}
      </div>
      {selected !== null && (
        <p className={`mt-3 text-sm ${selected === block.correct_index ? "text-emerald-700" : "text-ink-muted"}`}>
          {selected === block.correct_index ? "Correct. " : "Not quite. "}
          {block.explanation}
        </p>
      )}
    </div>
  );
}
