"""Shared block-schema + validation for interactive lesson content.

Deliberately NOT raw AI-generated SVG/HTML: diagrams are a small, closed
set of *shapes* (tiers / comparison / matrix / cycle) with structured data
that the frontend renders through its own styled components
(frontend/components/lesson-blocks/). This means there's no
dangerouslySetInnerHTML of AI-generated markup anywhere -- no XSS surface,
and every diagram matches the app's own visual design instead of whatever
styling the model happened to produce.

Same reasoning for the calculator block: `formula` is validated here to
contain nothing but variable names, numbers, and +-*/() -- never eval'd or
passed to `new Function()` server- or client-side; the frontend runs it
through a small hand-written arithmetic parser (see
frontend/lib/safeFormula.ts).
"""

import re

DIAGRAM_SHAPES = {"tiers", "comparison", "matrix", "cycle"}
CALLOUT_STYLES = {"insight", "warning"}

# Variable names, numbers (incl. decimals), operators, parens, whitespace --
# nothing else. A formula failing this is rejected before it's ever stored.
_FORMULA_TOKEN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*|[0-9]+(\.[0-9]+)?|[()+\-*/]|\s+$")
_FORMULA_ALLOWED_RE = re.compile(r"^[A-Za-z0-9_+\-*/().\s]+$")

BLOCK_SCHEMA = {
    "type": "object",
    "properties": {
        "blocks": {
            "type": "array",
            "items": {"type": "object"},
            "description": (
                "14-22 content blocks forming the FULL lesson, in reading order -- this needs to read like a "
                "real 20-25 minute course module a professional would pay for, not a summary or a blog post. "
                "If what you're about to write would take an attentive reader under 15 minutes, it's too short "
                "-- go deeper: more real-world scenarios, more nuance, more worked examples, not more filler. "
                "Mix types -- don't make it all 'text'. Every lesson should have: 6-9 'text' blocks (each a "
                "real, substantial section, not a fragment -- build the idea up in stages: motivate it with a "
                "concrete scenario, explain the mechanism, then get into nuance/exceptions/failure modes), "
                "2-3 'diagram' blocks visualizing different aspects of the lesson's structure (not just one -- "
                "e.g. a framework AND a comparison of options within it), 4-6 'check' blocks placed right after "
                "the section each one tests (spread throughout, not bunched at the end), 1-2 'callout' blocks "
                "for the most important takeaways. Add a 'calculator' block if the lesson touches any quantity "
                "someone would want to compute (cost, ROI, time, headcount, risk score).\n\n"
                "The \"type\" field must be EXACTLY one of these five strings -- text, diagram, callout, check, "
                "calculator -- never a synonym like \"paragraph\" or \"section\". Every other field name below "
                "must match exactly too (\"markdown\", not \"text\" or \"content\"; \"choices\", not \"options\"). "
                "Block shapes (every block needs \"type\", plus the fields for that type):\n"
                '  {"type":"text","markdown":"one substantial section of lesson prose, ## header optional, 200-350 words"}\n'
                '  {"type":"diagram","shape":"tiers","title":"...","items":[{"label":"...","description":"..."}, ...2-5 items]}\n'
                '  {"type":"diagram","shape":"comparison","title":"...","columns":["Option A","Option B","Option C"],'
                '"rows":[{"label":"Cost","values":["...","...","..."]}, ...2-5 rows]}\n'
                '  {"type":"diagram","shape":"matrix","title":"...","x_label":"...","y_label":"...",'
                '"quadrants":[{"position":"top-left","label":"...","description":"..."},'
                '{"position":"top-right","label":"...","description":"..."},'
                '{"position":"bottom-left","label":"...","description":"..."},'
                '{"position":"bottom-right","label":"...","description":"..."}]}\n'
                '  {"type":"diagram","shape":"cycle","title":"...","steps":[{"label":"...","description":"..."}, ...3-6 steps]}\n'
                '  {"type":"callout","style":"insight","markdown":"one punchy paragraph -- the single thing to remember"}\n'
                '  {"type":"check","question":"...","choices":["...","...","..."],"correct_index":0,'
                '"explanation":"why that answer is right, shown after the reader answers"}\n'
                '  {"type":"calculator","title":"...","description":"one sentence on what this computes",'
                '"inputs":[{"key":"snake_case_name","label":"Human label","default":100,"min":0,"max":10000,"step":1,"unit":"$"}],'
                '"formula":"an arithmetic expression using the input keys, e.g. (hours * rate) - api_cost",'
                '"output_label":"...","output_format":"currency"}'
            ),
        }
    },
    "required": ["blocks"],
}


