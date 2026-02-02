#!/usr/bin/env python3
"""
Test MCP server without an LLM: spawns server via stdio and calls tools.
Run from project root: uv run python scripts/test_mcp.py
"""

import sys
from pathlib import Path

import anyio

# Project root
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


async def main() -> None:
    """Spawn server, list tools, call tool, print result."""
    from mcp.client.session import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    # search_cars make model price_min price_max | get_car_details <url_or_id>
    args = sys.argv[1:]
    if len(args) >= 5 and args[0] == "search_cars":
        tool_name = "search_cars"
        tool_args = {
            "make": args[1],
            "model": args[2],
            "price_min": int(args[3]),
            "price_max": int(args[4]),
            "limit": 10,
        }
    elif len(args) >= 2 and args[0] == "get_car_details":
        tool_name = "get_car_details"
        tool_args = {"listing_id": args[1]}
    else:
        tool_name = "get_trending"
        tool_args = {"category": "new", "limit": 2}

    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "src.server"],
        cwd=ROOT,
    )
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, tool_args)
            if result.isError:
                print("Tool error")
            for block in result.content:
                if getattr(block, "type", None) == "text":
                    print(block.text)


if __name__ == "__main__":
    anyio.run(main, backend="trio")
