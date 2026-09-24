"use client";

import Link from "next/link";
import { PipelineMap, type Stage } from "@/components/explore/PipelineMap";
import { LanguageModelHero } from "@/components/explore/LanguageModelHero";
import { SlidePanel } from "@/components/explore/SlidePanel";
import { TokenizerDemo } from "@/components/explore/TokenizerDemo";
import { EmbeddingSpaceDemo } from "@/components/explore/EmbeddingSpaceDemo";
import { NextTokenDemo } from "@/components/explore/NextTokenDemo";
import { AttentionIllustration } from "@/components/explore/AttentionIllustration";
import { useSlidePanel } from "@/lib/useSlidePanel";

const COPY: Record<Stage, { title: string; body: string[] }> = {
  input: {
    title: "0 · Your text",
    body: [
      'This is the model\'s entire working world for this response: "After the meeting got rescheduled to 3pm, Maria finally sent the proposal." No memory of yesterday, nothing but this text.',
      "Every other stage in the diagram is a transformation applied to it, in order. Click through them -- tokens, embeddings, attention, prediction -- to see each one.",
    ],
  },
  tokens: {
    title: "1 · Tokens",
    body: [
      "The model can't read letters or words. Everything gets carved into tokens -- chunks from a fixed vocabulary of tens of thousands of pieces, each swapped for an ID number. Common short words get their own chunk; rarer material gets built from two or three smaller pieces, the way an unusual LEGO shape needs several studs instead of one custom brick.",
      'Watch "3pm" and "rescheduled" splinter below while "the" and "to" stay whole.',
    ],
  },
  embeddings: {
    title: "2 · Embeddings",
    body: [
      'Every token ID gets swapped again -- for a long list of numbers, a vector, acting as an address in an invisible space of meaning. Nobody hand-designed these addresses; they emerged from training. It\'s also why "king" - "man" + "woman" lands almost exactly on "queen."',
      "Below are five real words from Maria's setting, plus a deliberate outsider. Plot them and see which two the model's own math calls nearest.",
    ],
  },
  attention: {
    title: "3 · Attention",
    body: [
      'A word\'s address isn\'t fixed. "Proposal" means something different next to "sent" than next to "got down on one knee." Neighboring words pull a token\'s vector toward a different region of meaning-space -- a weighted vote, for every word, over every other word in the sentence.',
      "The shift is easiest to see when it's dramatic, so this one swaps sentences for a moment -- back to Maria's next door.",
    ],
  },
  prediction: {
    title: "4 · Prediction",
    body: [
      "Only now does the model do the one thing it was trained for: given everything so far -- tokens, addressed, adjusted for context -- produce a probability for every token in its vocabulary, pick one, and glue it on.",
      'The real sentence ended with "...sent the proposal." See if the live model agrees below -- click "Predict again" to watch it sample a different plausible answer each time.',
    ],
  },
  loop: {
    title: "↩ The loop back",
    body: [
      'The predicted token doesn\'t end the process. It gets appended to the input, and the entire pipeline -- tokenize, embed, attend, predict -- runs again on the now slightly longer text. "...sent the proposal" becomes the new "everything so far."',
      "A whole streamed reply, appearing word by word, is exactly this loop running a few dozen times a second -- each turn only able to see back as far as the model's context window allows.",
    ],
  },
};

export default function LanguageModelLoopPage() {
  const { panel, open, close } = useSlidePanel<Stage>();
  const copy = panel.stage ? COPY[panel.stage] : null;

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <div className="flex items-center justify-between text-xs text-ink-muted">
        <Link href="/dashboard/common-core" className="hover:text-ink">
          ← Back
        </Link>
        <Link href="/dashboard/explore/language-model" className="hover:text-ink">
          Prefer to read top to bottom? See the linear version →
        </Link>
      </div>

      <div className="mt-4 text-xs font-medium uppercase tracking-wide text-brand">Explore · map view</div>
      <h1 className="mt-1 text-3xl font-semibold">What a Language Model Actually Does</h1>

      {/* Part 1: what it is, in a graphic */}
      <section className="mt-8">
        <h2 className="text-lg font-semibold text-ink">What it is</h2>
        <div className="mt-3">
          <LanguageModelHero />
        </div>
      </section>

      {/* Part 2: how the workflow works -- click a stage, its detail slides in from the side */}
      <section className="mt-10">
        <h2 className="text-lg font-semibold text-ink">How it actually works</h2>
        <p className="mt-2 text-sm text-ink-muted">
          Open up that one box and there are four steps inside, run on the same sentence every time. Click any stage below -- including "Your
          text" -- and its explanation slides in beside the diagram. Click another and it moves to the other side. "Back" closes it.
        </p>

        <div className="mt-6 overflow-x-auto rounded-xl border border-line bg-surface p-4">
          <PipelineMap active={panel.visible ? panel.stage : null} onSelect={open} />
        </div>
      </section>

      {/* the floating detail panel -- position alternates left/right on each new selection */}
      <SlidePanel visible={panel.visible} side={panel.side} onBack={close}>
        {copy && (
          <>
            <h3 className="mt-2 text-lg font-semibold text-ink">{copy.title}</h3>
            {copy.body.map((p, i) => (
              <p key={i} className="mt-2 text-sm text-ink-muted">
                {p}
              </p>
            ))}
            <div className="mt-4">
              {panel.stage === "tokens" && <TokenizerDemo />}
              {panel.stage === "embeddings" && <EmbeddingSpaceDemo />}
              {panel.stage === "attention" && <AttentionIllustration />}
              {panel.stage === "prediction" && <NextTokenDemo />}
              {panel.stage === "loop" && (
                <button onClick={() => open("prediction")} className="text-sm font-medium text-amber-700 hover:text-amber-900">
                  ↦ Jump to Prediction and click "Predict again" a few times to feel it
                </button>
              )}
            </div>
          </>
        )}
      </SlidePanel>
    </main>
  );
}
