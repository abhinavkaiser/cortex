"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import type { Chapter, CourseDetail, CourseSummary, LessonBlock, LessonDetail, PendingAttempt, QuizQuestionInput, RosterRow } from "@/lib/types";

// Chapters and lessons are now edit-after-create + reorderable (PATCH
// .../chapters/{id} and .../lessons/{id}) -- reordering supports both HTML5
// drag-and-drop (draggable/onDragStart/onDragOver/onDrop, no new
// dependency) and up/down buttons as a keyboard-accessible alternative,
// since a screen reader / keyboard-only user can't drag. Every reorder
// reindexes the whole list to 1..N and PATCHes each chapter/lesson whose
// order_index changed, then reloads from the server -- simpler and safer
// than trying to diff a partial move client-side.
function slugify(s: string): string {
  return s
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}

function moveItem<T>(items: T[], fromIndex: number, toIndex: number): T[] {
  const next = [...items];
  const [item] = next.splice(fromIndex, 1);
  next.splice(toIndex, 0, item);
  return next;
}

function ReorderControls({ onUp, onDown, onMoveStart, disabledUp, disabledDown }: { onUp: () => void; onDown: () => void; onMoveStart: () => void; disabledUp: boolean; disabledDown: boolean }) {
  return (
    <div className="flex shrink-0 items-center gap-0.5">
      <span
        draggable
        onDragStart={onMoveStart}
        title="Drag to reorder"
        className="cursor-grab select-none px-1 text-ink-muted hover:text-ink active:cursor-grabbing"
      >
        ⠿
      </span>
      <button
        type="button"
        onClick={onUp}
        disabled={disabledUp}
        aria-label="Move up"
        className="rounded px-1 text-xs text-ink-muted hover:text-ink disabled:opacity-30"
      >
        ↑
      </button>
      <button
        type="button"
        onClick={onDown}
        disabled={disabledDown}
        aria-label="Move down"
        className="rounded px-1 text-xs text-ink-muted hover:text-ink disabled:opacity-30"
      >
        ↓
      </button>
    </div>
  );
}

// ---- Lesson content-block authoring (video / document / link) -----------

