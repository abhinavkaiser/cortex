"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { Certificate } from "@/lib/types";

export default function CertificatesPage() {
  const [certs, setCerts] = useState<Certificate[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .getMyCertificates()
      .then(setCerts)
      .catch((e) => setError(e instanceof Error ? e.message : "Could not load certificates."));
  }, []);

  if (error) return <main className="px-6 py-12 text-sm text-red-600">{error}</main>;
  if (!certs) return <main className="px-6 py-12 text-sm text-ink-muted">Loading...</main>;

  return (
    <main className="mx-auto max-w-2xl px-6 py-12">
      <h1 className="text-2xl font-semibold">Your certificates</h1>
      <p className="mt-1 text-sm text-ink-muted">Earned automatically once every chapter and quiz in a course is complete.</p>

      {certs.length === 0 ? (
        <p className="mt-8 text-sm text-ink-muted">
          No certificates yet --{" "}
          <Link href="/dashboard/courses" className="text-brand hover:text-brand-dark">
            browse courses
          </Link>{" "}
          to get started.
        </p>
      ) : (
        <div className="mt-8 space-y-3">
          {certs.map((c) => (
            <div key={c.id} className="flex items-center justify-between rounded-xl border border-line bg-surface p-4">
              <div>
                <div className="font-medium text-ink">{c.course_title}</div>
                <div className="text-xs text-ink-muted">Issued {new Date(c.issued_at).toLocaleDateString()}</div>
              </div>
              <Link href={`/certificates/verify/${c.certificate_code}`} className="text-sm font-medium text-brand hover:text-brand-dark">
                View &rarr;
              </Link>
            </div>
          ))}
        </div>
      )}
    </main>
  );
}
