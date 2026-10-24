"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { CurriculumUpdate } from "@/lib/learning";

export function LessonUpdates({ lessonId }: { lessonId: number }) {
  const [updates, setUpdates] = useState<CurriculumUpdate[]>([]);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let active = true;
    api.getLessonUpdates(lessonId).then(items => { if (active) setUpdates(items); }).catch(() => { if (active) setFailed(true); });
    return () => { active = false; };
  }, [lessonId]);
  return <aside className="mt-8 rounded-xl border border-line p-5">
    <h2 className="font-semibold">Recent developments to investigate</h2>
    <p className="mt-1 text-xs text-ink-muted">Automatically matched source announcements from the last 30 days. These are reading prompts, not verified amendments to this lesson.</p>
    {failed ? <p className="mt-3 text-sm">Updates could not be loaded. Try refreshing later.</p> : updates.length === 0 ? <p className="mt-3 text-sm text-ink-muted">No recent matching items are available. This does not establish that the topic has not changed.</p> : <ul className="mt-4 space-y-4">
      {updates.map(update => <li key={update.url}>
        <a href={update.url} target="_blank" rel="noreferrer" className="text-sm font-medium text-brand underline">{update.title} ↗</a>
        <p className="text-xs text-ink-muted">{update.source} · {update.published_at.slice(0, 10)}</p>
        <p className="mt-1 text-sm">{update.summary.slice(0, 280)}</p>
        <p className="mt-2 text-xs font-medium">Try: identify the claim, its evidence, and one experiment that would show whether it changes this lesson&apos;s advice.</p>
      </li>)}
    </ul>}
  </aside>;
}
