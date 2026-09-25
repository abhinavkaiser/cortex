"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import type { CourseDetail } from "@/lib/types";
import { formatDuration } from "@/lib/format";

export default function CourseDetailPage() {
  const params = useParams<{ slug: string }>();
  const router = useRouter();
  const [course, setCourse] = useState<CourseDetail | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setCourse(await api.getCourse(params.slug));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load this course.");
    }
  }, [params.slug]);

  useEffect(() => {
    load();
  }, [load]);

  async function enroll() {
    if (!course) return;
    setBusy(true);
    try {
      await api.enrollInCourse(course.id);
      await load();
    } finally {
      setBusy(false);
    }
  }

  if (error) return <main className="px-6 py-12 text-sm text-red-600">{error}</main>;
  if (!course) return <main className="px-6 py-12 text-sm text-ink-muted">Loading...</main>;

  return (
    <main className="mx-auto max-w-2xl px-6 py-12">
      <button onClick={() => router.push("/dashboard/courses")} className="text-xs text-ink-muted hover:text-ink">
        &larr; All courses
      </button>

      <div className="mt-4 flex items-start justify-between gap-4">
        <div>
          {course.category && <div className="mb-1 text-xs font-medium uppercase tracking-wide text-brand">{course.category}</div>}
          <h1 className="text-2xl font-semibold">{course.title}</h1>
          <p className="mt-1 text-sm text-ink-muted">{course.description}</p>
          <p className="mt-1 text-xs font-medium text-ink-muted">⏱ {formatDuration(course.estimated_total_minutes)} total</p>
        </div>
        {!course.enrolled && (
          <button onClick={enroll} disabled={busy} className="shrink-0 rounded-lg bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-brand-dark disabled:opacity-40">
            {busy ? "..." : "Enroll"}
          </button>
        )}
      </div>

      {course.enrolled && (
        <div className="mt-6">
          <div className="h-2 w-full overflow-hidden rounded-full bg-line">
            <div className="h-full bg-brand transition-all" style={{ width: `${course.progress_pct ?? 0}%` }} />
          </div>
          <p className="mt-2 text-sm text-ink-muted">{course.progress_pct ?? 0}% complete</p>
        </div>
      )}

      {course.completed_at && course.certificate_code && (
        <div className="mt-6 rounded-xl border border-emerald-500/30 bg-emerald-50 p-4">
          <div className="text-sm font-medium text-emerald-700">Course completed -- certificate earned</div>
          <Link href={`/certificates/verify/${course.certificate_code}`} className="mt-1 inline-block text-xs font-medium text-brand hover:text-brand-dark">
            View your certificate &rarr;
          </Link>
        </div>
      )}

      <div className="mt-8 space-y-8">
        {course.chapters.map((chapter, i) => (
          <div key={chapter.id}>
            <div className="mb-2 flex items-baseline justify-between">
              <h2 className="text-sm font-semibold text-ink">
                Chapter {i + 1}: {chapter.title}
              </h2>
              <span className="text-xs text-ink-muted">
                {chapter.lessons.filter((l) => l.completed).length} / {chapter.lessons.length}
              </span>
            </div>
            {chapter.objective && <p className="mb-2 text-xs text-ink-muted">{chapter.objective}</p>}

            <div className="space-y-2">
              {chapter.lessons.map((lesson) => (
                <Link
                  key={lesson.id}
                  href={`/dashboard/lessons/${lesson.id}`}
                  className={`flex items-center justify-between rounded-lg border px-4 py-3 transition hover:border-brand/40 ${
                    lesson.completed ? "border-line bg-surface" : "border-line"
                  }`}
                >
                  <div>
                    <div className={`text-sm font-medium ${lesson.completed ? "text-ink-muted line-through" : "text-ink"}`}>{lesson.title}</div>
                    <div className="text-xs text-ink-muted">{lesson.estimated_minutes} min</div>
                  </div>
                  {lesson.completed ? (
                    <span className="shrink-0 text-xs font-medium text-emerald-600">&#10003; Done</span>
                  ) : (
                    <span className="shrink-0 text-xs font-medium text-brand">Read &rarr;</span>
                  )}
                </Link>
              ))}

              {chapter.quiz && (
                <Link
                  href={`/dashboard/courses/${course.slug}/quiz/${chapter.quiz.id}`}
                  className="flex items-center justify-between rounded-lg border border-dashed border-line px-4 py-3 transition hover:border-brand/40"
                >
                  <div>
                    <div className="text-sm font-medium text-ink">{chapter.quiz.title}</div>
                    <div className="text-xs text-ink-muted">
                      {chapter.quiz.question_count} questions &middot; {chapter.quiz.passing_score}% to pass
                    </div>
                  </div>
                  {chapter.quiz.passed ? (
                    <span className="shrink-0 text-xs font-medium text-emerald-600">&#10003; Passed ({chapter.quiz.best_score}%)</span>
                  ) : chapter.quiz.best_score !== null ? (
                    <span className="shrink-0 text-xs font-medium text-amber-700">Retake ({chapter.quiz.best_score}%)</span>
                  ) : (
                    <span className="shrink-0 text-xs font-medium text-brand">Take Quiz &rarr;</span>
                  )}
                </Link>
              )}
            </div>
          </div>
        ))}
      </div>
    </main>
  );
}
