"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import type { CertificateVerify } from "@/lib/types";

// PUBLIC, no-auth page -- deliberately outside app/dashboard so it doesn't
// inherit that layout's nav (which assumes a logged-in session) or trigger
// any auth redirect. Matches the backend's GET /api/certificates/verify/
// {code}, which is likewise unauthenticated (see routes/certificates.py).
export default function VerifyCertificatePage() {
  const params = useParams<{ code: string }>();
  const [cert, setCert] = useState<CertificateVerify | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .verifyCertificate(params.code)
      .then(setCert)
      .catch((e) => setError(e instanceof Error ? e.message : "Could not verify this certificate."))
      .finally(() => setLoading(false));
  }, [params.code]);

  return (
    <main className="mx-auto flex min-h-screen max-w-lg flex-col items-center justify-center px-6 text-center">
      <div className="text-lg font-semibold text-ink">Cortex AI</div>

      {loading ? (
        <p className="mt-6 text-sm text-ink-muted">Verifying...</p>
      ) : error || !cert ? (
        <div className="mt-6 rounded-xl border border-red-500/30 bg-red-50 p-6">
          <div className="font-medium text-red-600">Certificate not found</div>
          <p className="mt-1 text-sm text-ink-muted">This code doesn&apos;t match any issued certificate.</p>
        </div>
      ) : (
        <div className="mt-6 w-full rounded-xl border border-line bg-surface p-8">
          <div className="text-xs font-medium uppercase tracking-wide text-brand">Certificate of Completion</div>
          <div className="mt-3 text-2xl font-semibold text-ink">{cert.learner_name}</div>
          <div className="mt-1 text-sm text-ink-muted">has completed</div>
          <div className="mt-2 text-lg font-medium text-ink">{cert.course_title}</div>
          <div className="mt-4 text-xs text-ink-muted">Issued {new Date(cert.issued_at).toLocaleDateString()}</div>
        </div>
      )}
    </main>
  );
}
