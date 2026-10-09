"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { FlashcardCard, FlashcardDeck } from "@/lib/types";

// Fisher-Yates over a copy -- shuffling must not mutate the fetched deck,
// since "Shuffle off" restores the deck's authored order.
function shuffled<T>(items: T[]): T[] {
  const out = [...items];
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}

export default function FlashcardReviewPage() {
  const params = useParams<{ slug: string; deckId: string }>();
  const router = useRouter();
  const deckId = Number(params.deckId);

  const [deck, setDeck] = useState<FlashcardDeck | null>(null);
  const [cards, setCards] = useState<FlashcardCard[]>([]);
  const [index, setIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [isShuffled, setIsShuffled] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      setError("");
      const d = await api.getFlashcardDeck(deckId);
      setDeck(d);
      setCards(d.cards);
      setIndex(0);
      setFlipped(false);
      setIsShuffled(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load this deck.");
    }
  }, [deckId]);

  useEffect(() => {
    load();
  }, [load]);

  const total = cards.length;

  // Advancing always lands on the front of the next card -- carrying a
  // flipped state across would show the answer before the question.
  const go = useCallback(
    (delta: number) => {
      setIndex((i) => Math.min(Math.max(i + delta, 0), Math.max(total - 1, 0)));
      setFlipped(false);
    },
    [total],
  );

  function toggleShuffle() {
    if (!deck) return;
    const next = !isShuffled;
    setIsShuffled(next);
    setCards(next ? shuffled(deck.cards) : deck.cards);
    setIndex(0);
    setFlipped(false);
  }

  // Keyboard review: space/enter flips, arrows move. Skipped while focus is
  // in a control so Tab-ing to a button and pressing Enter still activates
  // that button rather than flipping the card.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const el = document.activeElement;
      if (el && ["BUTTON", "INPUT", "TEXTAREA", "SELECT", "A"].includes(el.tagName)) return;
      if (e.key === " " || e.key === "Enter") {
        e.preventDefault();
        setFlipped((f) => !f);
      } else if (e.key === "ArrowRight") {
        go(1);
      } else if (e.key === "ArrowLeft") {
        go(-1);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [go]);

  if (error) return <main className="px-6 py-12 text-sm text-red-600">{error}</main>;
  if (!deck) return <main className="px-6 py-12 text-sm text-ink-muted">Loading...</main>;

  const card = cards[index];

  return (
    <main className="mx-auto max-w-2xl px-6 py-12">
      <button
        onClick={() => router.push(`/dashboard/courses/${params.slug}`)}
        className="text-xs text-ink-muted hover:text-ink"
      >
        &larr; Back to course
      </button>

      <div className="mt-4 flex items-start justify-between gap-4">
        <div>
          <div className="mb-1 text-xs font-medium uppercase tracking-wide text-brand">Flashcards</div>
          <h1 className="text-2xl font-semibold">{deck.title}</h1>
          {deck.module_title && <p className="mt-1 text-sm text-ink-muted">{deck.module_title}</p>}
        </div>
        {total > 1 && (
          <button
            onClick={toggleShuffle}
            className={`shrink-0 rounded-lg border px-3 py-2 text-sm font-medium transition ${
              isShuffled ? "border-brand bg-brand text-white" : "border-line text-ink hover:border-brand/40"
            }`}
          >
            {isShuffled ? "Shuffled" : "Shuffle"}
          </button>
        )}
      </div>

      {total === 0 ? (
        <p className="mt-8 text-sm text-ink-muted">This deck has no cards yet.</p>
      ) : (
        <>
          <div className="mt-6 flex items-center justify-between text-xs text-ink-muted">
            <span>
              Card {index + 1} of {total}
            </span>
            <span>{flipped ? "Answer" : "Tap the card to reveal"}</span>
          </div>
          <div className="mt-2 h-1 w-full overflow-hidden rounded-full bg-line">
            <div
              className="h-full bg-brand transition-all"
              style={{ width: `${((index + 1) / total) * 100}%` }}
            />
          </div>

          <button
            type="button"
            onClick={() => setFlipped((f) => !f)}
            aria-live="polite"
            className={`mt-6 flex min-h-[260px] w-full flex-col items-center justify-center rounded-xl border p-8 text-center transition ${
              flipped ? "border-brand/40 bg-surface" : "border-line bg-white hover:border-brand/40"
            }`}
          >
            <span className="mb-3 text-[11px] font-medium uppercase tracking-wide text-ink-muted">
              {flipped ? "Answer" : "Question"}
            </span>
            <span className={`whitespace-pre-wrap ${flipped ? "text-base" : "text-lg font-medium"}`}>
              {flipped ? card.back : card.front}
            </span>
          </button>

          <div className="mt-6 flex items-center justify-between gap-3">
            <button
              onClick={() => go(-1)}
              disabled={index === 0}
              className="rounded-lg border border-line px-4 py-2 text-sm font-medium text-ink transition hover:border-brand/40 disabled:opacity-30"
            >
              &larr; Previous
            </button>
            <button
              onClick={() => setFlipped((f) => !f)}
              className="rounded-lg border border-line px-4 py-2 text-sm font-medium text-ink transition hover:border-brand/40"
            >
              {flipped ? "Show question" : "Show answer"}
            </button>
            <button
              onClick={() => go(1)}
              disabled={index >= total - 1}
              className="rounded-lg bg-brand px-4 py-2 text-sm font-medium text-white transition hover:bg-brand-dark disabled:opacity-30"
            >
              Next &rarr;
            </button>
          </div>

          <p className="mt-4 text-center text-xs text-ink-muted">
            Space or Enter to flip &middot; arrow keys to move
          </p>
        </>
      )}
    </main>
  );
}
