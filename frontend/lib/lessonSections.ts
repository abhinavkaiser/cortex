import type { LessonBlock } from "./types";

export interface LessonSection {
  title: string;
  blocks: LessonBlock[];
}

const HEADING_RE = /^#{1,3}\s+(.+)/m;

// A short, single-line, non-sentence text block reads as a section title
// even without markdown "#" syntax -- and in practice most generated
// lessons DO write titles this way ("Where the Taxonomy Meets Risk") rather
// than with a literal "##" prefix, despite the generation prompt allowing
// either. Relying on "#" alone collapsed nearly every real lesson into one
// giant "Introduction" section; this heuristic is what actually matches
// the content that gets generated.
function looksLikeTitle(markdown: string): boolean {
  const trimmed = markdown.trim();
  if (trimmed.includes("\n") || trimmed.length === 0 || trimmed.length > 80) return false;
  return !/[.!?]['"]?\s*$/.test(trimmed);
}

// Groups a lesson's flat content_blocks into sections for the map view --
// entirely derived from the content itself, no per-lesson authoring. A
// heading (markdown "#" or a short title-like line) starts a new section;
// everything else attaches to the section already in progress.
export function segmentBlocks(blocks: LessonBlock[]): LessonSection[] {
  const sections: LessonSection[] = [];

  for (const block of blocks) {
    let title: string | null = null;
    let titleOnly = false; // the whole block IS the title, nothing else to render

    if (block.type === "text") {
      const heading = block.markdown.match(HEADING_RE);
      if (heading) {
        title = heading[1].trim();
        titleOnly = block.markdown.trim() === heading[0].trim();
      } else if (looksLikeTitle(block.markdown)) {
        title = block.markdown.trim();
        titleOnly = true;
      }
    }

    if (title !== null) {
      sections.push({ title, blocks: titleOnly ? [] : [block] });
    } else if (sections.length === 0) {
      sections.push({ title: "Introduction", blocks: [block] });
    } else {
      sections[sections.length - 1].blocks.push(block);
    }
  }

  return sections;
}
