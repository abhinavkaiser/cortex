"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { UserProgress } from "@/lib/types";
import { LessonList } from "@/components/LessonList";

export default function CommonCorePage() {
  const router = useRouter();
  const [progress, setProgress] = useState<UserProgress | null>(null);

  const load = useCallback(async () => {
    const userId = Number(localStorage.getItem("user_id"));
    if (!userId) {
      router.replace("/");
      return;
    }
    const p = await api.getProgress(userId);
    if (!p.track) {
      router.replace("/onboarding");
      return;
    }
    // Common Core already done -- this page is a one-time gate, not
    // somewhere a returning user should land again. Also fires right after
    // marking the last lesson complete, since that flips this flag -- the
    // user lands straight on their track page instead of staring at a
    // now-pointless 100% Common Core screen.
    if (p.common_core_completed) {
      router.replace(`/dashboard/tracks/${p.track.slug}`);
      return;
    }
    setProgress(p);
  }, [router]);

  useEffect(() => {
    load();
  }, [load]);

  if (!progress) return <main className="px-6 py-12 text-sm text-slate-500">Loading...</main>;

  const pct = progress.common_core_lessons_total
    ? Math.round((progress.common_core_lessons_completed / progress.common_core_lessons_total) * 100)
    : 0;

  return (
    <main className="mx-auto max-w-2xl px-6 py-12">
      <h1 className="text-2xl font-semibold">Common Core</h1>
      <p className="mt-1 text-sm text-slate-500">
        Everyone starts here, regardless of track. Your {progress.track?.name} curriculum unlocks once this is done.
      </p>

      <div className="mt-6 h-2 w-full overflow-hidden rounded-full bg-slate-800">
        <div className="h-full bg-brand transition-all" style={{ width: `${pct}%` }} />
      </div>
      <p className="mt-2 text-sm text-slate-500">
        {progress.common_core_lessons_completed} / {progress.common_core_lessons_total} lessons complete
      </p>

      <LessonList lessons={progress.common_core_lessons} onCompleted={load} />
    </main>
  );
}
