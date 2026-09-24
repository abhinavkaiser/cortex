"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import type { QuizAttemptResult, QuizTake } from "@/lib/types";

export default function QuizTakePage() {
  const params = useParams<{ slug: string; quizId: string }>();
  const router = useRouter();
  const quizId = Number(params.quizId);

  const [quiz, setQuiz] = useState<QuizTake | null>(null);
  const [answers, setAnswers] = useState<(number | null)[]>([]);
  const [result, setResult] = useState<QuizAttemptResult | null>(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const load = useCallback(async () => {
    try {
      const q = await api.getQuiz(quizId);
      setQuiz(q);
      setAnswers(new Array(q.questions.length).fill(null));
      setResult(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load this quiz.");
    }
  }, [quizId]);

  useEffect(() => {
    load();
  }, [load]);

  function selectAnswer(questionIndex: number, choiceIndex: number) {
    if (result) return; // locked once submitted -- retake starts a fresh attempt instead
    setAnswers((prev) => {
      const next = [...prev];
      next[questionIndex] = choiceIndex;
      return next;
    });
  }

  async function submit() {
    if (answers.some((a) => a === null)) return;
    setSubmitting(true);
    try {
      const r = await api.submitQuizAttempt(quizId, answers as number[]);
      setResult(r);
    } finally {
      setSubmitting(false);
    }
  }

  function retake() {
    if (quiz) setAnswers(new Array(quiz.questions.length).fill(null));
    setResult(null);
  }

  if (error) return <main className="px-6 py-12 text-sm text-red-600">{error}</main>;
  if (!quiz) return <main className="px-6 py-12 text-sm text-ink-muted">Loading...</main>;

  const allAnswered = answers.every((a) => a !== null);

  return (
    <main className="mx-auto max-w-2xl px-6 py-12">
      <button onClick={() => router.push(`/dashboard/courses/${params.slug}`)} className="text-xs text-ink-muted hover:text-ink">
        &larr; Back to course
      </button>

      <h1 className="mt-4 text-2xl font-semibold">{quiz.title}</h1>
      <p className="mt-1 text-sm text-ink-muted">
        {quiz.questions.length} questions &middot; {quiz.passing_score}% to pass
      </p>

      {result && (
        <div className={`mt-6 rounded-xl border p-4 ${result.passed ? "border-emerald-500/30 bg-emerald-50" : "border-red-500/30 bg-red-50"}`}>
          <div className={`text-lg font-semibold ${result.passed ? "text-emerald-700" : "text-red-600"}`}>
            {result.passed ? "Passed" : "Not yet"} -- {result.score}%
          </div>
          <p className="mt-1 text-sm text-ink-muted">
            {result.passed ? "Nice work -- this chapter is cleared." : `You need ${result.passing_score}% to pass. Review the answers below and try again.`}
          </p>
          {result.course_completed && (
            <p className="mt-2 text-sm font-medium text-emerald-700">
              This was the last thing standing between you and a certificate --{" "}
              <Link href={`/dashboard/courses/${params.slug}`} className="underline">
                see it on the course page
              </Link>
              .
            </p>
          )}
        </div>
      )}

      <div className="mt-8 space-y-6">
        {quiz.questions.map((q, qi) => (
          <div key={qi} className="rounded-xl border border-line p-4">
            <div className="text-sm font-medium text-ink">
              {qi + 1}. {q.question}
            </div>
            <div className="mt-3 space-y-2">
              {q.choices.map((choice, ci) => {
                const selected = answers[qi] === ci;
                const questionResult = result?.results[qi];
                let extraClass = "border-line hover:border-brand/40";
                if (result && questionResult) {
                  if (ci === questionResult.correct_index) extraClass = "border-emerald-500 bg-emerald-50";
                  else if (selected && !questionResult.correct) extraClass = "border-red-500 bg-red-50";
                } else if (selected) {
                  extraClass = "border-brand bg-brand/5";
                }
                return (
                  <button
                    key={ci}
                    onClick={() => selectAnswer(qi, ci)}
                    disabled={!!result}
                    className={`block w-full rounded-lg border px-3 py-2 text-left text-sm text-ink transition ${extraClass} disabled:cursor-default`}
                  >
                    {choice}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-8">
        {result ? (
          <button onClick={retake} className="rounded-lg bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-brand-dark">
            Retake quiz
          </button>
        ) : (
          <button
            onClick={submit}
            disabled={!allAnswered || submitting}
            className="rounded-lg bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-brand-dark disabled:opacity-40"
          >
            {submitting ? "Submitting..." : "Submit"}
          </button>
        )}
      </div>
    </main>
  );
}
