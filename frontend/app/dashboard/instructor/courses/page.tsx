"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { CourseSummary } from "@/lib/types";

function slugify(title: string): string {
  return title
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}

export default function InstructorCoursesPage() {
  const router = useRouter();
  const [courses, setCourses] = useState<CourseSummary[] | null>(null);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("");
  const [creating, setCreating] = useState(false);

  async function load() {
    try {
      const all = await api.getCourses();
      const myId = Number(localStorage.getItem("user_id"));
      setCourses(all.filter((c) => c.instructor_id === myId));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load courses.");
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function createCourse(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    setCreating(true);
    try {
      const course = await api.createCourse({ slug: slugify(title), title, description, category });
      router.push(`/dashboard/instructor/courses/${course.id}/edit`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not create course.");
      setCreating(false);
    }
  }

  if (error) return <main className="px-6 py-12 text-sm text-red-600">{error}</main>;
  if (!courses) return <main className="px-6 py-12 text-sm text-ink-muted">Loading...</main>;

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Your courses</h1>
        <button onClick={() => setShowForm((v) => !v)} className="rounded-lg bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-brand-dark">
          {showForm ? "Cancel" : "New Course"}
        </button>
      </div>

      {showForm && (
        <form onSubmit={createCourse} className="mt-6 space-y-3 rounded-xl border border-line bg-surface p-5">
          <div>
            <label className="text-xs font-medium text-ink-muted">Title</label>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
              className="mt-1 w-full rounded-lg border border-line bg-white px-3 py-2 text-sm text-ink"
              placeholder="e.g. Prompt Engineering for Teams"
            />
            {title && <p className="mt-1 text-xs text-ink-muted">Slug: {slugify(title)}</p>}
          </div>
          <div>
            <label className="text-xs font-medium text-ink-muted">Category</label>
            <input
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="mt-1 w-full rounded-lg border border-line bg-white px-3 py-2 text-sm text-ink"
              placeholder="e.g. AI Skills"
            />
          </div>
          <div>
            <label className="text-xs font-medium text-ink-muted">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="mt-1 w-full rounded-lg border border-line bg-white px-3 py-2 text-sm text-ink"
            />
          </div>
          <button type="submit" disabled={creating} className="rounded-lg bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-brand-dark disabled:opacity-40">
            {creating ? "Creating..." : "Create course"}
          </button>
        </form>
      )}

      {courses.length === 0 ? (
        <p className="mt-8 text-sm text-ink-muted">You haven&apos;t created any courses yet.</p>
      ) : (
        <div className="mt-8 space-y-2">
          {courses.map((c) => (
            <Link
              key={c.id}
              href={`/dashboard/instructor/courses/${c.id}/edit`}
              className="flex items-center justify-between rounded-lg border border-line px-4 py-3 transition hover:border-brand/40"
            >
              <div>
                <div className="text-sm font-medium text-ink">{c.title}</div>
                <div className="text-xs text-ink-muted">
                  {c.chapter_count} chapters &middot; {c.lesson_count} lessons
                </div>
              </div>
              <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${c.is_published ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"}`}>
                {c.is_published ? "Published" : "Draft"}
              </span>
            </Link>
          ))}
        </div>
      )}
    </main>
  );
}
