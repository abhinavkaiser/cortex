"use client";

import type { LinkBlock as LinkBlockType } from "@/lib/types";

// A clearly-labeled outbound card, not auto-embedded -- this is content
// the app doesn't control or host, unlike VideoBlockView/DocumentBlockView
// above (see lib/types.ts's LinkBlock docstring).
export function LinkBlockView({ block }: { block: LinkBlockType }) {
  let hostname = block.url;
  try {
    hostname = new URL(block.url).hostname;
  } catch {
    // not a fully-qualified URL -- show it as typed rather than throwing
  }

  return (
    <a
      href={block.url}
      target="_blank"
      rel="noopener noreferrer"
      className="block rounded-lg border border-line bg-surface p-4 transition-colors hover:border-brand/40 hover:bg-brand/5"
    >
      <div className="text-xs font-medium uppercase tracking-wide text-brand">↗ External link · {hostname}</div>
      <div className="mt-1 text-sm font-medium text-ink">{block.title}</div>
      {block.description && <p className="mt-1 text-sm text-ink-muted">{block.description}</p>}
    </a>
  );
}
