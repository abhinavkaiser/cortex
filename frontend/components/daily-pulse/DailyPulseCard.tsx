"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { DailyPulse } from "@/lib/types";
import { QuizQuestion } from "./QuizQuestion";
import { SandboxExercise } from "./SandboxExercise";

// One pulse. Broken out from DailyPulseCard below so each of today's
// (up to 3) track pulses renders as its own self-contained card.
function PulseCard({ pulse }: { pulse: DailyPulse }) {
  return (
    <div className="space-y-4 rounded-2xl border border-line bg-white p-5">
      <div>
        <div className="text-xs font-medium uppercase tracking-wide text-brand">
          {pulse.track_name ?? "Daily Pulse"} -- {pulse.pulse_date}
        </div>
        <p className="mt-2 whitespace-pre-line leading-relaxed">{pulse.summary}</p>
        {pulse.source_urls.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-3 text-xs text-ink-muted">
            {pulse.source_urls.map((url) => (
              <a key={url} href={url} target="_blank" rel="noreferrer" className="hover:text-ink">
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

// Learners no longer have a single assigned track (see README's "Courses
// vs. Tracks"), so there's no one pulse to scope this to anymore --
// GET /api/daily-pulse/today now returns every track's pulse for today,
// and this renders all of them, each labeled by track.
export function DailyPulseCard() {
  const [pulses, setPulses] = useState<DailyPulse[] | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .getTodayPulse()
      .then(setPulses)
      .catch((e) => setError(e instanceof Error ? e.message : "Could not load today's pulse."))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-sm text-ink-muted">Loading today&apos;s pulse...</div>;
  if (error) return <div className="rounded-xl border border-line p-5 text-sm text-ink-muted">{error}</div>;
  if (!pulses || pulses.length === 0) return null;

  return (
    <div className="space-y-6">
      {pulses.map((pulse) => (
        <PulseCard key={pulse.id} pulse={pulse} />
      ))}
    </div>
  );
}
