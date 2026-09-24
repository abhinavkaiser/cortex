"use client";

import { useState } from "react";
import { API_URL } from "@/lib/api";
import type { DocumentBlock as DocumentBlockType } from "@/lib/types";

export function DocumentBlockView({ block }: { block: DocumentBlockType }) {
  const [failed, setFailed] = useState(false);
  const src = `${API_URL}${block.url}`;

  return (
    <figure className="overflow-hidden rounded-lg border border-line bg-surface">
      <div className="flex items-center justify-between border-b border-line bg-white px-3 py-2">
        <div className="min-w-0">
          <div className="truncate text-sm font-medium text-ink">{block.title}</div>
          <div className="truncate text-xs text-ink-muted">{block.filename}</div>
        </div>
        <a
          href={src}
          download={block.filename}
          className="ml-3 shrink-0 rounded-lg border border-line px-3 py-1.5 text-xs font-medium text-ink hover:bg-surface"
        >
          Download
        </a>
      </div>
      {failed ? (
        <div className="flex min-h-[200px] flex-col items-center justify-center gap-1 p-6 text-center text-xs text-ink-muted">
          <span>This PDF can&apos;t be previewed inline in your browser -- use Download above.</span>
        </div>
      ) : (
        <embed
          src={src}
          type="application/pdf"
          className="h-[480px] w-full"
          onError={() => setFailed(true)}
        />
      )}
    </figure>
  );
}
