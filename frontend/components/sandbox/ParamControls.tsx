interface Params {
  model: string;
  temperature: number;
  top_p: number;
  max_output_tokens: number;
}

const MODELS = ["claude-haiku-4-5-20251001", "claude-sonnet-4-6", "claude-opus-4-7"];

export function ParamControls({ params, onChange }: { params: Params; onChange: (p: Params) => void }) {
  return (
    <div className="space-y-4 rounded-xl border border-slate-800 p-4">
      <div>
        <label className="text-xs font-medium uppercase tracking-wide text-slate-500">Model</label>
        <select
          value={params.model}
          onChange={(e) => onChange({ ...params, model: e.target.value })}
          className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-sm"
        >
          {MODELS.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className="flex justify-between text-xs font-medium uppercase tracking-wide text-slate-500">
          <span>Temperature</span>
          <span className="text-slate-300">{params.temperature.toFixed(2)}</span>
        </label>
        <input
          type="range"
          min={0}
          max={2}
          step={0.05}
          value={params.temperature}
          onChange={(e) => onChange({ ...params, temperature: Number(e.target.value) })}
          className="mt-1 w-full"
        />
      </div>

      <div>
        <label className="flex justify-between text-xs font-medium uppercase tracking-wide text-slate-500">
          <span>Top-p</span>
          <span className="text-slate-300">{params.top_p.toFixed(2)}</span>
        </label>
        <input
          type="range"
          min={0}
          max={1}
          step={0.01}
          value={params.top_p}
          onChange={(e) => onChange({ ...params, top_p: Number(e.target.value) })}
          className="mt-1 w-full"
        />
      </div>

      <div>
        <label className="flex justify-between text-xs font-medium uppercase tracking-wide text-slate-500">
          <span>Max output tokens</span>
          <span className="text-slate-300">{params.max_output_tokens}</span>
        </label>
        <input
          type="range"
          min={64}
          max={4096}
          step={64}
          value={params.max_output_tokens}
          onChange={(e) => onChange({ ...params, max_output_tokens: Number(e.target.value) })}
          className="mt-1 w-full"
        />
      </div>
    </div>
  );
}
