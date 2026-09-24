"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { RagResponse } from "@/lib/types";

const DEFAULT_QUESTION = "Do I need a receipt for a $50 lunch?";

export function RagDemo() {
  const [question, setQuestion] = useState(DEFAULT_QUESTION);
  const [result, setResult] = useState<RagResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function ask() {
    if (!question.trim()) return;
    setLoading(true);
    setError("");
    try {
      const res = await api.ragQuery(question);
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not reach the backend.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-xl border border-line bg-surface p-5">
      <textarea
        value={question}
        onChange={(e) => {
          setQuestion(e.target.value.slice(0, 300));
          setResult(null);
        }}
        rows={2}
        className="w-full resize-none rounded-lg border border-line bg-white px-3 py-2 text-sm text-ink focus:border-brand focus:outline-none"
      />
      <button
        onClick={ask}
        disabled={loading || !question.trim()}
        className="mt-3 rounded-lg bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-brand-dark disabled:opacity-50"
      >
        {loading ? "Searching + asking twice..." : "Ask, with and without retrieval"}
      </button>
      {error && <p className="mt-2 text-sm text-rose-600">{error}</p>}

      {result && (
        <div className="mt-4 space-y-4">
          <div>
            <div className="text-xs font-medium uppercase tracking-wide text-ink-muted">Retrieved from your documents</div>
            <div className="mt-1 space-y-1.5">
              {result.retrieved.map((r, i) => (
                <p key={i} className="rounded-lg bg-white px-3 py-2 text-xs text-ink-muted">
                  <span className="mr-2 rounded bg-brand/20 px-1.5 py-0.5 font-mono text-brand">{r.similarity.toFixed(2)}</span>
                  {r.text}
                </p>
              ))}
            </div>
          </div>

          <div>
            <div className="text-xs font-medium uppercase tracking-wide text-ink-muted">Without retrieval</div>
            <p className="mt-1 rounded-lg bg-surface px-3 py-2 text-sm text-ink-muted">{result.ungrounded_answer}</p>
          </div>

          <div>
            <div className="text-xs font-medium uppercase tracking-wide text-emerald-600">With retrieval (grounded)</div>
            <p className="mt-1 rounded-lg bg-emerald-50 px-3 py-2 text-sm text-ink ring-1 ring-emerald-500/30">
              {result.grounded_answer}
            </p>
          </div>
        </div>
      )}
      <p className="mt-3 text-xs text-ink-muted">
        Both answers above are real, live calls to the same local model -- one given the retrieved excerpt, one given nothing but the
        question. The documents are a small made-up handbook for this demo, not real company policy.
      </p>
    </div>
  );
}