# Despite the prompt spelling out the exact vocabulary, the model
# occasionally substitutes a synonym for "type" ("paragraph"/"heading"/"list"
# for "text") or a field name ("options" for "choices", "correctIndex" for
# "correct_index", "diagramType" for "shape"). Normalizing known synonyms
# here is cheap and safe (it only ever maps onto the same closed shape set
# below -- it can't smuggle in a new block kind or field) and salvages
# content instead of silently dropping a whole block over a naming
# mismatch -- confirmed live to matter: a real generation returned
# "heading"/"list"/"diagramType"/"correctIndex" variants that an earlier,
# narrower alias set still dropped.
_TYPE_ALIASES = {
    "paragraph": "text", "section": "text", "p": "text", "body": "text", "heading": "text", "header": "text",
    "list": "text", "bullets": "text", "bullet_list": "text",
    "note": "callout", "tip": "callout", "insight": "callout",
    "quiz": "check", "question": "check", "mcq": "check",
}
_MARKDOWN_ALIASES = ("markdown", "text", "content", "body")
_CHOICES_ALIASES = ("choices", "options", "answers")
_CORRECT_INDEX_ALIASES = ("correct_index", "correctIndex", "correct_idx", "answer_index", "answerIndex")
_SHAPE_ALIASES = ("shape", "diagramType", "diagram_type", "kind")
_DIAGRAM_LIST_FIELDS = {"tiers": "items", "cycle": "steps", "matrix": "quadrants", "comparison": "rows"}


def _first_present(b: dict, keys: tuple[str, ...]):
    for k in keys:
        if k in b:
            return b[k]
    return None


def _coerce_markdown(b: dict) -> str | None:
    alt = _first_present(b, _MARKDOWN_ALIASES)
    if isinstance(alt, str) and alt.strip():
        return alt
    items = b.get("items")
    if isinstance(items, list) and items:
        lines = [f"- {i}" for i in items if isinstance(i, str) and i.strip()]
        if lines:
            return "\n".join(lines)
    heading_text = b.get("text")
    if isinstance(heading_text, str) and heading_text.strip() and "level" in b:
        level = b.get("level") if isinstance(b.get("level"), int) else 2
        return f"{'#' * max(1, min(level, 6))} {heading_text}"
    return None


def validate_and_clean_blocks(raw_blocks: list) -> list[dict]:
    """Drops/repairs anything that doesn't match the closed shape set --
    called right after generation, before a block is ever saved or sent to
    the frontend. Returns only blocks safe to render."""
    if not isinstance(raw_blocks, list):
        return []

    cleaned = []
    for b in raw_blocks:
        if not isinstance(b, dict) or "type" not in b:
            continue
        t = _TYPE_ALIASES.get(b.get("type"), b.get("type"))

        if t in ("text", "callout") and "markdown" not in b:
            alt = _coerce_markdown(b)
            if alt:
                b = {**b, "markdown": alt}
        if t == "check":
            if "choices" not in b:
                alt = _first_present(b, _CHOICES_ALIASES)
                if isinstance(alt, list):
                    b = {**b, "choices": alt}
            if "correct_index" not in b:
                alt = _first_present(b, _CORRECT_INDEX_ALIASES)
                if isinstance(alt, int):
                    b = {**b, "correct_index": alt}
        if t == "diagram" and "shape" not in b:
            alt = _first_present(b, _SHAPE_ALIASES)
            if alt in DIAGRAM_SHAPES:
                b = {**b, "shape": alt}
        if t == "diagram" and b.get("shape") in _DIAGRAM_LIST_FIELDS:
            shape = b["shape"]
            list_field = _DIAGRAM_LIST_FIELDS[shape]
            if list_field not in b:
                # The model sometimes names the array field after the shape
                # itself (e.g. {"diagramType":"tiers","tiers":[...]}) rather
                # than the schema's fixed field name -- try that first since
                # it's the most common real variant, then the other shapes'
                # field names as a generic fallback.
                for candidate in (shape, "items", "steps", "quadrants", "rows", "cells", "stages"):
                    if candidate in b and isinstance(b[candidate], list):
                        b = {**b, list_field: b[candidate]}
                        break

        if t == "text" and isinstance(b.get("markdown"), str) and b["markdown"].strip():
            cleaned.append({"type": "text", "markdown": b["markdown"]})

        elif t == "callout" and isinstance(b.get("markdown"), str) and b["markdown"].strip():
            style = b.get("style") if b.get("style") in CALLOUT_STYLES else "insight"
            cleaned.append({"type": "callout", "style": style, "markdown": b["markdown"]})

        elif t == "check" and isinstance(b.get("choices"), list) and len(b["choices"]) >= 2:
            idx = b.get("correct_index")
            if isinstance(idx, int) and 0 <= idx < len(b["choices"]) and isinstance(b.get("question"), str):
                cleaned.append(
                    {
                        "type": "check",
                        "question": b["question"],
                        "choices": [str(c) for c in b["choices"]],
                        "correct_index": idx,
                        "explanation": str(b.get("explanation", "")),
                    }
                )

        elif t == "diagram" and b.get("shape") in DIAGRAM_SHAPES:
            cleaned_diagram = _clean_diagram(b)
            if cleaned_diagram:
                cleaned.append(cleaned_diagram)

        elif t == "calculator":
            cleaned_calc = _clean_calculator(b)
            if cleaned_calc:
                cleaned.append(cleaned_calc)

        elif t == "image":
            cleaned_image = _clean_image(b)
            if cleaned_image:
                cleaned.append(cleaned_image)

    return cleaned


