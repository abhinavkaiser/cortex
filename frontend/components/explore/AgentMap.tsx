"use client";

export type AgentStage = "goal" | "decide" | "tools" | "loop";

const NODES: { id: AgentStage; label: string; x: number }[] = [
  { id: "goal", label: "Goal", x: 20 },
  { id: "decide", label: "Decide", x: 240 },
  { id: "tools", label: "Real tools", x: 460 },
];

const NODE_W = 160;
const NODE_H = 64;
const TOP_Y = 40;
const BOTTOM_Y = 200;

interface Props {
  active: AgentStage | null;
  onSelect: (s: AgentStage) => void;
}

export function AgentMap({ active, onSelect }: Props) {
  const decide = NODES[1];
  const tools = NODES[2];

  return (
    <svg viewBox="0 0 680 260" className="w-full select-none">
      <defs>
        <marker id="agent-map-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L10,5 L0,10 z" className="fill-slate-600" />
        </marker>
        <marker id="agent-map-arrow-active" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L10,5 L0,10 z" className="fill-amber-400" />
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
            markerEnd="url(#agent-map-arrow)"
          />
        );
      })}

      {/* the loop: tools -> down -> back left -> up into decide */}
      <g onClick={() => onSelect("loop")} className="cursor-pointer">
        <path
          d={`M ${tools.x + NODE_W / 2} ${TOP_Y + NODE_H}
              L ${tools.x + NODE_W / 2} ${BOTTOM_Y}
              L ${decide.x + NODE_W / 2} ${BOTTOM_Y}
              L ${decide.x + NODE_W / 2} ${TOP_Y + NODE_H + 6}`}
          fill="none"
          className={active === "loop" ? "stroke-amber-400" : "stroke-slate-600"}
          strokeWidth={2}
          strokeDasharray="6 5"
          markerEnd={active === "loop" ? "url(#agent-map-arrow-active)" : "url(#agent-map-arrow)"}
        />
        <rect x={decide.x + (tools.x - decide.x) / 2 - 100} y={BOTTOM_Y - 16} width={220} height={32} fill="transparent" />
        <text x={decide.x + (tools.x - decide.x) / 2 + NODE_W / 2} y={BOTTOM_Y - 12} textAnchor="middle" className={`text-[13px] ${active === "loop" ? "fill-amber-300" : "fill-slate-500"}`}>
          result comes back -- decide again
        </text>
      </g>

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
