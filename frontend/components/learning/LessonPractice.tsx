"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { LearningUnit } from "@/lib/learning";

export function LessonPractice({ lessonId, unit, onSaved, onLearn }: {
  lessonId: number; unit: LearningUnit; onSaved: (unit: LearningUnit) => void; onLearn: () => void;
}) {
  const [answers, setAnswers] = useState<number[]>(unit.latest_attempt?.answers ?? unit.exercise.questions.map(() => -1));
  const [reflection, setReflection] = useState(unit.latest_attempt?.reflection ?? "");
  const [result, setResult] = useState(unit.latest_attempt);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [edited, setEdited] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setSaving(true); setError("");
    try {
      const next = await api.submitPractice(lessonId, unit.version, answers, reflection);
      setResult(next); setEdited(false);
      onSaved({ ...unit, latest_attempt: next, best_score: Math.max(unit.best_score ?? 0, next.score) });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Your work could not be saved. Try again.");
    } finally { setSaving(false); }
  }

  return <section className="mt-6 rounded-2xl border border-brand/30 bg-surface p-6">
    <p className="text-xs font-semibold uppercase tracking-wide text-brand">Try → learn → revise</p>
    <h2 className="mt-2 text-xl font-semibold">{unit.exercise.title}</h2>
    <p className="mt-2 text-sm text-ink-muted">Try the case first. You can open the explanation at any time, then return to improve your answer.</p>
    <p className="mt-4 whitespace-pre-line leading-relaxed">{unit.exercise.scenario}</p>
    <button type="button" onClick={onLearn} className="mt-3 text-sm font-medium text-brand underline">Read the worked explanation</button>
    <form onSubmit={submit} className="mt-6 space-y-6">
      {unit.exercise.questions.map((question, index) => <fieldset key={index}>
        <legend className="font-medium">{index + 1}. {question.question}</legend>
        <div className="mt-2 space-y-2">
          {question.choices.map((choice, choiceIndex) => <label key={choiceIndex} className="flex cursor-pointer items-start gap-3 rounded-lg border border-line bg-white p-3 text-sm">
            <input type="radio" name={`task-${index}`} checked={answers[index] === choiceIndex} required
              onChange={() => { setAnswers(current => current.map((answer, i) => i === index ? choiceIndex : answer)); setEdited(true); }}
              className="mt-1" />
            <span>{choice}</span>
          </label>)}
        </div>
        {result && !edited && <p className={`mt-2 text-sm ${result.feedback[index].correct ? "text-emerald-700" : "text-amber-800"}`}>
          {result.feedback[index].correct ? "✓ " : "Revisit: "}{result.feedback[index].explanation}
        </p>}
      </fieldset>)}
      <div>
        <label htmlFor="practice-reflection" className="font-medium">Explain your decision</label>
        <p className="mt-1 text-sm text-ink-muted">{unit.exercise.reflection_prompt}</p>
        <textarea id="practice-reflection" required minLength={40} maxLength={5000} rows={5} value={reflection}
          onChange={event => { setReflection(event.target.value); setEdited(true); }}
          className="mt-3 w-full rounded-lg border border-line bg-white p-3 text-sm" />
        <p className="text-xs text-ink-muted">At least 40 characters. Saved to your account for revision. Your written explanation is self-reviewed, not automatically scored.</p>
      </div>
      {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
      <button disabled={saving || unit.status === "changed_since_review" || answers.some(a => a < 0) || reflection.trim().length < 40}
        className="rounded-lg bg-brand px-4 py-2 text-sm font-medium text-white disabled:opacity-40">
        {saving ? "Saving…" : result ? "Save revised attempt" : "Check decisions and save my work"}
      </button>
    </form>
    {result && <div className="mt-6 border-t border-line pt-5" aria-live="polite">
      <p className="font-medium">Last saved decision score: {result.score}%{edited ? " · You have unsaved changes" : ""}</p>
      <p className="mt-1 text-sm text-ink-muted">{unit.best_score === 100 ? "Decision practice completed. Review your explanation against the criteria below." : "Correct the missed decisions and submit again. Use the explanation to understand why."}</p>
      <h3 className="mt-4 font-semibold">Compare your reasoning</h3>
      <p className="mt-2 text-sm leading-relaxed">{result.reference}</p>
      <ul className="mt-3 list-disc space-y-1 pl-5 text-sm">{result.rubric.map(item => <li key={item}>{item}</li>)}</ul>
      <p className="mt-3 text-xs text-ink-muted">This is guided practice with retries. It does not independently establish mastery.</p>
    </div>}
  </section>;
}
