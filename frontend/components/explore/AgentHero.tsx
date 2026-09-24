"use client";

export function AgentHero() {
  return (
    <div className="rounded-xl border border-line bg-surface p-6">
      <svg viewBox="0 0 720 240" className="w-full">
        <defs>
          <marker id="agent-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M0,0 L10,5 L0,10 z" className="fill-slate-500" />
          </marker>
          <marker id="agent-arrow-amber" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M0,0 L10,5 L0,10 z" className="fill-amber-400" />
          </marker>
        </defs>

        {/* goal */}
        <rect x={10} y={78} width={140} height={64} rx={12} className="fill-slate-950 stroke-slate-700" strokeWidth={2} />
        <text x={80} y={106} textAnchor="middle" className="fill-slate-200 text-[12px] font-medium">
          "Is $360 over
        </text>
        <text x={80} y={124} textAnchor="middle" className="fill-slate-200 text-[12px] font-medium">
          our limit?"
        </text>
        <text x={80} y={68} textAnchor="middle" className="fill-slate-500 text-[11px] uppercase tracking-wide">
          the goal
        </text>

        <line x1={152} y1={110} x2={208} y2={110} className="stroke-slate-500" strokeWidth={2} markerEnd="url(#agent-arrow)" />

        {/* the model box: decide next action */}
        <rect x={212} y={58} width={210} height={104} rx={16} className="fill-brand/15 stroke-brand" strokeWidth={2} />
        <text x={317} y={100} textAnchor="middle" className="fill-slate-100 text-[14px] font-semibold">
          Language model
        </text>
        <text x={317} y={121} textAnchor="middle" className="fill-slate-300 text-[12px]">
          decides: answer now, or
        </text>
        <text x={317} y={137} textAnchor="middle" className="fill-slate-300 text-[12px]">
          use a tool first?
        </text>

        <line x1={424} y1={110} x2={480} y2={110} className="stroke-slate-500" strokeWidth={2} markerEnd="url(#agent-arrow)" />

        {/* tool executes */}
        <rect x={484} y={78} width={150} height={64} rx={12} className="fill-slate-950 stroke-amber-500/60" strokeWidth={2} />
        <text x={559} y={106} textAnchor="middle" className="fill-amber-300 text-[12px] font-medium">
          A real tool
        </text>
        <text x={559} y={124} textAnchor="middle" className="fill-amber-300 text-[12px] font-medium">
          actually runs
        </text>
        <text x={559} y={68} textAnchor="middle" className="fill-slate-500 text-[11px] uppercase tracking-wide">
          action
        </text>

        {/* loop back: tool result -> back into the model box */}
        <path
          d="M 559 142 L 559 190 L 317 190 L 317 166"
          fill="none"
          className="stroke-amber-500/70"
          strokeWidth={2}
          strokeDasharray="5 5"
          markerEnd="url(#agent-arrow-amber)"
        />
        <text x={438} y={208} textAnchor="middle" className="fill-amber-300/80 text-[11px]">
          the real result gets added back in -- decide again
        </text>

        {/* final answer, branching off the model box */}
        <line x1={422} y1={90} x2={690} y2={40} className="stroke-emerald-500/60" strokeWidth={2} markerEnd="url(#agent-arrow)" />
        <rect x={640} y={10} width={70} height={44} rx={10} className="fill-slate-950 stroke-emerald-500/60" strokeWidth={2} />
        <text x={675} y={37} textAnchor="middle" className="fill-emerald-300 text-[11px] font-medium">
          final
        </text>
      </svg>

      <p className="mt-2 text-sm text-ink-muted">
        Same language-model box again -- nothing new inside it. What's new is the outer loop wrapped around it: instead of only producing
        words, this loop lets the model's output be "run this real tool," waits for the real result, feeds it back in, and asks the model to
        decide again. It stops the moment it decides it's ready to answer.
      </p>
    </div>
  );
}
