export function SandboxExercise({ text }: { text: string }) {
  return (
    <div className="rounded-xl border border-slate-800 p-5">
      <div className="text-xs font-medium uppercase tracking-wide text-slate-500">Try it yourself</div>
      <p className="mt-2 whitespace-pre-line text-sm leading-relaxed text-slate-200">{text}</p>
    </div>
  );
}
