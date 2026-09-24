"use client";

interface Props {
  visible: boolean;
  side: "left" | "right";
  onBack: () => void;
  children: React.ReactNode;
}

export function SlidePanel({ visible, side, onBack, children }: Props) {
  return (
    <div
      className={[
        "fixed top-20 bottom-6 z-40 w-[380px] max-w-[88vw] overflow-y-auto rounded-xl border border-line bg-white/95 p-5 shadow-2xl backdrop-blur",
        "transition-all duration-300 ease-out",
        side === "right" ? "right-6" : "left-6",
        visible
          ? "translate-x-0 opacity-100"
          : side === "right"
            ? "translate-x-[120%] opacity-0 pointer-events-none"
            : "-translate-x-[120%] opacity-0 pointer-events-none",
      ].join(" ")}
    >
      <button onClick={onBack} className="text-xs font-medium text-ink-muted hover:text-ink">
        ← Back
      </button>
      {children}
    </div>
  );
}
