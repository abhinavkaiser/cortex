"use client";

// The "what is this thing, in one picture" graphic -- deliberately simpler
// and visually distinct from the detailed PipelineMap below it. One box,
// one loop. Everything after this is that same box, opened up.

export function LanguageModelHero() {
  return (
    <div className="rounded-xl border border-line bg-surface p-6">
      <svg viewBox="0 0 720 220" className="w-full">
        <defs>
          <marker id="hero-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M0,0 L10,5 L0,10 z" className="fill-slate-500" />
          </marker>
        </defs>

        {/* input bubble */}
        <rect x={10} y={78} width={150} height={64} rx={12} className="fill-slate-950 stroke-slate-700" strokeWidth={2} />
        <text x={85} y={104} textAnchor="middle" className="fill-slate-200 text-[13px] font-medium">
          "...sent the
        </text>
        <text x={85} y={122} textAnchor="middle" className="fill-slate-200 text-[13px] font-medium">
          proposal."
        </text>
        <text x={85} y={68} textAnchor="middle" className="fill-slate-500 text-[11px] uppercase tracking-wide">
          your text
        </text>

        <line x1={162} y1={110} x2={228} y2={110} className="stroke-slate-500" strokeWidth={2} markerEnd="url(#hero-arrow)" />

        {/* the model box */}
        <rect x={232} y={58} width={256} height={104} rx={16} className="fill-brand/15 stroke-brand" strokeWidth={2} />
        <text x={360} y={100} textAnchor="middle" className="fill-slate-100 text-[16px] font-semibold">
          Language model
        </text>
        <text x={360} y={122} textAnchor="middle" className="fill-slate-300 text-[12px]">
          a function trained to guess
        </text>
        <text x={360} y={138} textAnchor="middle" className="fill-slate-300 text-[12px]">
          the single most plausible next token
        </text>

        <line x1={490} y1={110} x2={556} y2={110} className="stroke-slate-500" strokeWidth={2} markerEnd="url(#hero-arrow)" />

        {/* output bubble */}
        <rect x={560} y={78} width={150} height={64} rx={12} className="fill-slate-950 stroke-slate-700" strokeWidth={2} />
        <text x={635} y={110} textAnchor="middle" className="fill-amber-300 text-[15px] font-semibold">
          " Maria"
        </text>
        <text x={635} y={68} textAnchor="middle" className="fill-slate-500 text-[11px] uppercase tracking-wide">
          one new token
        </text>

        {/* loop back */}
        <path
          d="M 635 142 L 635 190 L 85 190 L 85 146"
          fill="none"
          className="stroke-slate-600"
          strokeWidth={2}
          strokeDasharray="5 5"
          markerEnd="url(#hero-arrow)"
        />
        <text x={360} y={210} textAnchor="middle" className="fill-slate-500 text-[12px]">
          that new token gets appended, and the whole thing runs again
        </text>
      </svg>

      <p className="mt-2 text-sm text-ink-muted">
        That's the entire concept in one box: a language model is a function that takes in text and predicts one plausible next chunk of it,
        over and over. Everything below is what's actually happening inside that one box -- four steps, run every single time it does this.
      </p>
    </div>
  );
}
