"use client";

export function RagHero() {
  return (
    <div className="rounded-xl border border-line bg-surface p-6">
      <svg viewBox="0 0 760 220" className="w-full">
        <defs>
          <marker id="rag-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M0,0 L10,5 L0,10 z" className="fill-slate-500" />
          </marker>
        </defs>

        {/* question */}
        <rect x={10} y={78} width={140} height={64} rx={12} className="fill-slate-950 stroke-slate-700" strokeWidth={2} />
        <text x={80} y={106} textAnchor="middle" className="fill-slate-200 text-[12px] font-medium">
          "Do I need a
        </text>
        <text x={80} y={124} textAnchor="middle" className="fill-slate-200 text-[12px] font-medium">
          receipt for $50?"
        </text>
        <text x={80} y={68} textAnchor="middle" className="fill-slate-500 text-[11px] uppercase tracking-wide">
          your question
        </text>

        <line x1={152} y1={110} x2={200} y2={110} className="stroke-slate-500" strokeWidth={2} markerEnd="url(#rag-arrow)" />

        {/* documents feeding into search, from below */}
        <rect x={155} y={172} width={140} height={40} rx={8} className="fill-slate-900 stroke-slate-700" strokeWidth={1.5} strokeDasharray="4 3" />
        <text x={225} y={196} textAnchor="middle" className="fill-slate-400 text-[11px]">
          your documents
        </text>
        <line x1={225} y1={172} x2={225} y2={148} className="stroke-slate-600" strokeWidth={2} markerEnd="url(#rag-arrow)" />

        {/* search box */}
        <rect x={204} y={78} width={140} height={64} rx={12} className="fill-slate-950 stroke-slate-700" strokeWidth={2} />
        <text x={274} y={104} textAnchor="middle" className="fill-slate-200 text-[13px] font-medium">
          Search your
        </text>
        <text x={274} y={122} textAnchor="middle" className="fill-slate-200 text-[13px] font-medium">
          documents
        </text>

        <line x1={346} y1={110} x2={412} y2={110} className="stroke-slate-500" strokeWidth={2} markerEnd="url(#rag-arrow)" />

        {/* the model box, same visual language as the language-model hero */}
        <rect x={416} y={58} width={220} height={104} rx={16} className="fill-brand/15 stroke-brand" strokeWidth={2} />
        <text x={526} y={100} textAnchor="middle" className="fill-slate-100 text-[15px] font-semibold">
          Language model
        </text>
        <text x={526} y={122} textAnchor="middle" className="fill-slate-300 text-[12px]">
          + the excerpt it just
        </text>
        <text x={526} y={138} textAnchor="middle" className="fill-slate-300 text-[12px]">
          got handed
        </text>

        <line x1={638} y1={110} x2={694} y2={110} className="stroke-slate-500" strokeWidth={2} markerEnd="url(#rag-arrow)" />

        {/* grounded answer */}
        <rect x={698} y={78} width={60} height={64} rx={12} className="fill-slate-950 stroke-emerald-500/60" strokeWidth={2} />
        <text x={728} y={106} textAnchor="middle" className="fill-emerald-300 text-[11px] font-medium">
          real
        </text>
        <text x={728} y={122} textAnchor="middle" className="fill-emerald-300 text-[11px] font-medium">
          answer
        </text>
      </svg>

      <p className="mt-2 text-sm text-ink-muted">
        Same box as before, with one addition: before it answers, it's handed a real excerpt pulled from your own documents. The model still
        only ever predicts the next token -- the difference is what it's predicting from.
      </p>
    </div>
  );
}
