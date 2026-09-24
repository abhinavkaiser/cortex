// Parses a video block's url (see lib/types.ts's VideoBlock) into an
// embeddable <iframe> src for the providers we know how to embed --
// YouTube and Vimeo. Everything else (a direct .mp4/.webm URL, or any
// other host) isn't a known provider, so VideoBlockView falls back to a
// native <video> tag instead of guessing at an embed format.

export interface EmbedInfo {
  provider: "youtube" | "vimeo";
  embedUrl: string;
}

export function parseVideoEmbed(url: string): EmbedInfo | null {
  const trimmed = url.trim();

  // youtu.be/<id>, youtube.com/watch?v=<id>, youtube.com/embed/<id>, or a
  // bare 11-char video id typed directly into the authoring form.
  const youtubeMatch =
    trimmed.match(/youtu\.be\/([a-zA-Z0-9_-]{6,})/) ||
    trimmed.match(/youtube\.com\/watch\?.*v=([a-zA-Z0-9_-]{6,})/) ||
    trimmed.match(/youtube\.com\/embed\/([a-zA-Z0-9_-]{6,})/) ||
    (/^[a-zA-Z0-9_-]{11}$/.test(trimmed) ? [null, trimmed] : null);
  if (youtubeMatch) {
    return { provider: "youtube", embedUrl: `https://www.youtube.com/embed/${youtubeMatch[1]}` };
  }

  // vimeo.com/<id>, player.vimeo.com/video/<id>, or a bare numeric id.
  const vimeoMatch =
    trimmed.match(/vimeo\.com\/(?:video\/)?(\d+)/) || (/^\d+$/.test(trimmed) ? [null, trimmed] : null);
  if (vimeoMatch) {
    return { provider: "vimeo", embedUrl: `https://player.vimeo.com/video/${vimeoMatch[1]}` };
  }

  return null;
}
