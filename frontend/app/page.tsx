"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

// Login removed for now (single-user local demo) -- auto-authenticates a
// fixed demo account instead of showing a form. The backend's real
// auth/JWT system is untouched (see app/api/routes/auth.py) -- bringing
// login back later is just restoring a form that POSTs to the same
// /api/auth/login and /api/auth/register endpoints this already calls,
// not rebuilding anything.
const DEMO_EMAIL = "demo@cortex.ai";
const DEMO_PASSWORD = "demopass123";

export default function AutoLoginPage() {
  const router = useRouter();
  const [error, setError] = useState("");

  useEffect(() => {
    async function go() {
      try {
        let res;
        try {
          res = await api.login(DEMO_EMAIL, DEMO_PASSWORD);
        } catch {
          // First run on a fresh DB -- the demo account doesn't exist yet.
          res = await api.register(DEMO_EMAIL, DEMO_PASSWORD, "Demo User");
        }
        localStorage.setItem("access_token", res.access_token);
        localStorage.setItem("user_id", String(res.user_id));
        router.replace(res.needs_onboarding ? "/onboarding" : "/dashboard/common-core");
      } catch (e) {
        setError(e instanceof Error ? e.message : "Could not reach the backend.");
      }
    }
    go();
  }, [router]);

  return (
    <main className="mx-auto flex min-h-screen max-w-sm flex-col items-center justify-center px-6 text-center">
      <h1 className="text-2xl font-semibold">Cortex AI</h1>
      {error ? <p className="mt-4 text-sm text-red-400">{error}</p> : <p className="mt-2 text-sm text-slate-500">Loading...</p>}
    </main>
  );
}
