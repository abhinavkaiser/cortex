"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { TrackSummary } from "@/lib/types";

export default function TracksIndexPage() {
  const [tracks, setTracks] = useState<TrackSummary[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .getTracks()
      .then(setTracks)
      .catch((e) => setError(e instanceof Error ? e.message : "Could not load courses."));
  }, []);

  if (error) return <main className="px-6 py-12 text-sm text-red-600">{error}</main>;
  if (!tracks) return <main className="px-6 py-12 text-sm text-ink-muted">Loading...</main>;

  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <h1 className="text-3xl font-semibold">Cortex AI</h1>
      <p className="mt-2 text-ink-muted">Pick a course. Every lesson opens as a clickable, interactive explainer.</p>

      <div className="mt-8 grid gap-4 sm:grid-cols-3">
        {tracks.map((t) => (
          <Link
            key={t.slug}
            href={`/dashboard/tracks/${t.slug}`}
            className="rounded-xl border border-line bg-surface p-5 text-left transition hover:border-brand/50 hover:bg-brand/5"
          >
            <div className="font-medium text-ink">{t.name}</div>
            <p className="mt-1 text-sm text-ink-muted">{t.description}</p>
            <div className="mt-3 text-xs text-ink-muted">{t.lesson_count} lessons</div>
          </Link>
        ))}
      </div>

      <Link href="/dashboard/common-core" className="mt-8 inline-block text-sm text-ink-muted hover:text-ink">
        Also see: Common Core (shared foundations) →
      </Link>
    </main>
  );
}
