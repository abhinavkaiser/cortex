"""MCP server exposing real image generation as a tool -- the one piece of
this app that genuinely can't run on the local Claude subscription (Claude
has no image-generation endpoint), so it's the one deliberate exception to
this app's "no metered API keys" design. Keys live only in backend/.env
(openai_api_key / gemini_api_key in app/core/config.py), never in this
file or in any committed config.

DALL-E-3-first-then-Gemini-fallback, verified as a real working pattern in
xiot's imageGenService.js (a sibling project on this machine) rather than
invented fresh -- Gemini 2.5 Flash Image's free tier means this tool still
works with zero OpenAI billing if only a Gemini key is configured. Note
what this is NOT: the `codex` CLI (ChatGPT-subscription-authenticated,
used for text elsewhere in that same sibling project) has no image
generation capability -- confirmed by reading its actual usage, not
assumed. Both DALL-E and Gemini here are real, separate, billed/metered
APIs requiring their own API keys.

Mirrors the existing MCP pattern in app/agents/mcp_tools.py (same `mcp`
SDK, same stdio-server shape) rather than inventing a new one. Run
standalone with `python -m app.agents.image_mcp`, or let Claude Code launch
it per the project's .mcp.json.

Generated images are saved to backend/static/lesson-images/ (served by
FastAPI's StaticFiles mount in main.py) and referenced from lesson content
by that stable local path -- not by hotlinking a provider's own temporary
image URLs, which expire.
"""

import asyncio
import base64
import re
import sys
from pathlib import Path

# Self-contained regardless of the invoking MCP client's working directory
# (an .mcp.json "cwd" isn't universally honored) -- mirrors the same
# sys.path fix-up every script/ entry point in this backend already uses.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from app.core.config import get_settings

settings = get_settings()

STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "static" / "lesson-images"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

_SLUG_RE = re.compile(r"[^a-z0-9-]+")

server = Server("cortex-ai-images")


def _slugify(name: str) -> str:
    slug = _SLUG_RE.sub("-", name.lower()).strip("-")
    return slug or "image"


def _unique_path(filename: str) -> Path:
    # Avoid clobbering a differently-prompted image saved under the same
    # short name -- append a numeric suffix rather than silently overwrite.
    path = STATIC_DIR / f"{filename}.png"
    n = 2
    while path.exists():
        path = STATIC_DIR / f"{filename}-{n}.png"
        n += 1
    return path


async def _generate_with_dalle(client: httpx.AsyncClient, prompt: str, size: str, quality: str) -> tuple[bytes, str]:
    if not settings.openai_api_key:
        raise RuntimeError("openai_api_key not configured")
    resp = await client.post(
        "https://api.openai.com/v1/images/generations",
        headers={"Authorization": f"Bearer {settings.openai_api_key}"},
        json={"model": "dall-e-3", "prompt": prompt, "size": size, "quality": quality, "n": 1, "response_format": "b64_json"},
    )
    if resp.status_code != 200:
        raise RuntimeError(f"DALL-E API returned {resp.status_code}: {resp.text[:300]}")
    data = resp.json()["data"][0]
    return base64.b64decode(data["b64_json"]), data.get("revised_prompt", prompt)


async def _generate_with_gemini(client: httpx.AsyncClient, prompt: str) -> tuple[bytes, str]:
    if not settings.gemini_api_key:
        raise RuntimeError("gemini_api_key not configured")
    resp = await client.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent?key={settings.gemini_api_key}",
        json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]}},
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Gemini API returned {resp.status_code}: {resp.text[:300]}")
    parts = resp.json().get("candidates", [{}])[0].get("content", {}).get("parts", [])
    image_part = next((p for p in parts if p.get("inlineData", {}).get("data")), None)
    if not image_part:
        raise RuntimeError("Gemini returned no image data")
    return base64.b64decode(image_part["inlineData"]["data"]), prompt


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="generate_lesson_image",
            description=(
                "Generates a real image (DALL-E 3, falling back to Gemini 2.5 Flash Image if DALL-E fails or "
                "isn't configured) and saves it to this app's static/lesson-images directory, returning the "
                "local URL path to reference in a lesson's content_blocks (as an 'image' block -- see "
                "app/agents/lesson_blocks.py). Use a descriptive, concrete prompt -- this is a real generation, "
                "not a placeholder."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "What to generate, described concretely."},
                    "filename": {
                        "type": "string",
                        "description": "A short, descriptive name for this image (e.g. 'ai-taxonomy-tiers') -- gets slugified into the saved filename.",
                    },
                    "size": {
                        "type": "string",
                        "enum": ["1024x1024", "1024x1792", "1792x1024"],
                        "description": "Defaults to 1024x1024.",
                    },
                    "quality": {"type": "string", "enum": ["standard", "hd"], "description": "Defaults to standard."},
                },
                "required": ["prompt", "filename"],
            },
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name != "generate_lesson_image":
        raise ValueError(f"Unknown tool: {name}")

    if not settings.openai_api_key and not settings.gemini_api_key:
        return [TextContent(type="text", text="ERROR: neither openai_api_key nor gemini_api_key is set in backend/.env")]

    prompt = arguments["prompt"]
    filename = _slugify(arguments["filename"])
    size = arguments.get("size", "1024x1024")
    quality = arguments.get("quality", "standard")

    errors = []
    image_bytes: bytes | None = None
    used_prompt = prompt
    source = ""

    async with httpx.AsyncClient(timeout=120) as client:
        if settings.openai_api_key:
            try:
                image_bytes, used_prompt = await _generate_with_dalle(client, prompt, size, quality)
                source = "DALL-E 3"
            except Exception as err:  # noqa: BLE001 -- fall through to Gemini, same as xiot's imageGenService.js
                errors.append(f"DALL-E: {err}")

        if image_bytes is None and settings.gemini_api_key:
            try:
                image_bytes, used_prompt = await _generate_with_gemini(client, prompt)
                source = "Gemini 2.5 Flash Image"
            except Exception as err:  # noqa: BLE001
                errors.append(f"Gemini: {err}")

    if image_bytes is None:
        return [TextContent(type="text", text="ERROR: all providers failed.\n" + "\n".join(errors))]

    path = _unique_path(filename)
    path.write_bytes(image_bytes)

    url_path = f"/static/lesson-images/{path.name}"
    note = f" (after DALL-E failed: {errors[0]})" if errors else ""
    return [TextContent(type="text", text=f"Saved to {url_path} via {source}{note}\nPrompt actually used: {used_prompt}")]


async def _run():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(_run())
