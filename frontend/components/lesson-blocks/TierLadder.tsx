"use client";

import { useState } from "react";
import type { TiersDiagram } from "@/lib/types";

// Cool -> warm ramp so climbing the ladder reads as escalation (capability,
// risk, autonomy -- whatever the tiers represent) even before you read a
// word of the labels. Cycles if a lesson ever has more than 5 tiers.
const RAMP = [
  { ring: "ring-emerald-500/40", bg: "bg-emerald-50", text: "text-emerald-700", bar: "bg-emerald-500" },
  { ring: "ring-cyan-500/40", bg: "bg-cyan-50", text: "text-cyan-700", bar: "bg-cyan-500" },
  { ring: "ring-amber-500/40", bg: "bg-amber-50", text: "text-amber-700", bar: "bg-amber-500" },
  { ring: "ring-orange-500/40", bg: "bg-orange-500/10", text: "text-orange-300", bar: "bg-orange-500" },
  { ring: "ring-rose-500/40", bg: "bg-rose-50", text: "text-rose-700", bar: "bg-rose-500" },
];

// A taxonomy isn't a process -- there's no "next step," just a set of
// tiers you compare. An accordion ladder (click a rung to expand it in
// place) fits that better than the click-a-node/slide-a-panel pattern used
// for actual workflows elsewhere in this app (see the language-model /
// RAG / agent explainer pages): everything stays in one place, the reader
// compares tiers by opening more than one at once if they want.
export function TierLadder({ block }: { block: TiersDiagram }) {
  const [open, setOpen] = useState<Set<number>>(new Set([0]));

  function toggle(i: number) {
    setOpen((prev) => {
      const next = new Set(prev);
      if (next.has(i)) next.delete(i);
      else next.add(i);
      return next;
    });
  }

  return (
    <div>
      {block.title && <div className="mb-3 text-sm font-medium text-ink">{block.title}</div>}
      <div className="space-y-1.5">
        {block.items.map((item, i) => {
          const color = RAMP[i % RAMP.length];
          const isOpen = open.has(i);
          return (
            <div key={i} className={`overflow-hidden rounded-lg ring-1 transition-colors ${color.ring} ${isOpen ? color.bg : "bg-surface"}`}>
              <button onClick={() => toggle(i)} className="flex w-full items-center gap-3 px-3 py-2.5 text-left">
                <span className={`h-1.5 w-6 shrink-0 rounded-full ${color.bar}`} style={{ width: `${18 + i * 8}px` }} />
                <span className={`flex-1 text-sm font-medium ${color.text}`}>{item.label}</span>
                <span className={`text-xs transition-transform ${color.text} ${isOpen ? "rotate-180" : ""}`}>▾</span>
              </button>
              {isOpen && item.description && <p className="px-3 pb-3 text-sm text-ink-muted">{item.description}</p>}
            </div>
          );
        })}
      </div>
      <p className="mt-2 text-xs text-ink-muted">Click a tier to expand it -- open as many as you want to compare them side by side.</p>
    </div>
  );
}
