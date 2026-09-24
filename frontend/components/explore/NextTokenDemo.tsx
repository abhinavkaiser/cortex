"use client";

import { useState } from "react";
import { api } from "@/lib/api";

const DEFAULT_PREFIX = "After the meeting got rescheduled to 3pm, Maria finally sent the";

export function NextTokenDemo() {
  const [prefix, setPrefix] = useState(DEFAULT_PREFIX);
  const [completions, setCompletions] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function predict() {
    if (!prefix.trim()) return;
    setLoading(true);
    setError("");
    try {
      const res = await api.completeText(prefix);
      setCompletions((prev) => [res.completion, ...prev].slice(0, 4));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not reach the backend.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-xl border border-line bg-surface p-5">
      <textarea
        value={prefix}
        onChange={(e) => {
          setPrefix(e.target.value.slice(0, 300));
          setCompletions([]);
        }}
        rows={2}
        className="w-full resize-none rounded-lg border border-line bg-white px-3 py-2 text-sm text-ink focus:border-brand focus:outline-none"
      />
      <button
        onClick={predict}
        disabled={loading || !prefix.trim()}
        className="mt-3 rounded-lg bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-brand-dark disabled:opacity-50"
      >
        {loading ? "Thinking..." : completions.length ? "Predict again" : "Predict what comes next"}
      </button>
      {error && <p className="mt-2 text-sm text-rose-600">{error}</p>}

      {completions.length > 0 && (
        <div className="mt-4 space-y-2">
          {completions.map((c, i) => (
            <p key={i} className={`rounded-lg px-3 py-2 text-sm ${i === 0 ? "bg-brand/10 text-ink ring-1 ring-brand/30" : "bg-surface text-ink-muted"}`}>
              <span className="text-ink-muted">{prefix} </span>
              <span className="font-medium">{c}</span>
            </p>
          ))}
        </div>
      )}
      {completions.length > 1 && (
        <p className="mt-2 text-xs text-ink-muted">
          Notice the completions aren't identical. The model isn't looking up "the" answer -- at each step it holds a probability over every
          possible next token and samples from it, which is why the same prefix can continue differently each time.
        </p>
      )}
      <p className="mt-3 text-xs text-ink-muted">
        This is a real, live completion from the local model running this app -- not a script or a canned response. What you can't see here is
        the actual probability number behind each candidate word; that layer isn't exposed by this interface, only the words it settled on.
      </p>
    </div>
  );
}
