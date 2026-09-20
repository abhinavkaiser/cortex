"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { SandboxResult } from "@/lib/types";
import { ParamControls } from "./ParamControls";
import { TokenCostMeter } from "./TokenCostMeter";

const DEFAULT_PARAMS = {
  model: "claude-sonnet-4-6",
  temperature: 0.7,
  top_p: 0.95,
  max_output_tokens: 1024,
};

export function PromptPlayground() {
  const [prompt, setPrompt] = useState("");
  const [params, setParams] = useState(DEFAULT_PARAMS);
  const [result, setResult] = useState<SandboxResult | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");

  async function run() {
    if (!prompt.trim() || running) return;
    setRunning(true);
    setError("");
    setResult(null);
    try {
      const res = await api.executeSandboxPrompt({ prompt, ...params });
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Execution failed.");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="grid gap-6 md:grid-cols-[1fr_280px]">
      {/* Side-by-side: prompt input + params on the left, live result on the right (below on mobile) */}
      <div className="space-y-3">
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Write a prompt to try..."
          rows={6}
          className="w-full rounded-xl border border-slate-800 bg-slate-900 p-4 text-sm"
        />
        <TokenCostMeter prompt={prompt} model={params.model} maxOutputTokens={params.max_output_tokens} />
        <button
          onClick={run}
          disabled={running || !prompt.trim()}
          className="rounded-lg bg-brand px-5 py-2.5 text-sm font-medium disabled:opacity-40"
        >
          {running ? "Running..." : "Run prompt"}
        </button>

        {error && <p className="text-sm text-red-400">{error}</p>}

        {result && (
          <div className="rounded-xl border border-slate-800 p-4">
            <div className="flex items-center justify-between text-xs text-slate-500">
              <span>
                {result.input_tokens} in / {result.output_tokens} out tokens · {result.latency_ms}ms
                {result.served_from_cache && <span className="ml-2 text-brand">· served from cache</span>}
              </span>
              <span>${result.estimated_cost_usd.toFixed(6)}</span>
            </div>
            <p className="mt-3 whitespace-pre-line text-sm leading-relaxed">{result.response_text}</p>
          </div>
        )}
      </div>

      <ParamControls params={params} onChange={setParams} />
    </div>
  );
}
