"use client";

import { useState } from "react";

export interface SlidePanelState<T> {
  stage: T | null;
  side: "left" | "right";
  visible: boolean;
}

export const SLIDE_PANEL_SWAP_MS = 260;

// Shared by every "click a diagram node -> detail slides in, alternating
// sides, with a Back button" explainer page under /dashboard/explore.
export function useSlidePanel<T>() {
  const [panel, setPanel] = useState<SlidePanelState<T>>({ stage: null, side: "right", visible: false });

  function open(stage: T) {
    setPanel((p) => {
      if (p.visible && p.stage === stage) return p; // already showing this one
      if (p.visible) {
        // slide the current panel out, then bring the new one in from the opposite edge
        setTimeout(() => setPanel({ stage, side: p.side === "right" ? "left" : "right", visible: true }), SLIDE_PANEL_SWAP_MS);
        return { ...p, visible: false };
      }
      return { stage, side: p.side === "right" ? "left" : "right", visible: true };
    });
  }

  function close() {
    setPanel((p) => ({ ...p, visible: false }));
  }

  return { panel, open, close };
}
