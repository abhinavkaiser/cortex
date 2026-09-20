"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { UserProgress } from "@/lib/types";
import { LessonList } from "@/components/LessonList";

const TRACK_NAMES: Record<string, string> = {
  leader: "AI Leader",
  practitioner: "AI Practitioner",
  developer: "AI Developer",
};

export default function TrackPage() {
  const params = useParams<{ slug: string }>();
  const router = useRouter();
  const [progress, setProgress] = useState<UserProgress | null>(null);

  const load = useCallback(async () => {
    const userId = Number(localStorage.getItem("user_id"));
    if (!userId) return;
    const p = await api.getProgress(userId);
    // Gate: this track's curriculum is off-limits until Common Core is
    // done, and this user's own track must match the URL they're on.
    if (!p.common_core_completed) {
      router.replace("/dashboard/common-core");
      return;
    }
    if (p.track?.slug !== params.slug) {
      router.replace(`/dashboard/tracks/${p.track?.slug ?? ""}`);
      return;
    }
    setProgress(p);
  }, [params.slug, router]);

  useEffect(() => {
    load();
  }, [load]);

  if (!progress) return <main className="px-6 py-12 text-sm text-slate-500">Loading...</main>;

  const pct = progress.track_lessons_total
    ? Math.round((progress.track_lessons_completed / progress.track_lessons_total) * 100)
    : 0;

  return (
    <main className="mx-auto max-w-2xl px-6 py-12">
      <h1 className="text-2xl font-semibold">{TRACK_NAMES[params.slug] ?? params.slug} track</h1>
      <div className="mt-4 h-2 w-full overflow-hidden rounded-full bg-slate-800">
        <div className="h-full bg-brand transition-all" style={{ width: `${pct}%` }} />
      </div>
      <p className="mt-2 text-sm text-slate-500">
        {progress.track_lessons_completed} / {progress.track_lessons_total} lessons complete
      </p>

      <LessonList lessons={progress.track_lessons} onCompleted={load} />
    </main>
  );
}
