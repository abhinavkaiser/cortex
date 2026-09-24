"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import type { Curriculum } from "@/lib/types";

export default function TrackCurriculumPage() {
  const params = useParams<{ slug: string }>();
  const [curriculum, setCurriculum] = useState<Curriculum | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const c = await api.getCurriculum(params.slug);
      setCurriculum(c);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load this course.");
    }
  }, [params.slug]);

  useEffect(() => {
    load();
  }, [load]);

  if (error) return <main className="px-6 py-12 text-sm text-red-600">{error}</main>;
  if (!curriculum) return <main className="px-6 py-12 text-sm text-ink-muted">Loading...</main>;

  return (
    <main className="mx-auto max-w-2xl px-6 py-12">
      <Link href="/dashboard/tracks" className="text-xs text-ink-muted hover:text-ink">
        ← All courses
      </Link>

      <h1 className="mt-4 text-2xl font-semibold">{curriculum.track.name}</h1>
      <p className="mt-1 text-sm text-ink-muted">{curriculum.track.description}</p>

      {curriculum.modules.map((m) => (
        <section key={m.id} className="mt-8">
          <h2 className="text-sm font-medium uppercase tracking-wide text-brand">{m.title}</h2>
          {m.objective && <p className="mt-1 text-sm text-ink-muted">{m.objective}</p>}
          <div className="mt-3 space-y-2">
            {m.lessons.map((l) => (
              <Link
                key={l.id}
                href={`/dashboard/lessons/${l.id}`}
                className="flex items-center justify-between rounded-lg border border-line bg-surface px-4 py-3 transition hover:border-brand/40"
              >
                <span className="text-sm text-ink">{l.title}</span>
                <span className="flex items-center gap-2 text-xs text-ink-muted">
                  {l.completed && <span className="text-emerald-600">✓</span>}
                  {l.estimated_minutes} min
                </span>
              </Link>
            ))}
          </div>
        </section>
      ))}

      {curriculum.ungrouped_lessons.length > 0 && (
        <section className="mt-8">
          <div className="space-y-2">
            {curriculum.ungrouped_lessons.map((l) => (
              <Link
                key={l.id}
                href={`/dashboard/lessons/${l.id}`}
                className="flex items-center justify-between rounded-lg border border-line bg-surface px-4 py-3 transition hover:border-brand/40"
              >
                <span className="text-sm text-ink">{l.title}</span>
                <span className="flex items-center gap-2 text-xs text-ink-muted">
                  {l.completed && <span className="text-emerald-600">✓</span>}
                  {l.estimated_minutes} min
                </span>
              </Link>
            ))}
          </div>
        </section>
      )}
    </main>
  );
}
