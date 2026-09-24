"use client";

export type RagStage = "question" | "retrieval" | "grounding";

const NODES: { id: RagStage; label: string; x: number }[] = [
  { id: "question", label: "Your question", x: 20 },
  { id: "retrieval", label: "Retrieval", x: 300 },
  { id: "grounding", label: "Grounding", x: 580 },
];

const NODE_W = 160;
const NODE_H = 64;
const TOP_Y = 40;

interface Props {
  active: RagStage | null;
  onSelect: (s: RagStage) => void;
}

export function RagMap({ active, onSelect }: Props) {
  return (
    <svg viewBox="0 0 760 140" className="w-full select-none">
      <defs>
        <marker id="rag-map-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L10,5 L0,10 z" className="fill-slate-600" />
        </marker>
      </defs>

      {NODES.slice(0, -1).map((n, i) => {
        const nxt = NODES[i + 1];
        return (
          <line
            key={n.id}
            x1={n.x + NODE_W}
            y1={TOP_Y + NODE_H / 2}
            x2={nxt.x - 6}
            y2={TOP_Y + NODE_H / 2}
            className="stroke-slate-600"
            strokeWidth={2}
            markerEnd="url(#rag-map-arrow)"
          />
        );
      })}

      {NODES.map((n) => {
        const isActive = active === n.id;
        return (
          <g key={n.id} onClick={() => onSelect(n.id)} className="cursor-pointer">
            <rect
              x={n.x}
              y={TOP_Y}
              width={NODE_W}
              height={NODE_H}
              rx={12}
              className={isActive ? "fill-brand stroke-brand" : "fill-slate-900 stroke-slate-700 hover:stroke-slate-500"}
              strokeWidth={2}
            />
            <text
              x={n.x + NODE_W / 2}
              y={TOP_Y + NODE_H / 2 + 5}
              textAnchor="middle"
              className={`text-[14px] font-medium ${isActive ? "fill-white" : "fill-slate-200"}`}
            >
              {n.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
