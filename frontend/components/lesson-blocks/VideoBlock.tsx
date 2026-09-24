"use client";

import { useState } from "react";
import type { VideoBlock as VideoBlockType } from "@/lib/types";
import { parseVideoEmbed } from "@/lib/videoEmbed";

export function VideoBlockView({ block }: { block: VideoBlockType }) {
  const [showTranscript, setShowTranscript] = useState(false);
  const embed = parseVideoEmbed(block.url);

  return (
    <figure className="overflow-hidden rounded-lg border border-line bg-surface">
      <div className="relative aspect-video w-full bg-black">
        {embed ? (
          <iframe
            src={embed.embedUrl}
            title={block.title}
            className="absolute inset-0 h-full w-full"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
          />
        ) : (
          // Not a known provider -- a direct file URL (or anything else),
          // so a native <video> tag is the honest fallback rather than
          // guessing at an embed format.
          <video controls className="absolute inset-0 h-full w-full" src={block.url}>
            Your browser doesn&apos;t support embedded video.{" "}
            <a href={block.url} className="text-brand underline">
              Download it instead
            </a>
            .
          </video>
        )}
      </div>
      <div className="px-3 py-2">
        <div className="text-sm font-medium text-ink">{block.title}</div>
        {block.transcript && (
          <button onClick={() => setShowTranscript((s) => !s)} className="mt-1 text-xs font-medium text-brand hover:text-brand-dark">
            {showTranscript ? "Hide transcript" : "Show transcript"}
          </button>
        )}
        {showTranscript && block.transcript && (
          <p className="mt-2 whitespace-pre-wrap text-xs leading-relaxed text-ink-muted">{block.transcript}</p>
        )}
      </div>
    </figure>
  );
}
