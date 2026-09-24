"use client";

import { API_URL } from "@/lib/api";
import type { ImageBlock as ImageBlockType } from "@/lib/types";

export function ImageBlockView({ block }: { block: ImageBlockType }) {
  return (
    <figure className="overflow-hidden rounded-lg border border-line bg-white">
      {/* eslint-disable-next-line @next/next/no-img-element -- a locally-generated file the backend serves at a stable path, not worth next/image's remote-pattern config for one static host */}
      <img src={`${API_URL}${block.url}`} alt={block.alt} className="w-full" />
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
