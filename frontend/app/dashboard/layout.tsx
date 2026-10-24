"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { api } from "@/lib/api";
import type { UserRole } from "@/lib/types";

// There was no shared top-level nav before the course system landed --
// every /dashboard/* page was a standalone screen with no way to get from
// one section to another except typing a URL. Added here, once, rather
// than duplicated per page, since it's now needed to link Daily Pulse /
// Sandbox / Courses / Certificates together, and to gate the Instructor
// link behind role. Tracks/Onboarding links removed -- see README's
// "Formerly Tracks, now migrated into Courses": the fixed 3-Track curriculum now lives inside
// Courses (GET /dashboard/courses), so Courses is the sole content catalog.
const NAV_LINKS: { href: string; label: string }[] = [
  { href: "/dashboard/learn", label: "Learning path" },
  { href: "/dashboard/courses", label: "Courses" },
  { href: "/dashboard/daily-pulse", label: "Daily Pulse" },
  { href: "/dashboard/sandbox", label: "Sandbox" },
  { href: "/dashboard/certificates", label: "Certificates" },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [sharedDemo, setSharedDemo] = useState(false);
  const [role, setRole] = useState<UserRole | null>(null);

  useEffect(() => {
    const userId = Number(localStorage.getItem("user_id"));
    if (!userId) return;
    // Role isn't behind its own endpoint (see schemas/user.py's
    // UserProgressOut) -- /progress is already the "current session user"
    // fetch every dashboard page makes, so this reuses that instead of
    // adding a parallel /me call.
    api
      .getProgress(userId)
      .then((p) => { setRole(p.role); setSharedDemo(p.email === "demo@cortex.ai"); })
      .catch(() => {});
  }, []);

  const isInstructor = role === "instructor" || role === "admin";

  return (
    <div className="min-h-screen bg-white">
      <header className="sticky top-0 z-10 border-b border-line bg-white">
        <nav className="mx-auto flex max-w-5xl items-center gap-6 overflow-x-auto px-6 py-3">
          <Link href="/dashboard/learn" className="shrink-0 text-lg font-semibold text-ink">
            Cortex AI
          </Link>
          <div className="flex flex-1 items-center gap-5 whitespace-nowrap text-sm">
            {NAV_LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={`transition ${
                  pathname?.startsWith(link.href) ? "font-medium text-brand" : "text-ink-muted hover:text-ink"
                }`}
              >
                {link.label}
              </Link>
            ))}
            {isInstructor && (
              <Link
                href="/dashboard/instructor/courses"
                className={`transition ${
                  pathname?.startsWith("/dashboard/instructor") ? "font-medium text-brand" : "text-ink-muted hover:text-ink"
                }`}
              >
                Instructor
              </Link>
            )}
            <button className="text-xs text-ink-muted underline" onClick={() => { localStorage.removeItem("access_token"); localStorage.removeItem("user_id"); window.location.href = "/"; }}>{sharedDemo ? "Shared demo · Sign out" : "Sign out"}</button>
          </div>
        </nav>
      </header>
      {children}
    </div>
  );
}
