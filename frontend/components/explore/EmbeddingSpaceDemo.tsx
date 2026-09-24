"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { EmbedResponse } from "@/lib/types";

const DEFAULT_WORDS = ["meeting", "proposal", "deadline", "calendar", "coffee"];

// Maps arbitrary PCA coordinates onto a fixed SVG viewbox with headroom,
// so points never sit flush against the edge regardless of their spread.
function toSvgCoords(points: EmbedResponse["points"]) {
  const xs = points.map((p) => p.x);
  const ys = points.map((p) => p.y);
  const minX = Math.min(...xs), maxX = Math.max(...xs);
  const minY = Math.min(...ys), maxY = Math.max(...ys);
  const spanX = maxX - minX || 1;
  const spanY = maxY - minY || 1;
  const pad = 60;
  const size = 400;
  return points.map((p) => ({
    ...p,
    sx: pad + ((p.x - minX) / spanX) * (size - 2 * pad),
    sy: pad + (size - 2 * pad) - ((p.y - minY) / spanY) * (size - 2 * pad),
  }));
}

export function EmbeddingSpaceDemo() {
  const [words, setWords] = useState<string[]>(DEFAULT_WORDS);
  const [draft, setDraft] = useState("");
  const [result, setResult] = useState<EmbedResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function plot(list: string[]) {
    if (list.length < 2) return;
    setLoading(true);
    setError("");
    try {
      const res = await api.embedWords(list);
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not reach the backend.");
    } finally {
      setLoading(false);
    }
  }

  function addWord() {
    const w = draft.trim();
    if (!w || words.length >= 8 || words.includes(w)) return;
    setWords([...words, w]);
    setDraft("");
  }

  function removeWord(w: string) {
    setWords(words.filter((x) => x !== w));
  }

  const svgPoints = result ? toSvgCoords(result.points) : [];

  return (
    <div className="rounded-xl border border-line bg-surface p-5">
      <div className="flex flex-wrap items-center gap-2">
        {words.map((w) => (
          <span key={w} className="flex items-center gap-1 rounded-full bg-line px-3 py-1 text-sm">
            {w}
            <button onClick={() => removeWord(w)} className="text-ink-muted hover:text-ink" aria-label={`remove ${w}`}>
              ×
            </button>
          </span>
        ))}
        {words.length < 8 && (
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && addWord()}
            placeholder="add a word..."
            className="w-28 rounded-full border border-line bg-white px-3 py-1 text-sm focus:border-brand focus:outline-none"
          />
        )}
      </div>

      <button
        onClick={() => plot(words)}
        disabled={loading || words.length < 2}
        className="mt-4 rounded-lg bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-brand-dark disabled:opacity-50"
      >
        {loading ? "Embedding..." : "Plot in meaning-space"}
      </button>
      {error && <p className="mt-2 text-sm text-rose-600">{error}</p>}

      {result && (
        <div className="mt-5">
          <svg viewBox="0 0 400 400" className="w-full max-w-md rounded-lg bg-white">
            {svgPoints.map((p, i) => (
              <g key={i}>
                <circle cx={p.sx} cy={p.sy} r={5} className="fill-brand" />
                <text x={p.sx + 8} y={p.sy + 4} className="fill-slate-200 text-[11px]">
                  {p.label}
                </text>
              </g>
            ))}
          </svg>
          <p className="mt-3 text-sm text-ink-muted">
            Closest in real meaning-space:{" "}
            <span className="text-ink">
              "{result.points[result.closest_pair[0]].label}" &harr; "{result.points[result.closest_pair[1]].label}"
            </span>{" "}
            (similarity {result.closest_similarity.toFixed(2)}). Farthest apart:{" "}
            <span className="text-ink">
              "{result.points[result.farthest_pair[0]].label}" &harr; "{result.points[result.farthest_pair[1]].label}"
            </span>{" "}
            ({result.farthest_similarity.toFixed(2)}).
          </p>
          <p className="mt-1 text-xs text-ink-muted">
            These are real embeddings from a local model running on this machine -- 384 real numbers per word, here squashed down to the 2
            dimensions that capture the most spread, just so it fits on screen. Closeness on this 2D plot is an approximation; the "similarity"
            numbers above are computed from the real, full 384-dimensional vectors.
          </p>
        </div>
      )}
    </div>
  );
}
