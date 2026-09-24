"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { CourseDetail, LessonDetail } from "@/lib/types";
import { segmentBlocks } from "@/lib/lessonSections";
import { toCardSlides } from "@/lib/cardSlides";
import { CardDeck } from "@/components/explore/CardDeck";
import { LessonBlockView } from "@/components/lesson-blocks/LessonBlockView";

const LESSON_TITLE = "The AI Taxonomy for Executives";

// A standalone alternate reading of one lesson -- fetches the same real
// content_blocks every other view of this lesson uses (no fork of the
// data, no hardcoded lesson id), just presents it as a flip-through card
// deck instead of a forced top-to-bottom scroll: one topic at a time,
// jump directly to any other topic without leaving the card, flip
// forward/back like a stack. Nothing here writes to the lesson, the
// module, or the curriculum -- purely a different window onto the same
// content, reachable only at this URL. Image blocks are dropped from this
// view specifically -- a full-width photo doesn't fit the card format.
export default function AiTaxonomyMapPage() {
  const [lesson, setLesson] = useState<LessonDetail | null>(null);
  const [error, setError] = useState("");
  const [index, setIndex] = useState(0);

  useEffect(() => {
    (async () => {
      try {
        // The AI Leader curriculum lives as the migrated "ai-leader" course
        // now (see scripts/migrate_tracks_to_courses.py) -- was
        // api.getCurriculum("leader") back when Leader was a Track.
        const course: CourseDetail = await api.getCourse("ai-leader");
        const match = course.chapters.flatMap((c) => c.lessons).find((l) => l.title === LESSON_TITLE);
        if (!match) {
          setError(`Could not find "${LESSON_TITLE}" in the current curriculum.`);
          return;
        }
        const full = await api.getLesson(match.id);
        setLesson(full);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Could not load this lesson.");
      }
    })();
  }, []);

  const slides = useMemo(() => {
    if (!lesson) return [];
    const sections = segmentBlocks(lesson.content_blocks).map((s) => ({
      ...s,
      blocks: s.blocks.filter((b) => b.type !== "image"),
    }));
    return toCardSlides(sections);
  }, [lesson]);

  if (error) return <main className="px-6 py-12 text-sm text-red-600">{error}</main>;
  if (!lesson) return <main className="px-6 py-12 text-sm text-ink-muted">Loading...</main>;

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <Link href="/dashboard/courses/ai-leader" className="text-xs text-ink-muted hover:text-ink">
        ← Back to AI Leader curriculum
      </Link>

      <div className="mt-4 text-xs font-medium uppercase tracking-wide text-brand">Alternate reading · card deck</div>
      <h1 className="mt-1 text-3xl font-semibold">{lesson.title}</h1>
      <p className="mt-3 max-w-2xl text-sm text-ink-muted">
        Same lesson, flipped through instead of scrolled. Tap a bar above the card to jump straight to that topic, or use Previous/Next --
        both stay with the card, so getting to the next thing never means scrolling back up.
      </p>

      <div className="mt-10">
        <CardDeck slides={slides} index={index} onNavigate={setIndex}>
          {slides[index]?.blocks.map((block, j) => <LessonBlockView key={j} block={block} />)}
        </CardDeck>
      </div>
    </main>
  );
}
