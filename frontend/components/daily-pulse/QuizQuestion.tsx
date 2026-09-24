"use client";

import { useState } from "react";
import { api } from "@/lib/api";

export function QuizQuestion({ pulseId, question, choices }: { pulseId: number; question: string; choices: string[] }) {
  const [selected, setSelected] = useState<number | null>(null);
  const [result, setResult] = useState<{ correct: boolean; correct_index: number } | null>(null);
  const [checking, setChecking] = useState(false);

  async function submit(index: number) {
    if (result) return; // one attempt per pulse -- don't let a user just click through until they hit the right answer
    setSelected(index);
    setChecking(true);
    try {
      const res = await api.answerQuiz(pulseId, index);
      setResult(res);
    } finally {
      setChecking(false);
    }
  }

  return (
    <div className="rounded-xl border border-line p-5">
      <div className="text-xs font-medium uppercase tracking-wide text-ink-muted">Quiz</div>
      <p className="mt-2 font-medium">{question}</p>
      <div className="mt-4 space-y-2">
        {choices.map((choice, i) => {
          const isSelected = selected === i;
          const isCorrectAnswer = result && i === result.correct_index;
          const isWrongSelection = result && isSelected && !result.correct;
          return (
            <button
              key={i}
              onClick={() => submit(i)}
              disabled={checking || !!result}
              className={`block w-full rounded-lg border px-4 py-2.5 text-left text-sm transition ${
                isCorrectAnswer
                  ? "border-emerald-500 bg-emerald-50"
                  : isWrongSelection
                  ? "border-red-500 bg-red-50"
                  : "border-line hover:border-brand/40"
              }`}
            >
              {choice}
            </button>
          );
        })}
      </div>
      {result && (
        <p className={`mt-3 text-sm ${result.correct ? "text-emerald-600" : "text-red-600"}`}>
          {result.correct ? "Correct." : "Not quite -- the highlighted choice above was right."}
        </p>
      )}
    </div>
  );
}
