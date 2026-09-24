"use client";

import ReactMarkdown from "react-markdown";
import type { CalloutBlock as CalloutBlockType } from "@/lib/types";

export function CalloutBlockView({ block }: { block: CalloutBlockType }) {
  const isWarning = block.style === "warning";
  return (
    <div
      className={`rounded-lg border px-4 py-3 text-sm ${
        isWarning ? "border-amber-300 bg-amber-50 text-amber-800" : "border-brand/40 bg-brand/10 text-ink"
      }`}
    >
      <div className={`mb-1 text-xs font-medium uppercase tracking-wide ${isWarning ? "text-amber-700" : "text-brand"}`}>
        {isWarning ? "⚠ Watch out" : "✦ Key takeaway"}
      </div>
      <ReactMarkdown>{block.markdown}</ReactMarkdown>
    </div>
  );
}
