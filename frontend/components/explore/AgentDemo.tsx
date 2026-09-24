"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { AgentResponse } from "@/lib/types";

const DEFAULT_GOAL = "What is 15% of $2,400, and does that exceed our no-receipt meal limit?";

export function AgentDemo() {
  const [goal, setGoal] = useState(DEFAULT_GOAL);
  const [result, setResult] = useState<AgentResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function run() {
    if (!goal.trim()) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const res = await api.runAgent(goal);
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
        value={goal}
        onChange={(e) => {
          setGoal(e.target.value.slice(0, 300));
          setResult(null);
        }}
        rows={2}
        className="w-full resize-none rounded-lg border border-line bg-white px-3 py-2 text-sm text-ink focus:border-brand focus:outline-none"
      />
      <button
        onClick={run}
        disabled={loading || !goal.trim()}
        className="mt-3 rounded-lg bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-brand-dark disabled:opacity-50"
      >
        {loading ? "Running the loop..." : "Give it the goal"}
      </button>
      {error && <p className="mt-2 text-sm text-rose-600">{error}</p>}

      {result && (
        <div className="mt-4 space-y-2">
          {result.steps.map((s, i) =>
            s.tool ? (
              <div key={i} className="rounded-lg bg-white px-3 py-2 text-xs">
                <div className="text-amber-700">
                  <span className="font-mono">{s.tool}</span>
                  <span className="text-ink-muted"> ({s.tool_input})</span>
                </div>
                <div className="mt-1 text-ink-muted">→ {s.observation}</div>
              </div>
            ) : null
          )}
          <div className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-ink ring-1 ring-emerald-500/30">
            {result.final_answer}
          </div>
        </div>
      )}
      <p className="mt-3 text-xs text-ink-muted">
        Every line above is real: the model's actual tool choices, a real arithmetic evaluator actually running (never <code>eval()</code>,
        just a whitelisted parser), and a real lookup against the same small demo handbook from the RAG page. Nothing here is scripted.
      </p>
    </div>
  );
}
