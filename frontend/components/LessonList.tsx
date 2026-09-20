"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { Lesson } from "@/lib/types";

export function LessonList({ lessons, onCompleted }: { lessons: Lesson[]; onCompleted: () => void }) {
  const [completing, setCompleting] = useState<number | null>(null);

  async function complete(lessonId: number) {
    setCompleting(lessonId);
    try {
      await api.completeLesson(lessonId);
      onCompleted(); // re-fetch progress so the checkbox/gate state stays accurate
    } finally {
      setCompleting(null);
    }
  }

  if (lessons.length === 0) {
    return <p className="mt-4 text-sm text-slate-500">No lessons in this section yet.</p>;
  }

  return (
    <div className="mt-4 space-y-2">
      {lessons.map((lesson) => (
        <div
          key={lesson.id}
          className={`flex items-center justify-between rounded-lg border px-4 py-3 ${
            lesson.completed ? "border-slate-800 bg-slate-900/40" : "border-slate-800"
          }`}
        >
          <div>
            <div className={`text-sm font-medium ${lesson.completed ? "text-slate-500 line-through" : "text-slate-100"}`}>{lesson.title}</div>
            <div className="text-xs text-slate-500">{lesson.estimated_minutes} min</div>
          </div>
          {lesson.completed ? (
            <span className="text-xs font-medium text-emerald-400">✓ Done</span>
          ) : (
            <button
              onClick={() => complete(lesson.id)}
              disabled={completing === lesson.id}
              className="rounded-lg bg-brand px-3 py-1.5 text-xs font-medium disabled:opacity-40"
            >
              {completing === lesson.id ? "..." : "Mark complete"}
            </button>
          )}
        </div>
      ))}
    </div>
  );
}