function BlocksEditor({ courseId, blocks, onChange }: { courseId: number; blocks: LessonBlock[]; onChange: (b: LessonBlock[]) => void }) {
  const [adding, setAdding] = useState<"video" | "document" | "link" | null>(null);
  const [uploading, setUploading] = useState(false);

  function removeBlock(i: number) {
    onChange(blocks.filter((_, idx) => idx !== i));
  }

  function addVideo(title: string, url: string, transcript: string) {
    onChange([...blocks, { type: "video", title, url, transcript }]);
    setAdding(null);
  }

  function addLink(title: string, url: string, description: string) {
    onChange([...blocks, { type: "link", title, url, description }]);
    setAdding(null);
  }

  async function addDocument(title: string, file: File) {
    setUploading(true);
    try {
      const { url, filename } = await api.uploadCourseDocument(courseId, file);
      onChange([...blocks, { type: "document", title: title || filename, url, filename }]);
      setAdding(null);
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="space-y-2">
      {blocks.length > 0 && (
        <div className="space-y-1.5">
          {blocks.map((b, i) => (
            <div key={i} className="flex items-center justify-between rounded-lg border border-line bg-white px-2.5 py-1.5 text-xs">
              <span className="text-ink">
                <span className="mr-1.5 rounded bg-surface px-1.5 py-0.5 font-medium uppercase text-ink-muted">{b.type}</span>
                {b.type === "video" && b.title}
                {b.type === "document" && b.title}
                {b.type === "link" && b.title}
                {b.type === "text" && b.markdown.slice(0, 60)}
              </span>
              <button type="button" onClick={() => removeBlock(i)} className="text-ink-muted hover:text-red-600">
                Remove
              </button>
            </div>
          ))}
        </div>
      )}

      {adding === "video" && <VideoBlockForm onCancel={() => setAdding(null)} onSave={addVideo} />}
      {adding === "link" && <LinkBlockForm onCancel={() => setAdding(null)} onSave={addLink} />}
      {adding === "document" && <DocumentBlockForm onCancel={() => setAdding(null)} onSave={addDocument} uploading={uploading} />}

      {!adding && (
        <div className="flex gap-3 text-xs">
          <button type="button" onClick={() => setAdding("video")} className="font-medium text-brand hover:text-brand-dark">
            + Video
          </button>
          <button type="button" onClick={() => setAdding("document")} className="font-medium text-brand hover:text-brand-dark">
            + Document (PDF)
          </button>
          <button type="button" onClick={() => setAdding("link")} className="font-medium text-brand hover:text-brand-dark">
            + Link
          </button>
        </div>
      )}
    </div>
  );
}

function VideoBlockForm({ onSave, onCancel }: { onSave: (title: string, url: string, transcript: string) => void; onCancel: () => void }) {
  const [title, setTitle] = useState("");
  const [url, setUrl] = useState("");
  const [transcript, setTranscript] = useState("");
  return (
    <div className="space-y-1.5 rounded-lg border border-dashed border-line p-2.5">
      <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Video title" className="w-full rounded border border-line px-2 py-1 text-xs text-ink" />
      <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="YouTube/Vimeo URL or a direct video file URL" className="w-full rounded border border-line px-2 py-1 text-xs text-ink" />
      <textarea value={transcript} onChange={(e) => setTranscript(e.target.value)} placeholder="Transcript (optional)" rows={2} className="w-full rounded border border-line px-2 py-1 text-xs text-ink" />
      <div className="flex gap-2">
        <button type="button" disabled={!title.trim() || !url.trim()} onClick={() => onSave(title, url, transcript)} className="rounded bg-brand px-2.5 py-1 text-xs font-medium text-white disabled:opacity-40">
          Add
        </button>
        <button type="button" onClick={onCancel} className="text-xs text-ink-muted hover:text-ink">
          Cancel
        </button>
      </div>
    </div>
  );
}

function LinkBlockForm({ onSave, onCancel }: { onSave: (title: string, url: string, description: string) => void; onCancel: () => void }) {
  const [title, setTitle] = useState("");
  const [url, setUrl] = useState("");
  const [description, setDescription] = useState("");
  return (
    <div className="space-y-1.5 rounded-lg border border-dashed border-line p-2.5">
      <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Link title" className="w-full rounded border border-line px-2 py-1 text-xs text-ink" />
      <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://..." className="w-full rounded border border-line px-2 py-1 text-xs text-ink" />
      <input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Description (optional)" className="w-full rounded border border-line px-2 py-1 text-xs text-ink" />
      <div className="flex gap-2">
        <button type="button" disabled={!title.trim() || !url.trim()} onClick={() => onSave(title, url, description)} className="rounded bg-brand px-2.5 py-1 text-xs font-medium text-white disabled:opacity-40">
          Add
        </button>
        <button type="button" onClick={onCancel} className="text-xs text-ink-muted hover:text-ink">
          Cancel
        </button>
      </div>
    </div>
  );
}

function DocumentBlockForm({ onSave, onCancel, uploading }: { onSave: (title: string, file: File) => void; onCancel: () => void; uploading: boolean }) {
  const [title, setTitle] = useState("");
  const [file, setFile] = useState<File | null>(null);
  return (
    <div className="space-y-1.5 rounded-lg border border-dashed border-line p-2.5">
      <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Document title (optional -- defaults to filename)" className="w-full rounded border border-line px-2 py-1 text-xs text-ink" />
      <input type="file" accept="application/pdf" onChange={(e) => setFile(e.target.files?.[0] ?? null)} className="w-full text-xs text-ink" />
      <div className="flex gap-2">
        <button type="button" disabled={!file || uploading} onClick={() => file && onSave(title, file)} className="rounded bg-brand px-2.5 py-1 text-xs font-medium text-white disabled:opacity-40">
          {uploading ? "Uploading..." : "Upload & Add"}
        </button>
        <button type="button" onClick={onCancel} className="text-xs text-ink-muted hover:text-ink">
          Cancel
        </button>
      </div>
    </div>
  );
}

// ---- Lesson create/edit -----------------------------------------------

function AddLessonForm({ courseId, moduleId, onAdded }: { courseId: number; moduleId: number; onAdded: () => void }) {
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [minutes, setMinutes] = useState(10);
  const [blocks, setBlocks] = useState<LessonBlock[]>([]);
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
        content_blocks: blocks,
        order_index: Date.now(), // append-only slot; reorder afterward via drag/up-down
        estimated_minutes: minutes,
      });
      setTitle("");
      setContent("");
      setBlocks([]);
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
      <div>
        <div className="mb-1 text-xs font-medium text-ink-muted">Additional content blocks</div>
        <BlocksEditor courseId={courseId} blocks={blocks} onChange={setBlocks} />
      </div>
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

