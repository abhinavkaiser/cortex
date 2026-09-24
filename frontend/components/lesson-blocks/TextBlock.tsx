"use client";

import ReactMarkdown from "react-markdown";
import type { TextBlock as TextBlockType } from "@/lib/types";

export function TextBlockView({ block }: { block: TextBlockType }) {
  return (
    <article className="prose prose-slate max-w-none prose-headings:font-semibold prose-a:text-brand prose-p:text-ink-muted">
      <ReactMarkdown>{block.markdown}</ReactMarkdown>
    </article>
  );
}
