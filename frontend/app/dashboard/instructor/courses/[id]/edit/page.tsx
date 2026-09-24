"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import type { Chapter, CourseDetail, CourseSummary, QuizQuestionInput, RosterRow } from "@/lib/types";

// Manually-authored course editing -- plain title + markdown content is
// enough for a lesson here (see backend/app/schemas/course.py's
// CourseLessonCreate docstring), no content_blocks authoring UI in scope.
// Chapters/lessons are append-only in this editor: creation order is the
// display order (order_index is set to "next available slot" on create).
// There's no drag-to-reorder or in-place lesson edit -- the backend has no
// PATCH route for either (see README's Scoping notes) -- so getting the
// order right means creating chapters/lessons in the order you want them
// to appear.
function slugify(s: string): string {
  return s
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}

function AddLessonForm({ courseId, moduleId, onAdded }: { courseId: number; moduleId: number; onAdded: () => void }) {
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [minutes, setMinutes] = useState(10);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    setBusy(true);
    try {
      await api.createCourseLesson(courseId, moduleId, {
        slug: `${slugify(title)}-${Date.now().toString(36)}`,
        title,
        content_markdown: content,
        order_index: Date.now(), // append-only editor -- see file header
        estimated_minutes: minutes,
      });
      setTitle("");
      setContent("");
      setMinutes(10);
      setOpen(false);
      onAdded();
    } finally {
      setBusy(false);
    }
  }

  if (!open) {
    return (
      <button onClick={() => setOpen(true)} className="text-xs font-medium text-brand hover:text-brand-dark">
        + Add lesson
      </button>
    );
  }

  return (
    <form onSubmit={submit} className="space-y-2 rounded-lg border border-line bg-white p-3">
      <input
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Lesson title"
        required
        className="w-full rounded-lg border border-line px-3 py-1.5 text-sm text-ink"
      />
      <textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        placeholder="Lesson content (markdown)"
        rows={4}
        className="w-full rounded-lg border border-line px-3 py-1.5 text-sm text-ink"
      />
      <div className="flex items-center gap-2">
        <label className="text-xs text-ink-muted">Minutes</label>
        <input
          type="number"
          value={minutes}
          min={1}
          onChange={(e) => setMinutes(Number(e.target.value))}
          className="w-20 rounded-lg border border-line px-2 py-1 text-sm text-ink"
        />
        <button type="submit" disabled={busy} className="ml-auto rounded-lg bg-brand px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-dark disabled:opacity-40">
          {busy ? "Saving..." : "Save lesson"}
        </button>
        <button type="button" onClick={() => setOpen(false)} className="text-xs text-ink-muted hover:text-ink">
          Cancel
        </button>
      </div>
    </form>
  );
}

