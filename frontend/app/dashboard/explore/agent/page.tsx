"use client";

import Link from "next/link";
import { AgentMap, type AgentStage } from "@/components/explore/AgentMap";
import { AgentHero } from "@/components/explore/AgentHero";
import { AgentDemo } from "@/components/explore/AgentDemo";
import { SlidePanel } from "@/components/explore/SlidePanel";
import { useSlidePanel } from "@/lib/useSlidePanel";

const COPY: Record<AgentStage, { title: string; body: string[] }> = {
  goal: {
    title: "0 · Goal",
    body: [
      '"What is 15% of $2,400, and does that exceed our no-receipt meal limit?" -- a plain language model can\'t reliably do exact arithmetic (it\'s predicting plausible-looking tokens, not running a calculator) and it doesn\'t know your policy at all. On its own, it would have to guess at both.',
      'Click "Decide" to see what an agent does instead.',
    ],
  },
  decide: {
    title: "1 · Decide",
    body: [
      'This is the exact same prediction step from the base language-model page -- given everything so far, produce the next tokens. The only difference is the instructions it\'s working under: instead of "write me a sentence," it\'s "either answer now, or say which tool you want and with what input."',
      "That's it. There's no separate \"reasoning module\" bolted on -- the model is still just predicting text, it's just been asked to predict text in a format the backend can parse as a decision.",
    ],
  },
  tools: {
    title: "2 · Real tools",
    body: [
      "Whatever the model decided, the backend actually does it -- for real, not simulated. This demo gives it exactly two whitelisted tools: a calculator (a hand-written arithmetic parser, never eval(), so it can't be tricked into running arbitrary code) and a policy lookup (the same real embedding-similarity search from the RAG page, over the same small demo handbook).",
      "The real result -- an actual computed number, an actual retrieved excerpt -- gets appended to the conversation, and control goes back to \"Decide\" with that new information available.",
    ],
  },
  loop: {
    title: "↻ The loop",
    body: [
      'This is the whole trick: decide → act → observe the real result → decide again, until the model itself says "I have enough, here\'s the answer." No fixed number of steps, no hand-written script for this specific question -- the model is choosing the path.',
      "Give it the goal below and watch every real step happen, in order, with nothing hidden.",
    ],
  },
};

export default function AgentExplainerPage() {
  const { panel, open, close } = useSlidePanel<AgentStage>();
  const copy = panel.stage ? COPY[panel.stage] : null;

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <div className="flex items-center justify-between text-xs text-ink-muted">
        <Link href="/dashboard/courses/ai-fundamentals" className="hover:text-ink">
          ← Back
        </Link>
        <Link href="/dashboard/explore/rag" className="hover:text-ink">
          ← What RAG Actually Does
        </Link>
      </div>

      <div className="mt-4 text-xs font-medium uppercase tracking-wide text-brand">Explore · map view</div>
      <h1 className="mt-1 text-3xl font-semibold">What an AI Agent Actually Does</h1>

      <section className="mt-8">
        <h2 className="text-lg font-semibold text-ink">What it is</h2>
        <div className="mt-3">
          <AgentHero />
        </div>
      </section>

      <section className="mt-10">
        <h2 className="text-lg font-semibold text-ink">How it actually works</h2>
        <p className="mt-2 text-sm text-ink-muted">
          Same language model underneath, unchanged again. An "agent" is that model wrapped in an outer loop that can trigger real actions
          and see their real results before deciding what to say next. Click a stage below -- the loop arc at the bottom holds the live demo.
        </p>

        <div className="mt-6 overflow-x-auto rounded-xl border border-line bg-surface p-4">
          <AgentMap active={panel.visible ? panel.stage : null} onSelect={open} />
        </div>
      </section>

      <SlidePanel visible={panel.visible} side={panel.side} onBack={close}>
        {copy && (
          <>
            <h3 className="mt-2 text-lg font-semibold text-ink">{copy.title}</h3>
            {copy.body.map((p, i) => (
              <p key={i} className="mt-2 text-sm text-ink-muted">
                {p}
              </p>
            ))}
            <div className="mt-4">{panel.stage === "loop" && <AgentDemo />}</div>
          </>
        )}
      </SlidePanel>
    </main>
  );
}
