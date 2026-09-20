"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";
import type { TrackSlug } from "@/lib/types";

const TRACKS: { slug: TrackSlug; name: string; description: string }[] = [
  { slug: "leader", name: "AI Leader", description: "Strategic and organizational AI literacy for execs and managers." },
  { slug: "practitioner", name: "AI Practitioner", description: "Practical, day-to-day AI skills for people using AI tools in their work." },
  { slug: "developer", name: "AI Developer", description: "Technical depth for people building with AI/ML." },
];

export default function OnboardingPage() {
  const router = useRouter();
  const [selected, setSelected] = useState<TrackSlug | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function confirm() {
    if (!selected) return;
    setSubmitting(true);
    setError("");
    try {
      await api.completeOnboarding(selected);
      // Onboarding assigns the track, but the UI still gates on Common
      // Core -- see dashboard/common-core, which every user lands on next
      // regardless of which track they just picked.
      router.push("/dashboard/common-core");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <h1 className="text-3xl font-semibold">Which track fits you best?</h1>
      <p className="mt-2 text-slate-400">
        You&apos;ll start with the shared Common Core either way -- this just decides what unlocks after that.
      </p>

      <div className="mt-8 grid gap-4 sm:grid-cols-3">
        {TRACKS.map((t) => (
          <button
            key={t.slug}
            onClick={() => setSelected(t.slug)}
            className={`rounded-xl border p-5 text-left transition ${
              selected === t.slug ? "border-brand bg-brand/10" : "border-slate-800 hover:border-slate-700"
            }`}
          >
            <div className="font-medium">{t.name}</div>
            <div className="mt-1 text-sm text-slate-400">{t.description}</div>
          </button>
        ))}
      </div>

      {error && <p className="mt-4 text-sm text-red-400">{error}</p>}

      <button
        onClick={confirm}
        disabled={!selected || submitting}
        className="mt-8 rounded-lg bg-brand px-5 py-2.5 font-medium disabled:opacity-40"
      >
        {submitting ? "Setting up..." : "Continue"}
      </button>
    </main>
  );
}