# Deliberately NOT part of BLOCK_SCHEMA / the AI generation prompt: an LLM
# asked for an "image url" will confidently invent one that doesn't
# resolve, which is exactly the kind of fabrication this app avoids
# everywhere else. Image blocks are added by a separate curation step
# (scripts/add_lesson_image.py) after a real image has actually been
# generated (see app/agents/image_mcp.py) and saved to static/lesson-images/
# -- so the only URLs that can ever pass this check are ones this app
# itself produced and can vouch for.
_ALLOWED_IMAGE_PREFIX = "/static/lesson-images/"


def _clean_image(b: dict) -> dict | None:
    url = b.get("url")
    if not isinstance(url, str) or not url.startswith(_ALLOWED_IMAGE_PREFIX):
        return None
    alt = str(b.get("alt", "")).strip()
    if not alt:
        return None
    return {
        "type": "image",
        "url": url,
        "alt": alt,
        "caption": str(b.get("caption", "")),
        "attribution": str(b.get("attribution", "")),
    }


def _clean_diagram(b: dict) -> dict | None:
    shape = b["shape"]
    title = str(b.get("title", ""))

    if shape == "tiers":
        items = [i for i in b.get("items", []) if isinstance(i, dict) and (i.get("label") or i.get("name"))]
        if not items:
            return None
        return {"type": "diagram", "shape": "tiers", "title": title, "items": [{"label": str(i.get("label") or i["name"]), "description": str(i.get("description", ""))} for i in items]}

    if shape == "comparison":
        columns = [str(c) for c in b.get("columns", []) if c]
        rows = [r for r in b.get("rows", []) if isinstance(r, dict) and r.get("label")]
        if not columns or not rows:
            return None
        return {
            "type": "diagram",
            "shape": "comparison",
            "title": title,
            "columns": columns,
            "rows": [{"label": str(r["label"]), "values": [str(v) for v in r.get("values", [])]} for r in rows],
        }

    if shape == "matrix":
        quadrants = [q for q in b.get("quadrants", []) if isinstance(q, dict) and q.get("position") and q.get("label")]
        if len(quadrants) != 4:
            return None
        return {
            "type": "diagram",
            "shape": "matrix",
            "title": title,
            "x_label": str(b.get("x_label", "")),
            "y_label": str(b.get("y_label", "")),
            "quadrants": [{"position": q["position"], "label": str(q["label"]), "description": str(q.get("description", ""))} for q in quadrants],
        }

    if shape == "cycle":
        steps = [s for s in b.get("steps", []) if isinstance(s, dict) and s.get("label")]
        if not steps:
            return None
        return {"type": "diagram", "shape": "cycle", "title": title, "steps": [{"label": str(s["label"]), "description": str(s.get("description", ""))} for s in steps]}

    return None