function QuizEditor({ courseId, moduleId, existing, onSaved }: { courseId: number; moduleId: number; existing: Chapter["quiz"]; onSaved: () => void }) {
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState(existing?.title ?? "Chapter Quiz");
  const [passingScore, setPassingScore] = useState(existing?.passing_score ?? 70);
  const [questions, setQuestions] = useState<QuizQuestionInput[]>(
    existing ? [] : [{ question: "", choices: ["", ""], correct_index: 0 }]
  );
  const [busy, setBusy] = useState(false);

  function addQuestion() {
    setQuestions((qs) => [...qs, { question: "", choices: ["", ""], correct_index: 0 }]);
  }

  function updateQuestion(i: number, patch: Partial<QuizQuestionInput>) {
    setQuestions((qs) => qs.map((q, idx) => (idx === i ? { ...q, ...patch } : q)));
  }

  function updateChoice(qi: number, ci: number, value: string) {
    setQuestions((qs) => qs.map((q, idx) => (idx === qi ? { ...q, choices: q.choices.map((c, cidx) => (cidx === ci ? value : c)) } : q)));
  }

  function addChoice(qi: number) {
    setQuestions((qs) => qs.map((q, idx) => (idx === qi ? { ...q, choices: [...q.choices, ""] } : q)));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await api.upsertChapterQuiz(courseId, moduleId, { title, passing_score: passingScore, questions });
      setOpen(false);
      onSaved();
    } finally {
      setBusy(false);
    }
  }

  if (existing && !open) {
    return (
      <div className="flex items-center justify-between rounded-lg border border-dashed border-line bg-white px-3 py-2 text-sm">
        <span className="text-ink">
          {existing.title} &middot; {existing.question_count} questions &middot; {existing.passing_score}% to pass
        </span>
        <button onClick={() => setOpen(true)} className="text-xs font-medium text-brand hover:text-brand-dark">
          Replace quiz
        </button>
      </div>
    );
  }

  if (!existing && !open) {
    return (
      <button onClick={() => setOpen(true)} className="text-xs font-medium text-brand hover:text-brand-dark">
        + Add chapter quiz
      </button>
    );
  }

  return (
    <form onSubmit={submit} className="space-y-3 rounded-lg border border-line bg-white p-3">
      <div className="flex gap-2">
        <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Quiz title" className="flex-1 rounded-lg border border-line px-3 py-1.5 text-sm text-ink" />
        <div className="flex items-center gap-1">
          <label className="text-xs text-ink-muted">Pass %</label>
          <input
            type="number"
            value={passingScore}
            min={0}
            max={100}
            onChange={(e) => setPassingScore(Number(e.target.value))}
            className="w-16 rounded-lg border border-line px-2 py-1 text-sm text-ink"
          />
        </div>
      </div>

      {questions.map((q, qi) => (
        <div key={qi} className="rounded-lg border border-line p-3">
          <input
            value={q.question}
            onChange={(e) => updateQuestion(qi, { question: e.target.value })}
            placeholder={`Question ${qi + 1}`}
            required
            className="w-full rounded-lg border border-line px-3 py-1.5 text-sm text-ink"
          />
          <div className="mt-2 space-y-1.5">
            {q.choices.map((choice, ci) => (
              <div key={ci} className="flex items-center gap-2">
                <input
                  type="radio"
                  name={`correct-${qi}`}
                  checked={q.correct_index === ci}
                  onChange={() => updateQuestion(qi, { correct_index: ci })}
                />
                <input
                  value={choice}
                  onChange={(e) => updateChoice(qi, ci, e.target.value)}
                  placeholder={`Choice ${ci + 1}`}
                  required
                  className="flex-1 rounded-lg border border-line px-2 py-1 text-sm text-ink"
                />
              </div>
            ))}
            <button type="button" onClick={() => addChoice(qi)} className="text-xs text-brand hover:text-brand-dark">
              + choice
            </button>
          </div>
        </div>
      ))}

      <div className="flex items-center gap-3">
        <button type="button" onClick={addQuestion} className="text-xs font-medium text-brand hover:text-brand-dark">
          + Add question
        </button>
        <button type="submit" disabled={busy} className="ml-auto rounded-lg bg-brand px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-dark disabled:opacity-40">
          {busy ? "Saving..." : "Save quiz"}
        </button>
        <button type="button" onClick={() => setOpen(false)} className="text-xs text-ink-muted hover:text-ink">
          Cancel
        </button>
      </div>
    </form>
  );
}

function AddChapterForm({ courseId, nextOrder, onAdded }: { courseId: number; nextOrder: number; onAdded: () => void }) {
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [objective, setObjective] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    setBusy(true);
    try {
      await api.createChapter(courseId, { title, objective, order_index: nextOrder });
      setTitle("");
      setObjective("");
      setOpen(false);
      onAdded();
    } finally {
      setBusy(false);
    }
  }

  if (!open) {
    return (
      <button onClick={() => setOpen(true)} className="rounded-lg border border-dashed border-line px-4 py-3 text-sm font-medium text-brand hover:border-brand/40">
        + Add chapter
      </button>
    );
  }

  return (
    <form onSubmit={submit} className="space-y-2 rounded-xl border border-line bg-surface p-4">
      <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Chapter title" required className="w-full rounded-lg border border-line px-3 py-1.5 text-sm text-ink" />
      <input value={objective} onChange={(e) => setObjective(e.target.value)} placeholder="Objective (optional)" className="w-full rounded-lg border border-line px-3 py-1.5 text-sm text-ink" />
      <div className="flex gap-2">
        <button type="submit" disabled={busy} className="rounded-lg bg-brand px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-dark disabled:opacity-40">
          {busy ? "Saving..." : "Save chapter"}
        </button>
        <button type="button" onClick={() => setOpen(false)} className="text-xs text-ink-muted hover:text-ink">
          Cancel
        </button>
      </div>
    </form>
  );
}

