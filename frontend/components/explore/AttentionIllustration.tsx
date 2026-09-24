"use client";

import { useState } from "react";

// A hand-authored Winograd-schema example (classic in NLP: swapping one
// word flips which earlier word a pronoun refers to). The highlight
// mapping below is authored by hand to teach the *idea* of context-
// dependent meaning -- it is explicitly NOT read from a real model's
// attention weights, and the copy says so.
const VARIANTS = {
  big: {
    words: ["The", "trophy", "doesn't", "fit", "in", "the", "suitcase", "because", "it", "is", "too", "big", "."],
    itIndex: 8,
    refersTo: 1, // "trophy"
  },
  small: {
    words: ["The", "trophy", "doesn't", "fit", "in", "the", "suitcase", "because", "it", "is", "too", "small", "."],
    itIndex: 8,
    refersTo: 6, // "suitcase"
  },
};

export function AttentionIllustration() {
  const [variant, setVariant] = useState<keyof typeof VARIANTS>("big");
  const [hovering, setHovering] = useState(false);
  const v = VARIANTS[variant];

  return (
    <div className="rounded-xl border border-line bg-surface p-5">
      <div className="flex gap-2 text-sm">
        <button
          onClick={() => setVariant("big")}
          className={`rounded-full px-3 py-1 ${variant === "big" ? "bg-brand text-white" : "bg-line text-ink-muted"}`}
        >
          "...too big."
        </button>
        <button
          onClick={() => setVariant("small")}
          className={`rounded-full px-3 py-1 ${variant === "small" ? "bg-brand text-white" : "bg-line text-ink-muted"}`}
        >
          "...too small."
        </button>
      </div>

      <p className="mt-4 flex flex-wrap gap-x-1.5 gap-y-2 text-lg leading-relaxed">
        {v.words.map((w, i) => {
          const isIt = i === v.itIndex;
          const isTarget = hovering && i === v.refersTo;
          return (
            <span
              key={i}
              onMouseEnter={() => isIt && setHovering(true)}
              onMouseLeave={() => isIt && setHovering(false)}
              className={[
                "rounded px-1 transition-colors",
                isIt ? "cursor-pointer bg-brand/20 ring-1 ring-brand/50" : "",
                isTarget ? "bg-amber-100 ring-1 ring-amber-400/60" : "",
              ].join(" ")}
            >
              {w}
            </span>
          );
        })}
      </p>
      <p className="mt-3 text-sm text-ink-muted">
        Hover <span className="rounded bg-brand/20 px-1 ring-1 ring-brand/50">"it"</span> above. One word changed at the end of the sentence
        ("big" &rarr; "small") and it flips which earlier word "it" means -- the trophy, or the suitcase. Nothing about the grammar changed;
        only the meaning did, and only because of a word eleven positions away. A model that only looked at "it" and its next-door neighbors
        would have no way to get this right -- there's nothing local to "it" that tells you which noun it points to.
      </p>
      <p className="mt-2 text-sm text-ink-muted">
        This is what attention actually computes: for every word, a weighted vote over every other word in the sentence, asking "how relevant
        are you to figuring out what I mean here?" For "it," the word "big" (or "small") ends up with a heavy vote, even though it's far away
        and grammatically unrelated. Real models don't do this once -- they run many attention "heads" in parallel per layer, each free to
        specialize in a different kind of relationship (one head might track grammatical subject/object pairs, another might track topic, a
        third pronoun reference like this one), and then stack a dozen-plus layers of this, each pass building a progressively more
        context-aware picture of what every word means <em>here</em>, in this exact sentence, not in general.
      </p>
      <p className="mt-2 text-xs text-ink-muted">
        This highlight is a hand-made illustration of the idea, not a real model's internal attention weights -- those aren't something this
        interface can read out. But the shape of the mechanism is real: whatever the model does with "it," it has to be able to look all the
        way back to "big" or "small" to do it correctly, and attention is the part of the architecture that makes that long-range lookup
        possible.
      </p>
    </div>
  );
}