function EditLessonForm({
  courseId,
  moduleId,
  lessonId,
  onClose,
  onSaved,
}: {
  courseId: number;
  moduleId: number;
  lessonId: number;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [lesson, setLesson] = useState<LessonDetail | null>(null);
  const [content, setContent] = useState("");
  const [minutes, setMinutes] = useState(10);
  const [blocks, setBlocks] = useState<LessonBlock[]>([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.getLesson(lessonId).then((l) => {
      setLesson(l);
      setContent(l.content_markdown);
      setMinutes(l.estimated_minutes);
      setBlocks(l.content_blocks as LessonBlock[]);
    });
  }, [lessonId]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await api.updateCourseLesson(courseId, moduleId, lessonId, {
        content_markdown: content,
        content_blocks: blocks,
        estimated_minutes: minutes,
      });
      onSaved();
      onClose();
    } finally {
      setBusy(false);
    }
  }

  if (!lesson) return <div className="rounded-lg border border-line bg-white p-3 text-xs text-ink-muted">Loading lesson...</div>;

  return (
    <form onSubmit={submit} className="space-y-2 rounded-lg border border-brand/40 bg-white p-3">
      <div className="text-xs font-medium text-ink-muted">Editing &ldquo;{lesson.title}&rdquo;</div>
      <textarea value={content} onChange={(e) => setContent(e.target.value)} rows={4} className="w-full rounded-lg border border-line px-3 py-1.5 text-sm text-ink" />
      <div>
        <div className="mb-1 text-xs font-medium text-ink-muted">Additional content blocks</div>
        <BlocksEditor courseId={courseId} blocks={blocks} onChange={setBlocks} />
      </div>
      <div className="flex items-center gap-2">
        <label className="text-xs text-ink-muted">Minutes</label>
        <input type="number" value={minutes} min={1} onChange={(e) => setMinutes(Number(e.target.value))} className="w-20 rounded-lg border border-line px-2 py-1 text-sm text-ink" />
        <button type="submit" disabled={busy} className="ml-auto rounded-lg bg-brand px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-dark disabled:opacity-40">
          {busy ? "Saving..." : "Save changes"}
        </button>
        <button type="button" onClick={onClose} className="text-xs text-ink-muted hover:text-ink">
          Cancel
        </button>
      </div>
    </form>
  );
}

// ---- Quiz create/edit (all four question types + settings) --------------

function emptyQuestion(): QuizQuestionInput {
  return { type: "multiple_choice", question: "", choices: ["", ""], correct_index: 0, correct_indices: [], sample_answer: "" };
}

