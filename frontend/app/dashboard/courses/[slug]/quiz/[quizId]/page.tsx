"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import type { AnswerValue, QuizAttemptResult, QuizTake } from "@/lib/types";

function emptyAnswer(type: string): AnswerValue {
  if (type === "multi_select") return [];
  if (type === "short_answer") return "";
  return null;
}

function isAnswered(type: string, value: AnswerValue): boolean {
  if (type === "multi_select") return Array.isArray(value) && value.length > 0;
  if (type === "short_answer") return typeof value === "string" && value.trim().length > 0;
  return value !== null;
}

export default function QuizTakePage() {
  const params = useParams<{ slug: string; quizId: string }>();
  const router = useRouter();
  const quizId = Number(params.quizId);

  const [quiz, setQuiz] = useState<QuizTake | null>(null);
  const [answers, setAnswers] = useState<AnswerValue[]>([]);
  const [result, setResult] = useState<QuizAttemptResult | null>(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const load = useCallback(async () => {
    try {
      setError("");
      const q = await api.getQuiz(quizId);
      setQuiz(q);
      setAnswers(q.questions.map((question) => emptyAnswer(question.type)));
      setResult(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load this quiz.");
    }
  }, [quizId]);

  useEffect(() => {
    load();
  }, [load]);

  function selectSingle(questionIndex: number, choiceIndex: number) {
    if (result) return; // locked once submitted -- retake starts a fresh attempt instead
    setAnswers((prev) => {
      const next = [...prev];
      next[questionIndex] = choiceIndex;
      return next;
    });
  }

  function toggleMulti(questionIndex: number, choiceIndex: number) {
    if (result) return;
    setAnswers((prev) => {
      const next = [...prev];
      const current = Array.isArray(next[questionIndex]) ? (next[questionIndex] as number[]) : [];
      next[questionIndex] = current.includes(choiceIndex) ? current.filter((c) => c !== choiceIndex) : [...current, choiceIndex].sort((a, b) => a - b);
      return next;
    });
  }

  function setText(questionIndex: number, text: string) {
    if (result) return;
    setAnswers((prev) => {
      const next = [...prev];
      next[questionIndex] = text;
      return next;
    });
  }

  async function submit() {
    if (!quiz || !allAnswered) return;
    setSubmitting(true);
    setError("");
    try {
      const order = quiz.questions.map((q) => q.original_index);
      const r = await api.submitQuizAttempt(quizId, answers, order);
      setResult(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not submit this attempt.");
    } finally {
      setSubmitting(false);
    }
  }

  async function retake() {
    await load();
  }

  if (error && !quiz) return <main className="px-6 py-12 text-sm text-red-600">{error}</main>;
  if (!quiz) return <main className="px-6 py-12 text-sm text-ink-muted">Loading...</main>;

  const allAnswered = answers.every((a, i) => isAnswered(quiz.questions[i].type, a));
  const attemptsExhausted = quiz.max_attempts !== null && quiz.attempts_used >= quiz.max_attempts;

  return (
    <main className="mx-auto max-w-2xl px-6 py-12">
      <button onClick={() => router.push(`/dashboard/courses/${params.slug}`)} className="text-xs text-ink-muted hover:text-ink">
        &larr; Back to course
      </button>

      <h1 className="mt-4 text-2xl font-semibold">{quiz.title}</h1>
      <p className="mt-1 text-sm text-ink-muted">
        {quiz.questions.length} questions &middot; {quiz.passing_score}% to pass
        {quiz.max_attempts !== null && (
          <>
            {" "}
            &middot; {quiz.attempts_used} of {quiz.max_attempts} attempts used
          </>
        )}
      </p>

      {error && <div className="mt-4 rounded-lg border border-red-500/30 bg-red-50 p-3 text-sm text-red-700">{error}</div>}

      {!result && attemptsExhausted && (
        <div className="mt-4 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-800">
          You&apos;ve used all {quiz.max_attempts} attempts allowed on this quiz.
        </div>
      )}

      {result && (
        <div
          className={`mt-6 rounded-xl border p-4 ${
            result.status === "pending" ? "border-amber-300 bg-amber-50" : result.passed ? "border-emerald-500/30 bg-emerald-50" : "border-red-500/30 bg-red-50"
          }`}
        >
          {result.status === "pending" ? (
            <>
              <div className="text-lg font-semibold text-amber-800">Awaiting review</div>
              <p className="mt-1 text-sm text-amber-800">
                This quiz includes a short-answer question, so an instructor needs to review it before your result is final. Auto-graded
                questions are shown below.
              </p>
            </>
          ) : (
            <>
              <div className={`text-lg font-semibold ${result.passed ? "text-emerald-700" : "text-red-600"}`}>
                {result.passed ? "Passed" : "Not yet"} -- {result.score}%
              </div>
              <p className="mt-1 text-sm text-ink-muted">
                {result.passed ? "Nice work -- this chapter is cleared." : `You need ${result.passing_score}% to pass. Review the answers below and try again.`}
              </p>
            </>
          )}
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
        {quiz.questions.map((q, qi) => {
          const questionResult = result?.results[qi];
          return (
            <div key={qi} className="rounded-xl border border-line p-4">
              <div className="text-sm font-medium text-ink">
                {qi + 1}. {q.question}
                {q.type === "multi_select" && <span className="ml-2 text-xs font-normal text-ink-muted">(select all that apply)</span>}
                {q.type === "short_answer" && <span className="ml-2 text-xs font-normal text-ink-muted">(short answer)</span>}
              </div>

              {q.type === "short_answer" ? (
                <textarea
                  value={(answers[qi] as string) || ""}
                  onChange={(e) => setText(qi, e.target.value)}
                  disabled={!!result}
                  rows={4}
                  placeholder="Write your answer..."
                  className="mt-3 w-full rounded-lg border border-line px-3 py-2 text-sm text-ink disabled:bg-surface disabled:text-ink-muted"
                />
              ) : (
                <div className="mt-3 space-y-2">
                  {q.choices.map((choice, ci) => {
                    const isMulti = q.type === "multi_select";
                    const selectedValue = answers[qi];
                    const selected = isMulti ? Array.isArray(selectedValue) && selectedValue.includes(ci) : selectedValue === ci;

                    let extraClass = "border-line hover:border-brand/40";
                    if (result && questionResult) {
                      const correctSet = isMulti ? new Set(questionResult.correct_indices || []) : new Set(questionResult.correct_index !== null ? [questionResult.correct_index] : []);
                      if (correctSet.has(ci)) extraClass = "border-emerald-500 bg-emerald-50";
                      else if (selected && !questionResult.correct) extraClass = "border-red-500 bg-red-50";
                    } else if (selected) {
                      extraClass = "border-brand bg-brand/5";
                    }

                    return (
                      <button
                        key={ci}
                        onClick={() => (isMulti ? toggleMulti(qi, ci) : selectSingle(qi, ci))}
                        disabled={!!result}
                        className={`flex w-full items-center gap-2 rounded-lg border px-3 py-2 text-left text-sm text-ink transition disabled:cursor-default ${extraClass}`}
                      >
                        {isMulti && (
                          <span className={`inline-block h-3.5 w-3.5 shrink-0 rounded border ${selected ? "border-brand bg-brand" : "border-line"}`} />
                        )}
                        {choice}
                      </button>
                    );
                  })}
                </div>
              )}

              {result && questionResult?.correct === null && (
                <p className="mt-2 text-xs font-medium text-amber-700">Awaiting instructor review -- not auto-graded.</p>
              )}
            </div>
          );
        })}
      </div>

      <div className="mt-8">
        {result ? (
          <button
            onClick={retake}
            disabled={quiz.max_attempts !== null && quiz.attempts_used >= quiz.max_attempts}
            className="rounded-lg bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-brand-dark disabled:opacity-40"
          >
            Retake quiz
          </button>
        ) : (
          <button
            onClick={submit}
            disabled={!allAnswered || submitting || attemptsExhausted}
            className="rounded-lg bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-brand-dark disabled:opacity-40"
          >
            {submitting ? "Submitting..." : "Submit"}
          </button>
        )}
      </div>
    </main>
  );
}
