"use client";

import type { LessonBlock } from "@/lib/types";
import { TextBlockView } from "./TextBlock";
import { CalloutBlockView } from "./CalloutBlock";
import { CheckBlockView } from "./CheckBlock";
import { CalculatorBlockView } from "./CalculatorBlock";
import { DiagramBlockView } from "./DiagramBlock";
import { ImageBlockView } from "./ImageBlock";

export function LessonBlockView({ block }: { block: LessonBlock }) {
  switch (block.type) {
    case "text":
      return <TextBlockView block={block} />;
    case "callout":
      return <CalloutBlockView block={block} />;
    case "check":
      return <CheckBlockView block={block} />;
    case "calculator":
      return <CalculatorBlockView block={block} />;
    case "diagram":
      return <DiagramBlockView block={block} />;
    case "image":
      return <ImageBlockView block={block} />;
    default:
      return null;
  }
}
