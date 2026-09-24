export function SandboxExercise({ text }: { text: string }) {
  return (
    <div className="rounded-xl border border-line p-5">
      <div className="text-xs font-medium uppercase tracking-wide text-ink-muted">Try it yourself</div>
      <p className="mt-2 whitespace-pre-line text-sm leading-relaxed text-ink">{text}</p>
    </div>
  );
}
