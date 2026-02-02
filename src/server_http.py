#!/usr/bin/env python3
"""
Turbo.az MCP Server (HTTP)
Same server as stdio but over Streamable HTTP for Remote MCP server URL.
Claude requires https: use cert.pem + key.pem in project root for HTTPS.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from starlette.applications import Starlette
from starlette.routing import Route
from starlette.types import Receive, Scope, Send

from .server import server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("turbo-az-mcp")

PORT = 8080
# Project root (parent of src/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_KEY = _PROJECT_ROOT / "key.pem"
_CERT = _PROJECT_ROOT / "cert.pem"
USE_HTTPS = _KEY.exists() and _CERT.exists()


class StreamableHTTPASGIApp:
    """ASGI app that delegates to StreamableHTTPSessionManager."""

    def __init__(self, session_manager: StreamableHTTPSessionManager) -> None:
        """Store session manager.

        Args:
            session_manager: StreamableHTTPSessionManager instance.
        """
        self.session_manager = session_manager

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Handle ASGI request.

        Args:
            scope: ASGI scope.
            receive: ASGI receive callable.
            send: ASGI send callable.
        """
        await self.session_manager.handle_request(scope, receive, send)


def create_app() -> Starlette:
    """Create Starlette app with Streamable HTTP at /mcp.

    Returns:
        Starlette: App with route /mcp for MCP over HTTP.
    """
    session_manager = StreamableHTTPSessionManager(app=server)
    asgi_app = StreamableHTTPASGIApp(session_manager)

    @asynccontextmanager
    async def lifespan(_app: Starlette) -> AsyncIterator[None]:
        async with session_manager.run():
            yield

    return Starlette(
        routes=[
            Route("/mcp", endpoint=asgi_app),
            Route("/mcp/", endpoint=asgi_app),
        ],
        lifespan=lifespan,
    )


async def main() -> None:
    """Run MCP server over HTTP or HTTPS on port 8080. HTTPS if cert.pem + key.pem exist."""
    import uvicorn
    app = create_app()
    kwargs = {"host": "0.0.0.0", "port": PORT, "log_level": "info"}
    if USE_HTTPS:
        kwargs["ssl_keyfile"] = str(_KEY)
        kwargs["ssl_certfile"] = str(_CERT)
    config = uvicorn.Config(app, **kwargs)
    server_uv = uvicorn.Server(config)
    scheme = "https" if USE_HTTPS else "http"
    logger.info("Turbo.az MCP Server: %s://localhost:%s/mcp", scheme, PORT)
    if not USE_HTTPS:
        logger.info("Claude requires https. Add cert.pem and key.pem to project root for HTTPS.")
    await server_uv.serve()


if __name__ == "__main__":
    asyncio.run(main())
