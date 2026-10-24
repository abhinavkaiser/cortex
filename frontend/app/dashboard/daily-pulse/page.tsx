import { DailyPulseCard } from "@/components/daily-pulse/DailyPulseCard";

export default function DailyPulsePage() {
  return (
    <main className="mx-auto max-w-2xl px-6 py-12">
      <h1 className="text-2xl font-semibold">Latest AI developments</h1>
      <p className="mt-1 text-sm text-ink-muted">
        Source-linked digests, exercises and questions for each specialization. Check the publication date; these digests do not automatically revise the course lessons.
      </p>
      <div className="mt-6">
        <DailyPulseCard />
      </div>
    </main>
  );
}
