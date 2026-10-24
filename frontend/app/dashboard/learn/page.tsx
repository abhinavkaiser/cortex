"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api, API_URL } from "@/lib/api";
import type { PathUnit } from "@/lib/learning";

export default function LearningPathPage() {
  const [units, setUnits] = useState<PathUnit[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => { api.getLearningPath().then(setUnits).catch(e => setError(e.message)).finally(() => setLoading(false)); }, []);
  const next = units.find(unit => unit.practice_score !== 100);
  const completed = units.filter(unit => unit.practice_score === 100).length;
  return <main className="mx-auto max-w-3xl px-6 py-12">
    <p className="text-xs font-semibold uppercase tracking-wide text-brand">Your learning path</p>
    <h1 className="mt-2 text-3xl font-semibold">Build skills by doing</h1>
    <p className="mt-3 text-ink-muted">Start with the AI foundation, then build the technical skills needed for the developer course. Each unit includes a worked example, decisions to test, feedback and a written explanation to revise.</p>
    {loading && <p className="mt-8">Loading your path…</p>}
    {error && <p role="alert" className="mt-6 text-red-700">{error}</p>}
    {!loading && !error && units.length === 0 && <p className="mt-8">The revised path has not been published yet. Browse the <Link href="/dashboard/courses" className="text-brand underline">course catalog</Link>.</p>}
    {units.length > 0 && <>
      <div className="mt-8 rounded-2xl border border-brand/30 bg-surface p-6">
        <p className="text-sm">{completed} of {units.length} decision practices completed</p>
        {next ? <><h2 className="mt-2 text-xl font-semibold">Next: {next.title}</h2><p className="mt-2 text-sm">{next.objective}</p><Link href={`/dashboard/lessons/${next.lesson_id}`} className="mt-4 inline-block rounded-lg bg-brand px-4 py-2 text-sm text-white">{next.practice_score === null ? "Try this lesson" : "Revise your attempt"} →</Link></> : <><h2 className="mt-2 text-xl font-semibold">Ready for the next challenge</h2><p className="mt-2 text-sm">Revisit your written reasoning and complete the project kit before moving to the developer course.</p><Link href="/dashboard/courses/ai-developer" className="mt-3 inline-block text-brand underline">Explore AI Developer →</Link></>}
      </div>
      {["AI foundation", "Technical bridge"].map(stage => <section key={stage} className="mt-10">
        <h2 className="text-xl font-semibold">{stage}</h2>
        <ol className="mt-4 space-y-3">{units.filter(unit => unit.stage === stage).map((unit, index) => <li key={unit.lesson_id} className="rounded-xl border border-line p-4">
          <Link href={`/dashboard/lessons/${unit.lesson_id}`} className="font-medium text-brand hover:underline">{index + 1}. {unit.title}</Link>
          <p className="mt-1 text-sm text-ink-muted">{unit.objective}</p>
          <p className="mt-2 text-xs">{unit.minutes} min · {unit.practice_score === null ? "Not attempted" : unit.practice_score === 100 ? "Decision practice complete" : `Best decision score: ${unit.practice_score}%`} {unit.status !== "reviewed" && " · Content needs review"}</p>
        </li>)}</ol>
      </section>)}
      <section className="mt-10 rounded-xl border border-line p-6">
        <h2 className="text-xl font-semibold">Your project kit</h2>
        <p className="mt-2 text-sm">Synthetic documents, labeled questions, Python baselines and tests for retrieval, classification and safe tool execution. Runs without paid APIs. Includes setup, expected behavior and a project brief.</p>
        <a href={`${API_URL}/api/learning/lab-pack`} className="mt-4 inline-block text-sm font-medium text-brand underline">Download the Python lab pack (.zip)</a>
        <p className="mt-3 text-xs text-ink-muted">Progress measures guided practice. Written explanations and the project require self-review; they are not independently graded qualifications.</p>
      </section>
    </>}
  </main>;
}
