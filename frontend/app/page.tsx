"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [registering, setRegistering] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const id = Number(localStorage.getItem("user_id"));
    if (id && localStorage.getItem("access_token")) api.getProgress(id).then(user => {
      if (user.email !== "demo@cortex.ai") router.replace("/dashboard/learn");
    }).catch(() => {});
  }, [router]);

  async function signIn(event?: React.FormEvent, demo = false) {
    event?.preventDefault(); setBusy(true); setError("");
    try {
      const result = demo ? await api.login("demo@cortex.ai", "demopass123") : registering ? await api.register(email, password, name) : await api.login(email, password);
      localStorage.setItem("access_token", result.access_token);
      localStorage.setItem("user_id", String(result.user_id));
      router.replace("/dashboard/learn");
    } catch (e) { setError(e instanceof Error ? e.message : "Could not sign in."); }
    finally { setBusy(false); }
  }

  return <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6 py-12">
    <p className="text-xs font-semibold uppercase tracking-wide text-brand">Cortex AI</p>
    <h1 className="mt-3 text-3xl font-semibold">Learn AI by doing</h1>
    <p className="mt-3 text-sm text-ink-muted">Work through practical cases, understand your mistakes and build toward your first technical project. Use your own account to keep your attempts separate.</p>
    <form onSubmit={signIn} className="mt-8 space-y-4">
      {registering && <label className="block text-sm">Name<input required maxLength={255} autoComplete="name" value={name} onChange={e => setName(e.target.value)} className="mt-1 w-full rounded-lg border border-line p-3" /></label>}
      <label className="block text-sm">Email<input type="email" required autoComplete="email" value={email} onChange={e => setEmail(e.target.value)} className="mt-1 w-full rounded-lg border border-line p-3" /></label>
      <label className="block text-sm">Password<input type="password" required minLength={8} maxLength={72} autoComplete={registering ? "new-password" : "current-password"} value={password} onChange={e => setPassword(e.target.value)} className="mt-1 w-full rounded-lg border border-line p-3" /></label>
      {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
      <button disabled={busy} className="w-full rounded-lg bg-brand p-3 text-sm font-medium text-white disabled:opacity-40">{busy ? "Please wait…" : registering ? "Create my account" : "Sign in"}</button>
    </form>
    <button onClick={() => { setRegistering(!registering); setError(""); }} className="mt-4 text-sm text-brand underline">{registering ? "Already have an account? Sign in" : "Create an account"}</button>
    <button disabled={busy} onClick={() => signIn(undefined, true)} className="mt-6 text-sm text-ink-muted underline">Explore the shared demo</button>
    <p className="mt-2 text-xs text-ink-muted">Demo attempts and progress are shared with other demo visitors.</p>
  </main>;
}
