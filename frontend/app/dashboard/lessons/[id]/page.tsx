"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import ReactMarkdown from "react-markdown";
import { api } from "@/lib/api";
import type { LessonDetail } from "@/lib/types";

export default function LessonPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [lesson, setLesson] = useState<LessonDetail | null>(null);
  const [error, setError] = useState("");
  const [completing, setCompleting] = useState(false);

  const load = useCallback(async () => {
    try {
      const l = await api.getLesson(Number(params.id));
      setLesson(l);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load this lesson.");
    }
  }, [params.id]);

  useEffect(() => {
    load();
  }, [load]);

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

  if (error) return <main className="px-6 py-12 text-sm text-red-400">{error}</main>;
  if (!lesson) return <main className="px-6 py-12 text-sm text-slate-500">Loading...</main>;

  return (
    <main className="mx-auto max-w-2xl px-6 py-12">
      <button onClick={() => router.back()} className="text-xs text-slate-500 hover:text-slate-300">
        ← Back
      </button>

      <div className="mt-4 flex items-start justify-between gap-4">
        <div>
          {lesson.module_title && (
            <div className="mb-1 text-xs font-medium uppercase tracking-wide text-brand">{lesson.module_title}</div>
          )}
          <h1 className="text-2xl font-semibold">{lesson.title}</h1>
          <p className="mt-1 text-xs text-slate-500">{lesson.estimated_minutes} min read</p>
        </div>
        {lesson.completed ? (
          <span className="shrink-0 text-sm font-medium text-emerald-400">✓ Completed</span>
        ) : (
          <button
            onClick={complete}
            disabled={completing}
            className="shrink-0 rounded-lg bg-brand px-4 py-2 text-sm font-medium disabled:opacity-40"
          >
            {completing ? "..." : "Mark complete"}
          </button>
        )}
      </div>

      {lesson.content_markdown ? (
        <article className="prose prose-invert prose-slate mt-8 max-w-none prose-headings:font-semibold prose-a:text-brand">
          <ReactMarkdown>{lesson.content_markdown}</ReactMarkdown>
        </article>
      ) : (
        <p className="mt-8 text-sm text-slate-500">
          This lesson doesn&apos;t have content yet -- run{" "}
          <code className="rounded bg-slate-900 px-1.5 py-0.5">python scripts/generate_lesson_content.py</code> on the backend.
        </p>
      )}
    </main>
  );
}
