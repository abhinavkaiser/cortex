import type { LessonBlock } from "./types";
import type { LessonSection } from "./lessonSections";

export interface CardSlide {
  topicIndex: number;
  topicTitle: string;
  blocks: LessonBlock[];
}

// Splits each topical section into evenly-sized slides so every card in
// the deck holds a comparable amount of content -- a section with one
// short paragraph and a section with three paragraphs plus a diagram and
// a check would otherwise render as wildly different card sizes. Rule:
// at most one 'text' block per slide (a second text block always starts a
// new slide), and no slide holds more than 3 blocks total regardless of
// type -- diagrams/callouts/checks are short enough to ride along with
// the text block they support, but never let two heavy blocks (e.g. two
// diagrams) pile onto the same card.
export function toCardSlides(sections: LessonSection[]): CardSlide[] {
  const slides: CardSlide[] = [];

  sections.forEach((section, topicIndex) => {
    let current: LessonBlock[] = [];
    let hasText = false;
    let addedForTopic = false;

    function flush() {
      if (current.length) {
        slides.push({ topicIndex, topicTitle: section.title, blocks: current });
        addedForTopic = true;
        current = [];
        hasText = false;
      }
    }

    for (const block of section.blocks) {
      const isText = block.type === "text";
      if ((isText && hasText) || current.length >= 3) flush();
      current.push(block);
      if (isText) hasText = true;
    }
    flush();

    if (!addedForTopic) {
      slides.push({ topicIndex, topicTitle: section.title, blocks: [] });
    }
  });

  return slides;
}
