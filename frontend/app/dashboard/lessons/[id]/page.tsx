"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import ReactMarkdown from "react-markdown";
import { api } from "@/lib/api";
import type { LessonDetail } from "@/lib/types";
import { segmentBlocks } from "@/lib/lessonSections";
import { LessonBlockView } from "@/components/lesson-blocks/LessonBlockView";

export default function LessonPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [lesson, setLesson] = useState<LessonDetail | null>(null);
  const [error, setError] = useState("");
  const [completing, setCompleting] = useState(false);
  const [cardIndex, setCardIndex] = useState(0);
  const [direction, setDirection] = useState<1 | -1>(1);

  const load = useCallback(async () => {
    try {
      const l = await api.getLesson(Number(params.id));
      setLesson(l);
      setCardIndex(0);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load this lesson.");
    }
  }, [params.id]);

  useEffect(() => {
    load();
  }, [load]);

  const sections = useMemo(() => (lesson ? segmentBlocks(lesson.content_blocks) : []), [lesson]);
  const lastCard = sections.length - 1;

  const goTo = useCallback((next: number) => {
    setCardIndex((current) => {
      const clamped = Math.max(0, Math.min(next, sections.length - 1));
      setDirection(clamped >= current ? 1 : -1);
      return clamped;
    });
  }, [sections.length]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (sections.length === 0) return;
      if (e.key === "ArrowRight") goTo(cardIndex + 1);
      if (e.key === "ArrowLeft") goTo(cardIndex - 1);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [sections.length, cardIndex, goTo]);

  async function complete() {
    if (!lesson || lesson.completed) return;
    setCompleting(true);
    try {
      await api.completeLesson(lesson.id);
      await load();
    } finally {
      setCompleting(false);
    }
  }

  if (error) return <main className="px-6 py-12 text-sm text-red-600">{error}</main>;
  if (!lesson) return <main className="px-6 py-12 text-sm text-ink-muted">Loading...</main>;

  return (
    <main className="mx-auto max-w-2xl px-6 py-12">
      <button onClick={() => router.back()} className="text-xs text-ink-muted hover:text-ink">
        ← Back
      </button>

      <div className="mt-4 flex items-start justify-between gap-4">
        <div>
          {lesson.module_title && (
            <div className="mb-1 text-xs font-medium uppercase tracking-wide text-brand">{lesson.module_title}</div>
          )}
          <h1 className="text-2xl font-semibold">{lesson.title}</h1>
          <p className="mt-1 text-xs text-ink-muted">{lesson.estimated_minutes} min</p>
        </div>
        {lesson.completed && <span className="shrink-0 text-sm font-medium text-emerald-600">✓ Completed</span>}
      </div>

      {sections.length > 0 ? (
        <div className="mt-8">
          <div className="mb-4 flex items-center gap-2">
            {sections.map((_, i) => (
              <button
                key={i}
                onClick={() => goTo(i)}
                aria-label={`Go to card ${i + 1}`}
                className={[
                  "h-1.5 flex-1 rounded-full transition-colors",
                  i === cardIndex ? "bg-brand" : i < cardIndex ? "bg-brand/40" : "bg-line",
                ].join(" ")}
              />
            ))}
          </div>
          <p className="mb-4 text-xs font-medium text-ink-muted">
            Card {cardIndex + 1} of {sections.length}
          </p>

          <div className="overflow-hidden">
            <section
              key={cardIndex}
              className={[
                "rounded-2xl border border-line bg-white p-6 shadow-sm sm:p-8",
                direction === 1 ? "animate-card-in-right" : "animate-card-in-left",
              ].join(" ")}
            >
              {sections[cardIndex].title !== "Introduction" && (
                <h2 className="mb-4 text-lg font-semibold text-ink">{sections[cardIndex].title}</h2>
              )}
              <div className="space-y-4">
                {sections[cardIndex].blocks.map((block, j) => (
                  <LessonBlockView key={j} block={block} />
                ))}
              </div>
            </section>
          </div>

          <div className="mt-5 flex items-center justify-between gap-3">
            <button
              onClick={() => goTo(cardIndex - 1)}
              disabled={cardIndex === 0}
              className="rounded-lg border border-line px-4 py-2 text-sm font-medium text-ink disabled:opacity-30"
            >
              ← Previous
            </button>

            {cardIndex === lastCard ? (
              !lesson.completed && (
                <button
                  onClick={complete}
                  disabled={completing}
                  className="rounded-lg bg-brand px-4 py-2 text-sm font-medium disabled:opacity-40"
                >
                  {completing ? "..." : "Mark complete"}
                </button>
              )
            ) : (
              <button onClick={() => goTo(cardIndex + 1)} className="rounded-lg bg-brand px-4 py-2 text-sm font-medium">
                Next →
              </button>
            )}
          </div>
        </div>
      ) : lesson.content_markdown ? (
        <article className="prose prose-slate mt-8 max-w-none prose-headings:font-semibold prose-a:text-brand">
          <ReactMarkdown>{lesson.content_markdown}</ReactMarkdown>
        </article>
      ) : (
        <p className="mt-8 text-sm text-ink-muted">
          This lesson doesn&apos;t have content yet -- run{" "}
          <code className="rounded bg-surface px-1.5 py-0.5">python scripts/generate_lesson_content.py</code> on the backend.
        </p>
      )}
    </main>
  );
}
