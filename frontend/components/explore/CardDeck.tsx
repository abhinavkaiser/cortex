"use client";

import { useState } from "react";
import type { ReactNode } from "react";
import type { CardSlide } from "@/lib/cardSlides";

interface CardDeckProps {
  slides: CardSlide[];
  index: number;
  onNavigate: (index: number) => void;
  children: ReactNode;
}

const FLIP_MS = 220;

// A literal flip transition, not a fade/slide -- the whole point is that
// moving between cards should feel like flipping through a stack, not
// jumping around a document. The jump-strip and prev/next controls live
// INSIDE this component, fixed to the card itself, so they're reachable no
// matter how far the card's own content has scrolled -- no trip back to a
// page-level nav needed to go to the next thing.
//
// The card itself is a fixed height (not content-fit) so every card in the
// deck is visually identical regardless of how much it holds -- content
// that doesn't fill it just leaves room, content that's too long scrolls
// internally as a fallback (shouldn't happen often given how slides are
// split, see lib/cardSlides.ts).
export function CardDeck({ slides, index, onNavigate, children }: CardDeckProps) {
  const [flipping, setFlipping] = useState<"out" | "in" | null>(null);

  function go(next: number) {
    if (next < 0 || next >= slides.length || next === index || flipping) return;
    setFlipping("out");
    setTimeout(() => {
      onNavigate(next);
      setFlipping("in");
      setTimeout(() => setFlipping(null), FLIP_MS);
    }, FLIP_MS);
  }

  // Group slides by topic for the jump-strip -- clicking a bar jumps to
  // that topic's first slide, but Previous/Next still step through every
  // individual slide, including the finer sub-slides within one topic.
  const topics: { topicIndex: number; title: string; firstSlide: number; slideCount: number }[] = [];
  slides.forEach((s, i) => {
    const last = topics[topics.length - 1];
    if (last && last.topicIndex === s.topicIndex) last.slideCount++;
    else topics.push({ topicIndex: s.topicIndex, title: s.topicTitle, firstSlide: i, slideCount: 1 });
  });
  const currentTopic = topics.find((t) => t.topicIndex === slides[index]?.topicIndex);
  const slideWithinTopic = currentTopic ? index - currentTopic.firstSlide + 1 : 1;

  return (
    <div className="mx-auto max-w-2xl" style={{ perspective: "1600px" }}>
      <div className="mb-3 flex flex-wrap gap-1.5">
        {topics.map((t) => (
          <button
            key={t.topicIndex}
            onClick={() => go(t.firstSlide)}
            title={t.title}
            className={`h-1.5 flex-1 rounded-full transition-colors ${
              t.topicIndex === slides[index]?.topicIndex ? "bg-brand" : "bg-line hover:bg-gray-300"
            }`}
          />
        ))}
      </div>

      <div
        className="flex h-[68vh] flex-col rounded-2xl border border-line bg-surface shadow-xl transition-all duration-200 ease-in-out"
        style={{
          transformStyle: "preserve-3d",
          transform: flipping === "out" ? "rotateY(-90deg)" : "rotateY(0deg)",
          opacity: flipping === "out" ? 0 : 1,
        }}
      >
        <div className="flex-1 overflow-y-auto p-6">
          <div className="text-xs font-medium uppercase tracking-wide text-brand">
            Topic {(currentTopic ? topics.indexOf(currentTopic) : 0) + 1} / {topics.length}
            {currentTopic && currentTopic.slideCount > 1 ? ` · ${slideWithinTopic}/${currentTopic.slideCount}` : ""}
          </div>
          <h2 className="mt-1 text-xl font-semibold text-ink">{slides[index]?.topicTitle}</h2>
          <div className="mt-4 space-y-4">{children}</div>
        </div>

        {/* nav footer -- outside the scrolling area, so it's always in reach */}
        <div className="flex items-center justify-between border-t border-line px-4 py-3">
          <button
            onClick={() => go(index - 1)}
            disabled={index === 0}
            className="rounded-lg px-3 py-1.5 text-sm font-medium text-ink-muted hover:bg-gray-100 disabled:opacity-30"
          >
            ← Previous
          </button>
          <span className="text-xs text-ink-muted">Click a bar above, or flip through</span>
          <button
            onClick={() => go(index + 1)}
            disabled={index === slides.length - 1}
            className="rounded-lg bg-brand px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-dark disabled:opacity-30"
          >
            Next →
          </button>
        </div>
      </div>
    </div>
  );
}
