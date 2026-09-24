"use client";

import type { LessonBlock } from "@/lib/types";
import { TextBlockView } from "./TextBlock";
import { CalloutBlockView } from "./CalloutBlock";
import { CheckBlockView } from "./CheckBlock";
import { CalculatorBlockView } from "./CalculatorBlock";
import { DiagramBlockView } from "./DiagramBlock";
import { ImageBlockView } from "./ImageBlock";
import { VideoBlockView } from "./VideoBlock";
import { DocumentBlockView } from "./DocumentBlock";
import { LinkBlockView } from "./LinkBlock";

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
    case "video":
      return <VideoBlockView block={block} />;
    case "document":
      return <DocumentBlockView block={block} />;
    case "link":
      return <LinkBlockView block={block} />;
    default:
      return null;
  }
}