export default function EditCoursePage() {
  const params = useParams<{ id: string }>();
  const courseId = Number(params.id);

  const [summary, setSummary] = useState<CourseSummary | null>(null);
  const [detail, setDetail] = useState<CourseDetail | null>(null);
  const [roster, setRoster] = useState<RosterRow[] | null>(null);
  const [error, setError] = useState("");
  const [publishing, setPublishing] = useState(false);

  const load = useCallback(async () => {
    try {
      const all = await api.getCourses();
      const mine = all.find((c) => c.id === courseId);
      if (!mine) {
        setError("Course not found, or you don't own it.");
        return;
      }
      setSummary(mine);
      const [d, r] = await Promise.all([api.getCourse(mine.slug), api.getRoster(courseId)]);
      setDetail(d);
      setRoster(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load this course.");
    }
  }, [courseId]);

  useEffect(() => {
    load();
  }, [load]);

  async function togglePublish() {
    if (!summary) return;
    setPublishing(true);
    try {
      await api.updateCourse(courseId, { is_published: !summary.is_published });
      await load();
    } finally {
      setPublishing(false);
    }
  }

  if (error) return <main className="px-6 py-12 text-sm text-red-600">{error}</main>;
  if (!summary || !detail || !roster) return <main className="px-6 py-12 text-sm text-ink-muted">Loading...</main>;

  const nextChapterOrder = detail.chapters.length + 1;

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">{summary.title}</h1>
          <p className="mt-1 text-sm text-ink-muted">{summary.description}</p>
        </div>
        <button
          onClick={togglePublish}
          disabled={publishing}
          className={`shrink-0 rounded-lg px-4 py-2 text-sm font-medium disabled:opacity-40 ${
            summary.is_published ? "border border-line text-ink hover:bg-surface" : "bg-brand text-white hover:bg-brand-dark"
          }`}
        >
          {publishing ? "..." : summary.is_published ? "Unpublish" : "Publish"}
        </button>
      </div>

      <h2 className="mt-10 text-lg font-semibold text-ink">Chapters</h2>
      <div className="mt-4 space-y-6">
        {detail.chapters.map((chapter) => (
          <div key={chapter.id} className="rounded-xl border border-line bg-surface p-4">
            <div className="font-medium text-ink">{chapter.title}</div>
            {chapter.objective && <p className="text-xs text-ink-muted">{chapter.objective}</p>}

            <div className="mt-3 space-y-1.5">
              {chapter.lessons.map((l) => (
                <div key={l.id} className="rounded-lg border border-line bg-white px-3 py-2 text-sm text-ink">
                  {l.title} <span className="text-xs text-ink-muted">({l.estimated_minutes} min)</span>
                </div>
              ))}
            </div>

            <div className="mt-2">
              <AddLessonForm courseId={courseId} moduleId={chapter.id} onAdded={load} />
            </div>

            <div className="mt-3">
              <QuizEditor courseId={courseId} moduleId={chapter.id} existing={chapter.quiz} onSaved={load} />
            </div>
          </div>
        ))}

        <AddChapterForm courseId={courseId} nextOrder={nextChapterOrder} onAdded={load} />
      </div>

      <h2 className="mt-10 text-lg font-semibold text-ink">Roster</h2>
      {roster.length === 0 ? (
        <p className="mt-2 text-sm text-ink-muted">No one has enrolled yet.</p>
      ) : (
        <div className="mt-4 overflow-x-auto rounded-xl border border-line">
          <table className="w-full text-left text-sm">
            <thead className="bg-surface text-xs uppercase tracking-wide text-ink-muted">
              <tr>
                <th className="px-4 py-2">Learner</th>
                <th className="px-4 py-2">Progress</th>
                <th className="px-4 py-2">Completed</th>
              </tr>
            </thead>
            <tbody>
              {roster.map((r) => (
                <tr key={r.user_id} className="border-t border-line">
                  <td className="px-4 py-2 text-ink">
                    {r.full_name || r.email}
                    <div className="text-xs text-ink-muted">{r.email}</div>
                  </td>
                  <td className="px-4 py-2 text-ink">{r.progress_pct}%</td>
                  <td className="px-4 py-2 text-ink-muted">{r.completed_at ? new Date(r.completed_at).toLocaleDateString() : "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}
