import Link from "next/link";
import type { Lesson } from "@/lib/types";

// onCompleted isn't used here anymore (completing now happens on the lesson
// reading page, not from this list) -- kept as a prop so callers don't need
// to change, and re-fetching on return-to-list still keeps state accurate.
function LessonRow({ lesson }: { lesson: Lesson }) {
  return (
    <Link
      href={`/dashboard/lessons/${lesson.id}`}
      className={`flex items-center justify-between rounded-lg border px-4 py-3 transition hover:border-slate-700 ${
        lesson.completed ? "border-slate-800 bg-slate-900/40" : "border-slate-800"
      }`}
    >
      <div>
        <div className={`text-sm font-medium ${lesson.completed ? "text-slate-500 line-through" : "text-slate-100"}`}>{lesson.title}</div>
        <div className="text-xs text-slate-500">{lesson.estimated_minutes} min</div>
      </div>
      {lesson.completed ? (
        <span className="shrink-0 text-xs font-medium text-emerald-400">✓ Done</span>
      ) : (
        <span className="shrink-0 text-xs font-medium text-brand">Read →</span>
      )}
    </Link>
  );
}

export function LessonList({ lessons }: { lessons: Lesson[]; onCompleted?: () => void }) {
  if (lessons.length === 0) {
    return <p className="mt-4 text-sm text-slate-500">No lessons in this section yet.</p>;
  }

  // Group by module when the curriculum has real modules (e.g. AI Leader's
  // 6-module structure); lessons without a module (Common Core, and any
  // track lesson predating the Module concept) just render as a flat list.
  const hasModules = lessons.some((l) => l.module_id !== null);
  if (!hasModules) {
    return (
      <div className="mt-4 space-y-2">
        {lessons.map((lesson) => (
          <LessonRow key={lesson.id} lesson={lesson} />
        ))}
      </div>
    );
  }

  const moduleOrder: number[] = [];
  const byModule = new Map<number, Lesson[]>();
  for (const lesson of lessons) {
    const key = lesson.module_id ?? -1;
    if (!byModule.has(key)) {
      byModule.set(key, []);
      moduleOrder.push(key);
    }
    byModule.get(key)!.push(lesson);
  }

  return (
    <div className="mt-6 space-y-8">
      {moduleOrder.map((moduleId) => {
        const moduleLessons = byModule.get(moduleId)!;
        const completedCount = moduleLessons.filter((l) => l.completed).length;
        return (
          <div key={moduleId}>
            <div className="mb-2 flex items-baseline justify-between">
              <h2 className="text-sm font-semibold text-slate-200">{moduleLessons[0].module_title ?? "Other lessons"}</h2>
              <span className="text-xs text-slate-500">
                {completedCount} / {moduleLessons.length}
              </span>
            </div>
            <div className="space-y-2">
              {moduleLessons.map((lesson) => (
                <LessonRow key={lesson.id} lesson={lesson} />
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
