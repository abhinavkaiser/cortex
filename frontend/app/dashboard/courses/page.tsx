"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { CourseSummary } from "@/lib/types";

export default function CoursesCatalogPage() {
  const [courses, setCourses] = useState<CourseSummary[] | null>(null);
  const [error, setError] = useState("");
  const [enrolling, setEnrolling] = useState<number | null>(null);

  async function load() {
    try {
      setCourses(await api.getCourses());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load courses.");
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function enroll(courseId: number) {
    setEnrolling(courseId);
    try {
      await api.enrollInCourse(courseId);
      await load();
    } finally {
      setEnrolling(null);
    }
  }

  if (error) return <main className="px-6 py-12 text-sm text-red-600">{error}</main>;
  if (!courses) return <main className="px-6 py-12 text-sm text-ink-muted">Loading...</main>;

  return (
    <main className="mx-auto max-w-5xl px-6 py-12">
      <h1 className="text-2xl font-semibold">Courses</h1>
      <p className="mt-1 text-sm text-ink-muted">
        Enroll in any course -- including AI Leader, AI Practitioner, AI Developer, and AI Fundamentals -- work through
        its chapters at your own pace, and earn a certificate on completion.
      </p>

      {courses.length === 0 ? (
        <p className="mt-8 text-sm text-ink-muted">No courses published yet.</p>
      ) : (
        <div className="mt-8 grid gap-4 sm:grid-cols-2">
          {courses.map((c) => (
            <div key={c.id} className="rounded-xl border border-line bg-surface p-5">
              <div className="flex items-start justify-between gap-2">
                <div>
                  {c.category && <div className="text-xs font-medium uppercase tracking-wide text-brand">{c.category}</div>}
                  <Link href={`/dashboard/courses/${c.slug}`} className="mt-0.5 block font-medium text-ink hover:text-brand">
                    {c.title}
                  </Link>
                </div>
                {!c.is_published && <span className="shrink-0 rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700">Draft</span>}
              </div>
              <p className="mt-2 text-sm text-ink-muted">{c.description}</p>
              <div className="mt-3 text-xs text-ink-muted">
                {c.chapter_count} chapters &middot; {c.lesson_count} lessons
              </div>

              {c.enrolled ? (
                <div className="mt-4">
                  <div className="h-2 w-full overflow-hidden rounded-full bg-line">
                    <div className="h-full bg-brand transition-all" style={{ width: `${c.progress_pct ?? 0}%` }} />
                  </div>
                  <div className="mt-2 flex items-center justify-between">
                    <span className="text-xs text-ink-muted">{c.progress_pct ?? 0}% complete</span>
                    {c.completed_at ? (
                      <span className="text-xs font-medium text-emerald-600">Completed</span>
                    ) : (
                      <Link href={`/dashboard/courses/${c.slug}`} className="text-xs font-medium text-brand">
                        Continue &rarr;
                      </Link>
                    )}
                  </div>
                </div>
              ) : (
                <button
                  onClick={() => enroll(c.id)}
                  disabled={enrolling === c.id}
                  className="mt-4 rounded-lg bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-brand-dark disabled:opacity-40"
                >
                  {enrolling === c.id ? "..." : "Enroll"}
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </main>
  );
}
