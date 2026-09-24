"use client";

import { useState } from "react";
import { API_URL } from "@/lib/api";
import type { ImageBlock as ImageBlockType } from "@/lib/types";

export function ImageBlockView({ block }: { block: ImageBlockType }) {
  const [failed, setFailed] = useState(false);
  const src = `${API_URL}${block.url}`;

  return (
    <figure className="overflow-hidden rounded-lg border border-line bg-surface">
      {failed ? (
        <div className="flex min-h-[160px] flex-col items-center justify-center gap-1 p-6 text-center text-xs text-ink-muted">
          <span>Image failed to load</span>
          <span className="break-all text-[10px] opacity-70">{src}</span>
        </div>
      ) : (
        // eslint-disable-next-line @next/next/no-img-element -- a locally-generated file the backend serves at a stable path, not worth next/image's remote-pattern config for one static host
        <img src={src} alt={block.alt} className="w-full" onError={() => setFailed(true)} />
      )}
      {(block.caption || block.attribution) && (
        <figcaption className="px-3 py-2 text-xs text-ink-muted">
          {block.caption}
          {block.caption && block.attribution ? " — " : ""}
          {block.attribution}
        </figcaption>
      )}
    </figure>
  );
}
