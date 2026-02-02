#!/usr/bin/env python3
"""
Turbo.az MCP Server
MCP server for car search and fetching information.
Uses Selenium because turbo.az blocks external access.
"""

import asyncio
import base64
import io
import json
import logging
from typing import Any
import aiohttp
from PIL import Image
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ImageContent

from .scraper import TurboAzScraper

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("turbo-az-mcp")

# Create MCP Server
server = Server("turbo-az-mcp")

# Scraper instance
scraper = TurboAzScraper()


async def fetch_image_as_base64(url: str, max_width: int = 800, quality: int = 70) -> tuple[str, str] | None:
    """
    Fetches an image from URL, resizes and compresses it, returns (base64_data, mime_type).
    Returns None if fetch fails.

    Args:
        url: Image URL to fetch
        max_width: Maximum width in pixels (default: 800)
        quality: JPEG quality 1-100 (default: 70)
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    image_bytes = await response.read()

                    # Open image with PIL
                    img = Image.open(io.BytesIO(image_bytes))

                    # Convert RGBA to RGB if necessary (for JPEG compatibility)
                    if img.mode in ('RGBA', 'LA', 'P'):
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                        img = background

                    # Resize if image is larger than max_width
                    if img.width > max_width:
                        ratio = max_width / img.width
                        new_height = int(img.height * ratio)
                        img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

                    # Compress and save to bytes
                    output = io.BytesIO()
                    img.save(output, format='JPEG', quality=quality, optimize=True)
                    compressed_bytes = output.getvalue()

                    # Encode to base64
                    base64_data = base64.b64encode(compressed_bytes).decode('utf-8')

                    return base64_data, 'image/jpeg'
                else:
                    logger.warning(f"Failed to fetch image {url}: HTTP {response.status}")
                    return None
    except Exception as e:
        logger.warning(f"Error fetching image {url}: {e}")
        return None


@server.list_tools()
async def list_tools() -> list[Tool]:
    """Lists MCP tools."""
    return [
        Tool(
            name="search_cars",
            description="Car search on Turbo.az. Search by make, model, price range, year, etc.",
            inputSchema={
                "type": "object",
                "properties": {
                    "make": {
                        "type": "string",
                        "description": "Car make (e.g. BMW, Mercedes, Toyota)"
                    },
                    "model": {
                        "type": "string",
                        "description": "Car model (e.g. X5, E-Class, Camry)"
                    },
                    "price_min": {
                        "type": "integer",
                        "description": "Minimum price (AZN)"
                    },
                    "price_max": {
                        "type": "integer",
                        "description": "Maximum price (AZN)"
                    },
                    "year_min": {
                        "type": "integer",
                        "description": "Minimum year of manufacture"
                    },
                    "year_max": {
                        "type": "integer",
                        "description": "Maximum year of manufacture"
                    },
                    "fuel_type": {
                        "type": "string",
                        "description": "Fuel type: petrol, diesel, gas, electric, hybrid"
                    },
                    "transmission": {
                        "type": "string",
                        "description": "Transmission: automatic, manual"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Result count limit (default: 20)",
                        "default": 20
                    }
                }
            }
        ),
        Tool(
            name="get_car_details",
            description="Fetches detailed listing info from Turbo.az. Requires listing ID or URL.",
            inputSchema={
                "type": "object",
                "properties": {
                    "listing_id": {
                        "type": "string",
                        "description": "Listing ID (e.g. 1234567) or full URL"
                    }
                },
                "required": ["listing_id"]
            }
        ),
        Tool(
            name="get_makes_models",
            description="Fetches list of available makes and models on Turbo.az.",
            inputSchema={
                "type": "object",
                "properties": {
                    "make": {
                        "type": "string",
                        "description": "Make name (to see its models). Leave empty for all makes."
                    }
                }
            }
        ),
        Tool(
            name="get_trending",
            description="Fetches most popular/new listings on Turbo.az.",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Category: new, popular, vip",
                        "default": "new"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Result count (default: 20)",
                        "default": 20
                    }
                }
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Executes tool calls."""
    logger.info(f"Tool called: {name} with args: {arguments}")
    
    try:
        if name == "search_cars":
            results = await scraper.search_cars(
                make=arguments.get("make"),
                model=arguments.get("model"),
                price_min=arguments.get("price_min"),
                price_max=arguments.get("price_max"),
                year_min=arguments.get("year_min"),
                year_max=arguments.get("year_max"),
                fuel_type=arguments.get("fuel_type"),
                transmission=arguments.get("transmission"),
                limit=arguments.get("limit", 20)
            )

            # Return only text results (no images to avoid confusion about which image belongs to which car)
            return [TextContent(type="text", text=json.dumps(results, ensure_ascii=False, indent=2))]
        
        elif name == "get_car_details":
            listing_id = arguments.get("listing_id")
            if not listing_id:
                return [TextContent(type="text", text="Error: listing_id is required")]

            details = await scraper.get_car_details(listing_id)

            # Fetch images and include them as ImageContent
            content_list = [TextContent(type="text", text=json.dumps(details, ensure_ascii=False, indent=2))]

            if details.get("success") and details.get("details", {}).get("images"):
                image_urls = details["details"]["images"]
                # Fetch up to 10 compressed images (quality=50 for smaller size)
                for img_url in image_urls[:10]:
                    img_data = await fetch_image_as_base64(img_url, quality=50)
                    if img_data:
                        base64_data, mime_type = img_data
                        content_list.append(
                            ImageContent(
                                type="image",
                                data=base64_data,
                                mimeType=mime_type
                            )
                        )

            return content_list
        
        elif name == "get_makes_models":
            make = arguments.get("make")
            results = await scraper.get_makes_models(make)
            return [TextContent(type="text", text=json.dumps(results, ensure_ascii=False, indent=2))]
        
        elif name == "get_trending":
            category = arguments.get("category", "new")
            limit = arguments.get("limit", 20)
            results = await scraper.get_trending(category, limit)
            return [TextContent(type="text", text=json.dumps(results, ensure_ascii=False, indent=2))]
        
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    
    except Exception as e:
        logger.error(f"Tool error: {e}")
        return [TextContent(type="text", text=f"An error occurred: {str(e)}")]


async def main():
    """Starts the MCP server."""
    logger.info("Turbo.az MCP Server starting...")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
