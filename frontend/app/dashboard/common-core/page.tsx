"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
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

  if (!progress) return <main className="px-6 py-12 text-sm text-ink-muted">Loading...</main>;

  const pct = progress.common_core_lessons_total
    ? Math.round((progress.common_core_lessons_completed / progress.common_core_lessons_total) * 100)
    : 0;

  return (
    <main className="mx-auto max-w-2xl px-6 py-12">
      <h1 className="text-2xl font-semibold">Common Core</h1>
      <p className="mt-1 text-sm text-ink-muted">
        Everyone starts here, regardless of track. Your {progress.track?.name} curriculum unlocks once this is done.
      </p>

      <div className="mt-6 h-2 w-full overflow-hidden rounded-full bg-line">
        <div className="h-full bg-brand transition-all" style={{ width: `${pct}%` }} />
      </div>
      <p className="mt-2 text-sm text-ink-muted">
        {progress.common_core_lessons_completed} / {progress.common_core_lessons_total} lessons complete
      </p>

      <LessonList lessons={progress.common_core_lessons} onCompleted={load} />

      <Link
        href="/dashboard/explore/language-model"
        className="mt-8 flex items-center justify-between rounded-xl border border-brand/30 bg-brand/10 px-5 py-4 transition-colors hover:bg-brand/20"
      >
        <div>
          <div className="text-xs font-medium uppercase tracking-wide text-brand">Interactive explainer</div>
          <div className="mt-0.5 text-sm font-medium text-ink">What a Language Model Actually Does</div>
        </div>
        <span className="text-brand">→</span>
      </Link>

      <Link
        href="/dashboard/explore/language-model-loop"
        className="mt-3 flex items-center justify-between rounded-xl border border-amber-300 bg-amber-50 px-5 py-4 transition-colors hover:bg-amber-100"
      >
        <div>
          <div className="text-xs font-medium uppercase tracking-wide text-amber-700">Interactive explainer · map view</div>
          <div className="mt-0.5 text-sm font-medium text-ink">What a Language Model Actually Does (diagram-navigated)</div>
        </div>
        <span className="text-amber-700">→</span>
      </Link>

      <Link
        href="/dashboard/explore/rag"
        className="mt-3 flex items-center justify-between rounded-xl border border-emerald-500/30 bg-emerald-50 px-5 py-4 transition-colors hover:bg-emerald-50"
      >
        <div>
          <div className="text-xs font-medium uppercase tracking-wide text-emerald-600">Interactive explainer · map view</div>
          <div className="mt-0.5 text-sm font-medium text-ink">What Retrieval-Augmented Generation (RAG) Actually Does</div>
        </div>
        <span className="text-emerald-600">→</span>
      </Link>

      <Link
        href="/dashboard/explore/agent"
        className="mt-3 flex items-center justify-between rounded-xl border border-sky-300 bg-sky-50 px-5 py-4 transition-colors hover:bg-sky-100"
      >
        <div>
          <div className="text-xs font-medium uppercase tracking-wide text-sky-600">Interactive explainer · map view</div>
          <div className="mt-0.5 text-sm font-medium text-ink">What an AI Agent Actually Does</div>
        </div>
        <span className="text-sky-600">→</span>
      </Link>
    </main>
  );
}