def _clean_calculator(b: dict) -> dict | None:
    inputs = b.get("inputs", [])
    formula = str(b.get("formula", ""))
    if not isinstance(inputs, list) or not inputs or not formula:
        return None

    clean_inputs = []
    valid_keys = set()
    for i in inputs:
        if not isinstance(i, dict) or not i.get("key") or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", str(i["key"])):
            continue
        try:
            default, min_v, max_v = float(i.get("default", 0)), float(i.get("min", 0)), float(i.get("max", 100))
        except (TypeError, ValueError):
            continue
        key = str(i["key"])
        valid_keys.add(key)
        clean_inputs.append({"key": key, "label": str(i.get("label", key)), "default": default, "min": min_v, "max": max_v, "step": float(i.get("step", 1)), "unit": str(i.get("unit", ""))})

    if not clean_inputs:
        return None

    # The formula must be pure arithmetic over declared input keys -- reject
    # anything else outright rather than trying to sanitize it.
    if not _FORMULA_ALLOWED_RE.match(formula):
        return None
    referenced = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", formula))
    if not referenced or not referenced.issubset(valid_keys):
        return None

    output_format = b.get("output_format") if b.get("output_format") in {"currency", "number", "percent"} else "number"
    return {
        "type": "calculator",
        "title": str(b.get("title", "")),
        "description": str(b.get("description", "")),
        "inputs": clean_inputs,
        "formula": formula,
        "output_label": str(b.get("output_label", "Result")),
        "output_format": output_format,
    }


def blocks_to_plain_text(blocks: list[dict]) -> str:
    """Flattens blocks into plain-ish markdown -- the content_markdown
    fallback field (TTS reads this, search/export can use it) so nothing
    downstream needs to know how to walk block structures. Deliberately
    uses short placeholders for diagram/check/calculator blocks (e.g.
    "[Diagram: ...]") rather than their full content -- this is a fallback
    for when there's no UI to actually render them, not a substitute
    reading of them. Do NOT reuse this for word-count/time-estimate
    purposes (see estimate_reading_words below) -- it was tried and
    silently undercounted every diagram-heavy lesson, since a whole tiers
    diagram collapsed to a 3-word placeholder instead of the 60-100 words
    of real item labels/descriptions it actually contains."""
    parts = []
    for b in blocks:
        t = b.get("type")
        if t in ("text", "callout"):
            parts.append(b.get("markdown", ""))
        elif t == "diagram":
            parts.append(f"[Diagram: {b.get('title', '')}]")
        elif t == "check":
            parts.append(f"Check your understanding: {b.get('question', '')}")
        elif t == "calculator":
            parts.append(f"[Interactive calculator: {b.get('title', '')}]")
    return "\n\n".join(p for p in parts if p)


def estimate_reading_words(blocks: list[dict]) -> int:
    """Real word count across every block's actual content -- for time
    estimates, not the placeholder-based blocks_to_plain_text above. Walks
    each block type's real fields (diagram item/row/quadrant/step labels
    and descriptions, check questions/choices/explanations, calculator
    labels) rather than a short stand-in string."""
    parts: list[str] = []
    for b in blocks:
        t = b.get("type")
        if t in ("text", "callout"):
            parts.append(str(b.get("markdown", "")))
        elif t == "diagram":
            parts.append(str(b.get("title", "")))
            shape = b.get("shape")
            if shape == "tiers":
                for i in b.get("items", []):
                    parts.append(f"{i.get('label', '')} {i.get('description', '')}")
            elif shape == "comparison":
                parts.extend(str(c) for c in b.get("columns", []))
                for r in b.get("rows", []):
                    parts.append(f"{r.get('label', '')} {' '.join(str(v) for v in r.get('values', []))}")
            elif shape == "matrix":
                parts.append(f"{b.get('x_label', '')} {b.get('y_label', '')}")
                for q in b.get("quadrants", []):
                    parts.append(f"{q.get('label', '')} {q.get('description', '')}")
            elif shape == "cycle":
                for s in b.get("steps", []):
                    parts.append(f"{s.get('label', '')} {s.get('description', '')}")
        elif t == "check":
            parts.append(str(b.get("question", "")))
            parts.extend(str(c) for c in b.get("choices", []))
            parts.append(str(b.get("explanation", "")))
        elif t == "calculator":
            parts.append(f"{b.get('title', '')} {b.get('description', '')}")
            for i in b.get("inputs", []):
                parts.append(str(i.get("label", "")))
    return len(" ".join(parts).split())
