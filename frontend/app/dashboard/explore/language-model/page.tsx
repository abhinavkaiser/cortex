"use client";

import Link from "next/link";
import { TokenizerDemo } from "@/components/explore/TokenizerDemo";
import { EmbeddingSpaceDemo } from "@/components/explore/EmbeddingSpaceDemo";
import { NextTokenDemo } from "@/components/explore/NextTokenDemo";
import { AttentionIllustration } from "@/components/explore/AttentionIllustration";

export default function LanguageModelExplainerPage() {
  return (
    <main className="mx-auto max-w-2xl px-6 py-12">
      <div className="flex items-center justify-between text-xs text-ink-muted">
        <Link href="/dashboard/courses/ai-fundamentals" className="hover:text-ink">
          ← Back
        </Link>
        <Link href="/dashboard/explore/language-model-loop" className="hover:text-ink">
          Prefer a diagram you click through? See the map view →
        </Link>
      </div>

      <div className="mt-4 text-xs font-medium uppercase tracking-wide text-brand">Explore</div>
      <h1 className="mt-1 text-3xl font-semibold">What a Language Model Actually Does</h1>
      <p className="mt-3 text-ink-muted">
        You type a sentence into a chatbot, hit enter, and a few seconds later words appear that feel almost like they understand you. There's
        no separate "understanding" module in there, no lookup table, no hidden reasoning step you can't see. There are four ideas, stacked on
        top of each other, running on the same short sentence over and over. We'll follow one real sentence -- <em>"After the meeting got
        rescheduled to 3pm, Maria finally sent the proposal."</em> -- through all four, so you can watch each stage hand its output to the
        next one instead of treating them as four separate tricks.
      </p>

      {/* Step 1: tokenization */}
      <section className="mt-12">
        <h2 className="text-xl font-semibold">1. First: it can't actually read</h2>
        <p className="mt-2 text-ink-muted">
          Not the way you're reading this. A language model never sees letters or words directly -- it sees <em>tokens</em>: chunks of text,
          each one swapped for an ID number before anything else happens. The chunking comes from a fixed vocabulary of tens of thousands of
          possible pieces, learned once ahead of time by scanning enormous amounts of text and noticing which byte sequences show up together
          constantly. Think of it like a box of LEGO bricks: extremely common shapes ("the," "ing," "tion") get their own single brick, because
          they appeared so often during that scan that giving them a dedicated piece pays for itself. Rarer shapes -- a name, a typo, a number,
          a word from another language -- don't get a brick of their own, so the model has to build them out of two or three smaller,
          more generic studs instead.
        </p>
        <p className="mt-2 text-ink-muted">
          Below is our sentence about Maria's proposal, already loaded in. Notice "3pm" and "rescheduled" splinter into multiple pieces while
          short common words like "the" and "to" stay whole -- that split isn't random, it's a direct fingerprint of what was and wasn't common
          in the data this particular tokenizer was built from.
        </p>
        <div className="mt-4">
          <TokenizerDemo />
        </div>
      </section>

      {/* Step 2: embeddings */}
      <section className="mt-12">
        <h2 className="text-xl font-semibold">2. Then: those chunks become points in space</h2>
        <p className="mt-2 text-ink-muted">
          Every one of the token IDs from step 1 gets swapped again -- this time for a long list of numbers, a vector, that acts as its
          address in a huge, invisible space of meaning. Nobody hand-designed these addresses. They fell out of training: the model was
          shown a staggering amount of text and nudged, over and over, to place words that appear in similar contexts near each other. That
          process is also why the famous party trick works -- take the address for "king," subtract "man," add "woman," and you land almost
          exactly on "queen." The arithmetic isn't programmed in; it's a side effect of the geometry that emerges from the training data.
        </p>
        <p className="mt-2 text-ink-muted">
          Below are five real words pulled straight from Maria's sentence and its setting -- "meeting," "proposal," "deadline," "calendar,"
          and, as a deliberate outsider, "coffee." Plot them and look at which two the model's own math calls closest, and which two it calls
          farthest apart. You're not reading a canned example -- that's a live 384-number vector for each word, computed on this machine right
          now, just flattened to 2D so it fits on your screen.
        </p>
        <div className="mt-4">
          <EmbeddingSpaceDemo />
        </div>
      </section>

      {/* Step 3: attention (moved before prediction so the "assemble everything, then predict" order matches how the model actually processes) */}
      <section className="mt-12">
        <h2 className="text-xl font-semibold">3. But a word's meaning isn't fixed -- it bends around its neighbors</h2>
        <p className="mt-2 text-ink-muted">
          Here's a wrinkle step 2 glossed over: a word doesn't get one permanent address and keep it forever. "Proposal" means something
          slightly different in "Maria sent the proposal" than it does in "he got down on one knee with a proposal" -- same token, same
          starting vector, but the surrounding words pull it toward a different region of meaning-space before the model uses it for anything.
          The mechanism that does this pulling is called <em>attention</em>, and it's easiest to see with an example where the shift is dramatic
          rather than subtle. So for a moment, let's swap sentences -- we'll come straight back to Maria's proposal in step 4.
        </p>
        <div className="mt-4">
          <AttentionIllustration />
        </div>
      </section>

      {/* Step 4: next-token prediction */}
      <section className="mt-12">
        <h2 className="text-xl font-semibold">4. Now do the actual job: guess what comes next</h2>
        <p className="mt-2 text-ink-muted">
          Back to Maria. Every token has an address (step 2), and every address has just been adjusted to account for its neighbors (step 3).
          Only now does the model do the one thing it was ever trained to do: given everything so far, produce a probability for literally
          every token in its vocabulary -- tens of thousands of candidates, each scored -- pick one, glue it onto the end, and treat the
          slightly longer text as the new "everything so far" for the next round. There's no separate planning phase where it decides the
          whole sentence in advance. A fluent paragraph is just this single step, "guess the next chunk," repeated a few dozen times a
          second.
        </p>
        <p className="mt-2 text-ink-muted">
          The sentence really did end with "...finally sent the <strong>proposal</strong>." See if the model's own live guess below lands on
          the same word -- and if it doesn't, that's not a failure, it's the point: there is rarely one "correct" next word, only more and less
          plausible ones, and the model is sampling from a genuine spread of good options, not recalling a fact.
        </p>
        <div className="mt-4">
          <NextTokenDemo />
        </div>
      </section>

      {/* Wrap-up */}
      <section className="mt-12 rounded-xl border border-brand/30 bg-brand/10 p-5">
        <h2 className="text-lg font-semibold">The whole trip, back to back</h2>
        <p className="mt-2 text-sm text-ink-muted">
          "After the meeting got rescheduled to 3pm, Maria finally sent the proposal" arrives as raw characters. It gets carved into a
          dozen-ish tokens, each swapped for a numeric ID (step 1). Each ID becomes a vector -- a coordinate in meaning-space shaped by
          everything the model was ever trained on (step 2). Attention then lets every token adjust its vector by consulting every other
          token in the sentence, the way "proposal" would shift depending on whether the surrounding words were about work or romance (step
          3). Only then does the model use that fully-adjusted representation to score every possible next token and sample one (step 4).
          Then -- and this is the part that's easy to miss -- it does the entire four-step trip again, on the now-slightly-longer text,
          to produce the token after that. Every word you've ever seen a chatbot generate is this loop, running in real time.
        </p>
      </section>
    </main>
  );
}
