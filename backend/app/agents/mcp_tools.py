"""MCP (Model Context Protocol) tool definitions wrapping this agent's
capabilities, so an external MCP host (Claude Desktop, another agent
runtime, etc.) can call them directly.

Honest scoping note: the Daily Pulse cron job itself (scripts/run_daily_pulse.py)
calls daily_pulse_agent.py's functions DIRECTLY, in-process -- routing a
same-process scheduled script through an MCP round-trip would add protocol
overhead with no real benefit, since MCP's value is exposing tools *across*
process/agent boundaries. This module is what makes those same tools
reachable from OUTSIDE this process (e.g. a separate curation agent that
wants to trigger pulse generation, or an operator inspecting the pipeline
from an MCP-aware chat client) -- run it standalone with
`python -m app.agents.mcp_tools` to serve it over stdio.

Requires the `mcp` package (`pip install mcp`).
"""

import asyncio
import json

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from app.agents import daily_pulse_agent
from app.agents.news_ingest import fetch_recent_articles
from app.core.db import SessionLocal

server = Server("ai-academy-daily-pulse")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="fetch_ai_news",
            description="Fetch recent AI news articles from the configured RSS feeds, before any LLM processing.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="generate_daily_pulse",
            description="Generate and evaluate a track-tailored Daily Pulse (summary + sandbox exercise + quiz) from recent AI news, and persist it to the database.",
            inputSchema={
                "type": "object",
                "properties": {
                    "track_slug": {"type": "string", "enum": ["leader", "practitioner", "developer"]},
                },
                "required": ["track_slug"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "fetch_ai_news":
        articles = fetch_recent_articles()
        payload = [a.__dict__ for a in articles]
        return [TextContent(type="text", text=json.dumps(payload, indent=2))]

    if name == "generate_daily_pulse":
        db = SessionLocal()
        try:
            pulse = daily_pulse_agent.generate_and_evaluate(db, track_slug=arguments["track_slug"])
            return [TextContent(type="text", text=json.dumps({"id": pulse.id, "status": pulse.status.value, "eval_score": pulse.eval_score}))]
        finally:
            db.close()

    raise ValueError(f"Unknown tool: {name}")


async def _run():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(_run())
