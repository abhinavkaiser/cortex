"use client";

import type { DiagramBlockType } from "@/lib/types";
import { TierLadder } from "./TierLadder";

const QUADRANT_ORDER = ["top-left", "top-right", "bottom-left", "bottom-right"] as const;

export function DiagramBlockView({ block }: { block: DiagramBlockType }) {
  if (block.shape === "tiers") {
    return (
      <div className="rounded-lg border border-line bg-white p-4">
        <TierLadder block={block} />
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-line bg-white p-4">
      {block.title && <div className="mb-3 text-sm font-medium text-ink">{block.title}</div>}

      {block.shape === "comparison" && (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[420px] text-left text-sm">
            <thead>
              <tr className="border-b border-line text-xs uppercase tracking-wide text-ink-muted">
                <th className="py-1.5 pr-3"> </th>
                {block.columns.map((c, i) => (
                  <th key={i} className="py-1.5 pr-3 font-medium text-ink-muted">
                    {c}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {block.rows.map((row, i) => (
                <tr key={i} className="border-b border-line last:border-0">
                  <td className="py-1.5 pr-3 font-medium text-ink-muted">{row.label}</td>
                  {row.values.map((v, j) => (
                    <td key={j} className="py-1.5 pr-3 text-ink-muted">
                      {v}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {block.shape === "matrix" && (
        <div>
          <div className="grid grid-cols-2 gap-1.5">
            {QUADRANT_ORDER.map((pos) => {
              const q = block.quadrants.find((x) => x.position === pos);
              if (!q) return <div key={pos} />;
              return (
                <div key={pos} className="rounded-lg bg-surface p-3">
                  <div className="text-sm font-medium text-ink">{q.label}</div>
                  {q.description && <div className="mt-0.5 text-xs text-ink-muted">{q.description}</div>}
                </div>
              );
            })}
          </div>
          {(block.x_label || block.y_label) && (
            <div className="mt-2 flex justify-between text-xs text-ink-muted">
              <span>{block.y_label}</span>
              <span>{block.x_label}</span>
            </div>
          )}
        </div>
      )}

      {block.shape === "cycle" && (
        <div className="flex flex-wrap items-center gap-2">
          {block.steps.map((step, i) => (
            <div key={i} className="flex items-center gap-2">
              <div className="rounded-lg bg-surface px-3 py-2">
                <div className="text-sm font-medium text-ink">{step.label}</div>
                {step.description && <div className="mt-0.5 text-xs text-ink-muted">{step.description}</div>}
              </div>
              {i < block.steps.length - 1 ? (
                <span className="text-ink-muted">→</span>
              ) : (
                <span className="text-ink-muted" title="loops back to the start">
                  ↺
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
