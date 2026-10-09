"""Shared schema + validation for AI-generated flashcard decks.

Same philosophy as lesson_blocks.py: the model's output is never trusted
into the database as-is. A card is a closed two-field shape of plain text
(never HTML -- the frontend renders it as text, so there is no markup
surface to sanitize in the first place), and anything that doesn't match
is repaired where that's unambiguous or dropped where it isn't. A deck
that comes back half-malformed still yields its good cards rather than
failing the whole generation.
"""

MIN_CARDS = 8
MAX_CARDS = 20
MAX_FRONT_CHARS = 200
MAX_BACK_CHARS = 600

FLASHCARD_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {
            "type": "string",
            "description": "Short deck title, e.g. 'Key terms: Build vs. Buy vs. Partner'",
        },
        "cards": {
            "type": "array",
            "items": {"type": "object"},
            "description": (
                f"{MIN_CARDS}-15 flashcards covering this chapter's key terms, concepts and "
                "distinctions, in the order a learner would want to review them.\n\n"
                'Every card is exactly {"front": "...", "back": "..."} -- those two field '
                'names exactly, both plain text, no markdown, no HTML.\n\n'
                "front: a term, question or prompt. Short -- a few words to one sentence. "
                "It must be answerable on its own: 'What does RAG stand for and why use it?' "
                "not 'What is it?'.\n"
                "back: the answer. 1-3 sentences. Specific and self-contained -- a learner "
                "reading only this card should get a correct, useful answer, not a pointer "
                "back to the lesson.\n\n"
                "Cover what the chapter actually taught: real definitions, the distinctions "
                "it drew, the numbers or thresholds it gave, the failure modes it warned "
                "about. Do NOT write trivia, do NOT ask about the structure of the course "
                "itself, and do NOT invent material the chapter never covered."
            ),
        },
    },
    "required": ["title", "cards"],
}

# The model occasionally renames the two fields; these are the variants seen
# in practice for this kind of prompt. Mapping them is safe -- they can only
# ever resolve onto the same closed {front, back} shape below.
_FRONT_ALIASES = ("front", "question", "term", "prompt", "q")
_BACK_ALIASES = ("back", "answer", "definition", "response", "a")


def _first_str(card: dict, keys: tuple[str, ...]) -> str:
    for k in keys:
        v = card.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def validate_and_clean_cards(raw_cards) -> list[dict]:
    """Returns only cards safe to store and render. Drops duplicates by
    front text -- a deck that asks the same thing twice is a worse study
    aid, and repeated fronts were a real failure mode in generation."""
    if not isinstance(raw_cards, list):
        return []

    cleaned: list[dict] = []
    seen_fronts: set[str] = set()

    for card in raw_cards:
        if not isinstance(card, dict):
            continue
        front = _first_str(card, _FRONT_ALIASES)
        back = _first_str(card, _BACK_ALIASES)
        if not front or not back:
            continue

        key = front.lower().rstrip("?. ")
        if key in seen_fronts:
            continue
        seen_fronts.add(key)

        cleaned.append({
            "front": front[:MAX_FRONT_CHARS],
            "back": back[:MAX_BACK_CHARS],
        })
        if len(cleaned) >= MAX_CARDS:
            break

    return cleaned
