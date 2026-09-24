import { PromptPlayground } from "@/components/sandbox/PromptPlayground";

export default function SandboxPage() {
  return (
    <main className="mx-auto max-w-4xl px-6 py-12">
      <h1 className="text-2xl font-semibold">Prompt Playground</h1>
      <p className="mt-1 text-sm text-ink-muted">Try a prompt, tune the parameters, see the real token cost.</p>
      <div className="mt-6">
        <PromptPlayground />
      </div>
    </main>
  );
}
