"use client";

export type Stage = "input" | "tokens" | "embeddings" | "attention" | "prediction" | "loop";

const NODES: { id: Stage; label: string; x: number }[] = [
  { id: "input", label: "Your text", x: 20 },
  { id: "tokens", label: "Tokens", x: 200 },
  { id: "embeddings", label: "Embeddings", x: 380 },
  { id: "attention", label: "Attention", x: 560 },
  { id: "prediction", label: "Prediction", x: 740 },
];

const NODE_W = 140;
const NODE_H = 64;
const TOP_Y = 40;
const BOTTOM_Y = 280;

interface Props {
  active: Stage | null;
  onSelect: (s: Stage) => void;
}

export function PipelineMap({ active, onSelect }: Props) {
  const first = NODES[0];
  const last = NODES[NODES.length - 1];

  return (
    <svg viewBox="0 0 920 340" className="w-full select-none">
      <defs>
        <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L10,5 L0,10 z" className="fill-slate-600" />
        </marker>
        <marker id="arrow-active" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L10,5 L0,10 z" className="fill-amber-400" />
        </marker>
      </defs>

      {/* top-row connectors, left to right */}
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
            markerEnd="url(#arrow)"
          />
        );
      })}

      {/* return loop: prediction -> down -> right-to-left along the bottom -> up into input */}
      <g
        onClick={() => onSelect("loop")}
        onMouseEnter={() => {}}
        className="cursor-pointer"
      >
        <path
          d={`M ${last.x + NODE_W / 2} ${TOP_Y + NODE_H}
              L ${last.x + NODE_W / 2} ${BOTTOM_Y}
              L ${first.x + NODE_W / 2} ${BOTTOM_Y}
              L ${first.x + NODE_W / 2} ${TOP_Y + NODE_H + 6}`}
          fill="none"
          className={active === "loop" ? "stroke-amber-400" : "stroke-slate-600"}
          strokeWidth={2}
          strokeDasharray="6 5"
          markerEnd={active === "loop" ? "url(#arrow-active)" : "url(#arrow)"}
        />
        <rect
          x={first.x + (last.x - first.x) / 2 - 150}
          y={BOTTOM_Y - 16}
          width={300}
          height={32}
          fill="transparent"
        />
        <text
          x={first.x + (last.x - first.x) / 2}
          y={BOTTOM_Y - 12}
          textAnchor="middle"
          className={`text-[13px] ${active === "loop" ? "fill-amber-300" : "fill-slate-500"}`}
        >
          predicted token appended to context -- run it again
        </text>
      </g>

      {/* nodes */}
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