function QuizEditor({ courseId, moduleId, existing, onSaved }: { courseId: number; moduleId: number; existing: Chapter["quiz"]; onSaved: () => void }) {
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState(existing?.title ?? "Chapter Quiz");
  const [passingScore, setPassingScore] = useState(existing?.passing_score ?? 70);
  const [randomize, setRandomize] = useState(existing?.randomize_questions ?? false);
  const [maxAttempts, setMaxAttempts] = useState<string>(existing?.max_attempts != null ? String(existing.max_attempts) : "");
  const [questions, setQuestions] = useState<QuizQuestionInput[]>(existing ? [] : [emptyQuestion()]);
  const [busy, setBusy] = useState(false);
  const [showGrading, setShowGrading] = useState(false);

  function addQuestion() {
    setQuestions((qs) => [...qs, emptyQuestion()]);
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

  function toggleMultiCorrect(qi: number, ci: number) {
    setQuestions((qs) =>
      qs.map((q, idx) => {
        if (idx !== qi) return q;
        const has = q.correct_indices.includes(ci);
        return { ...q, correct_indices: has ? q.correct_indices.filter((c) => c !== ci) : [...q.correct_indices, ci].sort((a, b) => a - b) };
      })
    );
  }

  function changeType(qi: number, type: QuizQuestionInput["type"]) {
    setQuestions((qs) =>
      qs.map((q, idx) => {
        if (idx !== qi) return q;
        if (type === "true_false") return { ...q, type, choices: ["True", "False"], correct_index: 0 };
        if (type === "short_answer") return { ...q, type, choices: [], correct_index: null, correct_indices: [] };
        if (type === "multi_select") return { ...q, type, choices: q.choices.length ? q.choices : ["", ""], correct_indices: [] };
        return { ...q, type, choices: q.choices.length ? q.choices : ["", ""], correct_index: 0 };
      })
    );
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await api.upsertChapterQuiz(courseId, moduleId, {
        title,
        passing_score: passingScore,
        questions,
        randomize_questions: randomize,
        max_attempts: maxAttempts.trim() === "" ? null : Number(maxAttempts),
      });
      setOpen(false);
      onSaved();
    } finally {
      setBusy(false);
    }
  }

  if (existing && !open) {
    return (
      <div className="space-y-2">
        <div className="flex items-center justify-between rounded-lg border border-dashed border-line bg-white px-3 py-2 text-sm">
          <span className="text-ink">
            {existing.title} &middot; {existing.question_count} questions &middot; {existing.passing_score}% to pass
            {existing.randomize_questions && " · shuffled"}
            {existing.max_attempts !== null && ` · max ${existing.max_attempts} attempts`}
          </span>
          <div className="flex shrink-0 gap-3">
            <button onClick={() => setShowGrading((s) => !s)} className="text-xs font-medium text-brand hover:text-brand-dark">
              {showGrading ? "Hide" : "Pending grading"}
            </button>
            <button onClick={() => setOpen(true)} className="text-xs font-medium text-brand hover:text-brand-dark">
              Replace quiz
            </button>
          </div>
        </div>
        {showGrading && <GradingQueue quizId={existing.id} onGraded={onSaved} />}
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
      <div className="flex flex-wrap gap-2">
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
        <div className="flex items-center gap-1">
          <label className="text-xs text-ink-muted">Max attempts</label>
          <input
            type="number"
            value={maxAttempts}
            min={1}
            placeholder="∞"
            onChange={(e) => setMaxAttempts(e.target.value)}
            className="w-16 rounded-lg border border-line px-2 py-1 text-sm text-ink"
          />
        </div>
        <label className="flex items-center gap-1.5 text-xs text-ink-muted">
          <input type="checkbox" checked={randomize} onChange={(e) => setRandomize(e.target.checked)} />
          Shuffle question order
        </label>
      </div>

      {questions.map((q, qi) => (
        <div key={qi} className="rounded-lg border border-line p-3">
          <div className="flex items-center gap-2">
            <input
              value={q.question}
              onChange={(e) => updateQuestion(qi, { question: e.target.value })}
              placeholder={`Question ${qi + 1}`}
              required
              className="flex-1 rounded-lg border border-line px-3 py-1.5 text-sm text-ink"
            />
            <select
              value={q.type}
              onChange={(e) => changeType(qi, e.target.value as QuizQuestionInput["type"])}
              className="rounded-lg border border-line px-2 py-1.5 text-xs text-ink"
            >
              <option value="multiple_choice">Multiple choice</option>
              <option value="multi_select">Multi-select</option>
              <option value="true_false">True / False</option>
              <option value="short_answer">Short answer</option>
            </select>
          </div>

          {q.type === "short_answer" ? (
            <textarea
              value={q.sample_answer}
              onChange={(e) => updateQuestion(qi, { sample_answer: e.target.value })}
              placeholder="Sample/reference answer (shown to you when grading -- not graded automatically)"
              rows={2}
              className="mt-2 w-full rounded-lg border border-line px-2 py-1 text-sm text-ink"
            />
          ) : (
            <div className="mt-2 space-y-1.5">
              {q.choices.map((choice, ci) => (
                <div key={ci} className="flex items-center gap-2">
                  {q.type === "multi_select" ? (
                    <input type="checkbox" checked={q.correct_indices.includes(ci)} onChange={() => toggleMultiCorrect(qi, ci)} />
                  ) : (
                    <input type="radio" name={`correct-${qi}`} checked={q.correct_index === ci} onChange={() => updateQuestion(qi, { correct_index: ci })} />
                  )}
                  <input
                    value={choice}
                    onChange={(e) => updateChoice(qi, ci, e.target.value)}
                    placeholder={`Choice ${ci + 1}`}
                    required
                    disabled={q.type === "true_false"}
                    className="flex-1 rounded-lg border border-line px-2 py-1 text-sm text-ink disabled:bg-surface"
                  />
                </div>
              ))}
              {q.type !== "true_false" && (
                <button type="button" onClick={() => addChoice(qi)} className="text-xs text-brand hover:text-brand-dark">
                  + choice
                </button>
              )}
            </div>
          )}
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

// ---- Instructor grading queue (short_answer attempts) --------------------

function GradingQueue({ quizId, onGraded }: { quizId: number; onGraded: () => void }) {
  const [attempts, setAttempts] = useState<PendingAttempt[] | null>(null);
  const [scores, setScores] = useState<Record<number, string>>({});
  const [grading, setGrading] = useState<number | null>(null);

  const load = useCallback(() => {
    api.getPendingAttempts(quizId).then(setAttempts);
  }, [quizId]);

  useEffect(() => {
    load();
  }, [load]);

  async function grade(attemptId: number, passed: boolean) {
    setGrading(attemptId);
    try {
      const score = Number(scores[attemptId] ?? (passed ? 100 : 0));
      await api.gradeAttempt(attemptId, { score, passed });
      onGraded();
      load();
    } finally {
      setGrading(null);
    }
  }

  if (!attempts) return <div className="rounded-lg border border-line bg-white p-3 text-xs text-ink-muted">Loading grading queue...</div>;
  if (attempts.length === 0) return <div className="rounded-lg border border-line bg-white p-3 text-xs text-ink-muted">Nothing waiting on grading.</div>;

  return (
    <div className="space-y-3 rounded-lg border border-line bg-white p-3">
      {attempts.map((a) => (
        <div key={a.id} className="rounded-lg border border-line p-3">
          <div className="text-sm font-medium text-ink">
            {a.user_full_name || a.user_email} <span className="font-normal text-ink-muted">({a.user_email})</span>
          </div>
          <div className="text-xs text-ink-muted">Submitted {new Date(a.attempted_at).toLocaleString()}</div>
          <div className="mt-2 space-y-2">
            {a.questions.map((q, qi) => (
              <div key={qi} className="rounded bg-surface p-2 text-xs">
                <div className="font-medium text-ink">{q.question}</div>
                <div className="mt-1 text-ink-muted">
                  Answer: <span className="text-ink">{JSON.stringify(a.answers[qi])}</span>
                </div>
                {q.type === "short_answer" && q.sample_answer && <div className="mt-1 italic text-ink-muted">Sample answer: {q.sample_answer}</div>}
              </div>
            ))}
          </div>
          <div className="mt-3 flex items-center gap-2">
            <label className="text-xs text-ink-muted">Score</label>
            <input
              type="number"
              min={0}
              max={100}
              value={scores[a.id] ?? ""}
              onChange={(e) => setScores((s) => ({ ...s, [a.id]: e.target.value }))}
              placeholder="0-100"
              className="w-20 rounded-lg border border-line px-2 py-1 text-sm text-ink"
            />
            <button
              onClick={() => grade(a.id, true)}
              disabled={grading === a.id}
              className="rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-700 disabled:opacity-40"
            >
              Pass
            </button>
            <button
              onClick={() => grade(a.id, false)}
              disabled={grading === a.id}
              className="rounded-lg border border-line px-3 py-1.5 text-xs font-medium text-ink hover:bg-surface disabled:opacity-40"
            >
              Fail
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

// ---- Chapter create -------------------------------------------------------

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

function EditChapterForm({ courseId, chapter, onClose, onSaved }: { courseId: number; chapter: Chapter; onClose: () => void; onSaved: () => void }) {
  const [title, setTitle] = useState(chapter.title);
  const [objective, setObjective] = useState(chapter.objective);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await api.updateChapter(courseId, chapter.id, { title, objective });
      onSaved();
      onClose();
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="mt-2 space-y-2 rounded-lg border border-brand/40 bg-white p-3">
      <input value={title} onChange={(e) => setTitle(e.target.value)} required className="w-full rounded-lg border border-line px-3 py-1.5 text-sm text-ink" />
      <input value={objective} onChange={(e) => setObjective(e.target.value)} placeholder="Objective" className="w-full rounded-lg border border-line px-3 py-1.5 text-sm text-ink" />
      <div className="flex gap-2">
        <button type="submit" disabled={busy} className="rounded-lg bg-brand px-3 py-1.5 text-xs font-medium text-white disabled:opacity-40">
          {busy ? "Saving..." : "Save"}
        </button>
        <button type="button" onClick={onClose} className="text-xs text-ink-muted hover:text-ink">
          Cancel
        </button>
      </div>
    </form>
  );
}

// ---- Page ------------------------------------------------------------

export default function EditCoursePage() {
  const params = useParams<{ id: string }>();
  const courseId = Number(params.id);

  const [summary, setSummary] = useState<CourseSummary | null>(null);
  const [detail, setDetail] = useState<CourseDetail | null>(null);
  const [roster, setRoster] = useState<RosterRow[] | null>(null);
  const [error, setError] = useState("");
  const [publishing, setPublishing] = useState(false);
  const [editingChapterId, setEditingChapterId] = useState<number | null>(null);
  const [editingLesson, setEditingLesson] = useState<{ moduleId: number; lessonId: number } | null>(null);
  const [dragChapterIndex, setDragChapterIndex] = useState<number | null>(null);
  const [dragLesson, setDragLesson] = useState<{ chapterId: number; index: number } | null>(null);
  const [validityDays, setValidityDays] = useState<string>("");
  const [savingValidity, setSavingValidity] = useState(false);

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
      setValidityDays(d.certificate_validity_days != null ? String(d.certificate_validity_days) : "");
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

  async function saveValidity() {
    setSavingValidity(true);
    try {
      const days = validityDays.trim() === "" ? 0 : Number(validityDays); // 0 clears it back to never-expires -- see backend's update_course
      await api.updateCourse(courseId, { certificate_validity_days: days });
      await load();
    } finally {
      setSavingValidity(false);
    }
  }

  async function persistChapterOrder(ordered: Chapter[]) {
    await Promise.all(ordered.map((ch, i) => api.updateChapter(courseId, ch.id, { order_index: i + 1 })));
    await load();
  }

  async function persistLessonOrder(chapterId: number, ordered: Chapter["lessons"]) {
    await Promise.all(ordered.map((l, i) => api.updateCourseLesson(courseId, chapterId, l.id, { order_index: i + 1 })));
    await load();
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

      <div className="mt-6 flex items-center gap-2 rounded-lg border border-line bg-surface px-4 py-3">
        <label className="text-sm text-ink">Certificate validity (days)</label>
        <input
          type="number"
          min={0}
          value={validityDays}
          onChange={(e) => setValidityDays(e.target.value)}
          placeholder="Never expires"
          className="w-28 rounded-lg border border-line px-2 py-1 text-sm text-ink"
        />
        <button onClick={saveValidity} disabled={savingValidity} className="rounded-lg border border-line px-3 py-1.5 text-xs font-medium text-ink hover:bg-white disabled:opacity-40">
          {savingValidity ? "..." : "Save"}
        </button>
        <span className="text-xs text-ink-muted">Leave blank for certificates that never expire. Only affects certificates issued after this change.</span>
      </div>

      <h2 className="mt-10 text-lg font-semibold text-ink">Chapters</h2>
      <div className="mt-4 space-y-6">
        {detail.chapters.map((chapter, ci) => (
          <div
            key={chapter.id}
            onDragOver={(e) => e.preventDefault()}
            onDrop={() => {
              if (dragChapterIndex !== null && dragChapterIndex !== ci) persistChapterOrder(moveItem(detail.chapters, dragChapterIndex, ci));
              setDragChapterIndex(null);
            }}
            className="rounded-xl border border-line bg-surface p-4"
          >
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0 flex-1">
                <div className="font-medium text-ink">{chapter.title}</div>
                {chapter.objective && <p className="text-xs text-ink-muted">{chapter.objective}</p>}
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <button onClick={() => setEditingChapterId(editingChapterId === chapter.id ? null : chapter.id)} className="text-xs font-medium text-brand hover:text-brand-dark">
                  Edit
                </button>
                <ReorderControls
                  onMoveStart={() => setDragChapterIndex(ci)}
                  onUp={() => ci > 0 && persistChapterOrder(moveItem(detail.chapters, ci, ci - 1))}
                  onDown={() => ci < detail.chapters.length - 1 && persistChapterOrder(moveItem(detail.chapters, ci, ci + 1))}
                  disabledUp={ci === 0}
                  disabledDown={ci === detail.chapters.length - 1}
                />
              </div>
            </div>

            {editingChapterId === chapter.id && (
              <EditChapterForm courseId={courseId} chapter={chapter} onClose={() => setEditingChapterId(null)} onSaved={load} />
            )}

            <div className="mt-3 space-y-1.5">
              {chapter.lessons.map((l, li) => (
                <div
                  key={l.id}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={() => {
                    if (dragLesson && dragLesson.chapterId === chapter.id && dragLesson.index !== li) {
                      persistLessonOrder(chapter.id, moveItem(chapter.lessons, dragLesson.index, li));
                    }
                    setDragLesson(null);
                  }}
                >
                  {editingLesson?.lessonId === l.id ? (
                    <EditLessonForm
                      courseId={courseId}
                      moduleId={chapter.id}
                      lessonId={l.id}
                      onClose={() => setEditingLesson(null)}
                      onSaved={load}
                    />
                  ) : (
                    <div className="flex items-center justify-between rounded-lg border border-line bg-white px-3 py-2 text-sm text-ink">
                      <span>
                        {l.title} <span className="text-xs text-ink-muted">({l.estimated_minutes} min)</span>
                      </span>
                      <div className="flex shrink-0 items-center gap-2">
                        <button onClick={() => setEditingLesson({ moduleId: chapter.id, lessonId: l.id })} className="text-xs font-medium text-brand hover:text-brand-dark">
                          Edit
                        </button>
                        <ReorderControls
                          onMoveStart={() => setDragLesson({ chapterId: chapter.id, index: li })}
                          onUp={() => li > 0 && persistLessonOrder(chapter.id, moveItem(chapter.lessons, li, li - 1))}
                          onDown={() => li < chapter.lessons.length - 1 && persistLessonOrder(chapter.id, moveItem(chapter.lessons, li, li + 1))}
                          disabledUp={li === 0}
                          disabledDown={li === chapter.lessons.length - 1}
                        />
                      </div>
                    </div>
                  )}
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
