"use client";

import { useMemo, useState } from "react";
import type { CalculatorBlock as CalculatorBlockType } from "@/lib/types";
import { evaluateFormula } from "@/lib/safeFormula";

function formatOutput(value: number, format: CalculatorBlockType["output_format"]): string {
  if (!Number.isFinite(value)) return "--";
  if (format === "currency") return value.toLocaleString(undefined, { style: "currency", currency: "USD", maximumFractionDigits: 2 });
  if (format === "percent") return `${value.toFixed(1)}%`;
  return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

export function CalculatorBlockView({ block }: { block: CalculatorBlockType }) {
  const [values, setValues] = useState<Record<string, number>>(() =>
    Object.fromEntries(block.inputs.map((i) => [i.key, i.default]))
  );

  const result = useMemo(() => {
    try {
      return evaluateFormula(block.formula, values);
    } catch {
      return NaN;
    }
  }, [block.formula, values]);

  return (
    <div className="rounded-lg border border-line bg-white p-4">
      <div className="text-sm font-medium text-ink">{block.title}</div>
      {block.description && <p className="mt-1 text-xs text-ink-muted">{block.description}</p>}

      <div className="mt-3 space-y-3">
        {block.inputs.map((input) => (
          <div key={input.key}>
            <div className="flex items-center justify-between text-xs text-ink-muted">
              <span>{input.label}</span>
              <span className="font-mono text-ink-muted">
                {input.unit === "$" ? "$" : ""}
                {values[input.key]}
                {input.unit && input.unit !== "$" ? ` ${input.unit}` : ""}
              </span>
            </div>
            <input
              type="range"
              min={input.min}
              max={input.max}
              step={input.step}
              value={values[input.key]}
              onChange={(e) => setValues((v) => ({ ...v, [input.key]: Number(e.target.value) }))}
              className="mt-1 w-full accent-brand"
            />
          </div>
        ))}
      </div>

      <div className="mt-4 rounded-lg bg-brand/10 px-3 py-2 text-sm ring-1 ring-brand/30">
        <span className="text-ink-muted">{block.output_label}: </span>
        <span className="font-semibold text-ink">{formatOutput(result, block.output_format)}</span>
      </div>
    </div>
  );
}
