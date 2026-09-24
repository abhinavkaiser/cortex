"use client";

import Link from "next/link";
import { RagMap, type RagStage } from "@/components/explore/RagMap";
import { RagHero } from "@/components/explore/RagHero";
import { RagDemo } from "@/components/explore/RagDemo";
import { SlidePanel } from "@/components/explore/SlidePanel";
import { useSlidePanel } from "@/lib/useSlidePanel";

const COPY: Record<RagStage, { title: string; body: string[] }> = {
  question: {
    title: "0 · Your question",
    body: [
      'A plain question -- "Do I need a receipt for a $50 lunch?" On its own, a base language model has no way to answer this correctly. It was trained on a huge slice of the public internet, not on your company\'s expense policy, so at best it can guess at what\'s typical.',
      'Click "Retrieval" to see the fix.',
    ],
  },
  retrieval: {
    title: "1 · Retrieval",
    body: [
      "Before the model answers anything, your question gets embedded -- turned into the exact same kind of meaning-vector from the tokenizer/embeddings explainer -- and compared against every document in your own store the same way, using real cosine similarity, not keyword matching.",
      'The documents whose vectors land closest to the question\'s vector get pulled out and handed to the model as extra context, on top of the question. "Receipt" and "$50" never need to appear verbatim anywhere -- the match is on meaning, not exact words.',
      'Click "Grounding" to search the demo\'s document set live and see exactly what gets pulled.',
    ],
  },
  grounding: {
    title: "2 · Grounding",
    body: [
      "Now the model answers twice, back to back, on the exact same question -- once with nothing but general training knowledge, once with the retrieved excerpt stuffed into its context. Compare them below.",
      "This is the entire idea behind RAG in one comparison: the model's reasoning ability doesn't change at all between the two answers. What changes is whether it was handed the one fact it actually needed.",
    ],
  },
};

export default function RagExplainerPage() {
  const { panel, open, close } = useSlidePanel<RagStage>();
  const copy = panel.stage ? COPY[panel.stage] : null;

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <div className="flex items-center justify-between text-xs text-ink-muted">
        <Link href="/dashboard/common-core" className="hover:text-ink">
          ← Back
        </Link>
        <Link href="/dashboard/explore/language-model-loop" className="hover:text-ink">
          ← What a Language Model Actually Does
        </Link>
      </div>

      <div className="mt-4 text-xs font-medium uppercase tracking-wide text-brand">Explore · map view</div>
      <h1 className="mt-1 text-3xl font-semibold">What Retrieval-Augmented Generation (RAG) Actually Does</h1>

      <section className="mt-8">
        <h2 className="text-lg font-semibold text-ink">What it is</h2>
        <div className="mt-3">
          <RagHero />
        </div>
      </section>

      <section className="mt-10">
        <h2 className="text-lg font-semibold text-ink">How it actually works</h2>
        <p className="mt-2 text-sm text-ink-muted">
          The language model underneath is unchanged from before -- same tokenize, embed, attend, predict loop. RAG adds one thing in front
          of it: a real search over your own documents. Click a stage below to see each part, including a live search over a small demo
          document set.
        </p>

        <div className="mt-6 overflow-x-auto rounded-xl border border-line bg-surface p-4">
          <RagMap active={panel.visible ? panel.stage : null} onSelect={open} />
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
            <div className="mt-4">{panel.stage === "grounding" && <RagDemo />}</div>
          </>
        )}
      </SlidePanel>
    </main>
  );
}
