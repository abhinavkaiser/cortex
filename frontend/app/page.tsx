"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit() {
    setSubmitting(true);
    setError("");
    try {
      const res = mode === "login" ? await api.login(email, password) : await api.register(email, password, fullName);
      localStorage.setItem("access_token", res.access_token);
      localStorage.setItem("user_id", String(res.user_id));
      router.push(res.needs_onboarding ? "/onboarding" : "/dashboard/common-core");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-sm flex-col justify-center px-6">
      <h1 className="text-2xl font-semibold">Cortex AI</h1>
      <p className="mt-1 text-sm text-slate-500">Interactive AI training, one track at a time.</p>

      <div className="mt-8 space-y-3">
        {mode === "register" && (
          <input
            placeholder="Full name"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            className="w-full rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-sm"
          />
        )}
        <input
          placeholder="Email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-sm"
        />
        <input
          placeholder="Password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-sm"
        />
        {error && <p className="text-sm text-red-400">{error}</p>}
        <button onClick={submit} disabled={submitting} className="w-full rounded-lg bg-brand px-4 py-2.5 text-sm font-medium disabled:opacity-40">
          {submitting ? "..." : mode === "login" ? "Log in" : "Create account"}
        </button>
      </div>

      <button onClick={() => setMode(mode === "login" ? "register" : "login")} className="mt-4 text-xs text-slate-500 hover:text-slate-300">
        {mode === "login" ? "Need an account? Register" : "Already have an account? Log in"}
      </button>
    </main>
  );
}
