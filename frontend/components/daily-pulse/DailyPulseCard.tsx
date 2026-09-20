"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { DailyPulse } from "@/lib/types";
import { QuizQuestion } from "./QuizQuestion";
import { SandboxExercise } from "./SandboxExercise";

export function DailyPulseCard() {
  const [pulse, setPulse] = useState<DailyPulse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .getTodayPulse()
      .then(setPulse)
      .catch((e) => setError(e instanceof Error ? e.message : "Could not load today's pulse."))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-sm text-slate-500">Loading today&apos;s pulse...</div>;
  if (error) return <div className="rounded-xl border border-slate-800 p-5 text-sm text-slate-400">{error}</div>;
  if (!pulse) return null;

  return (
    <div className="space-y-4">
      <div>
        <div className="text-xs font-medium uppercase tracking-wide text-brand">Daily Pulse -- {pulse.pulse_date}</div>
        <p className="mt-2 whitespace-pre-line leading-relaxed">{pulse.summary}</p>
        {pulse.source_urls.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-3 text-xs text-slate-500">
            {pulse.source_urls.map((url) => (
              <a key={url} href={url} target="_blank" rel="noreferrer" className="hover:text-slate-300">
                Source ↗
              </a>
            ))}
          </div>
        )}
      </div>

      <SandboxExercise text={pulse.sandbox_exercise} />
      <QuizQuestion pulseId={pulse.id} question={pulse.quiz_question} choices={pulse.quiz_choices} />
    </div>
  );
}
