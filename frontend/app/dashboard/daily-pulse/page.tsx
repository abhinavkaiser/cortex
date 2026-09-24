import { DailyPulseCard } from "@/components/daily-pulse/DailyPulseCard";

export default function DailyPulsePage() {
  return (
    <main className="mx-auto max-w-2xl px-6 py-12">
      <h1 className="text-2xl font-semibold">Today&apos;s Pulse</h1>
      <p className="mt-1 text-sm text-ink-muted">
        A 2-minute read, a hands-on exercise, and a quiz for each specialization -- generated fresh every morning.
      </p>
      <div className="mt-6">
        <DailyPulseCard />
      </div>
    </main>
  );
}
