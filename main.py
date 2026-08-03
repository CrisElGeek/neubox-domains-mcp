import contextlib
import logging
import signal
import sys

import uvicorn
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from config import Config
from middleware import APIKeyMiddleware, IPWhitelistMiddleware, RateLimitMiddleware
from neubox_client import NeuboxClient
from tools import register_tools

logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("neubox-mcp")

EXEMPT_PATHS = ["/health"]

client = NeuboxClient(Config)

from mcp.server import MCPServer

mcp = MCPServer("neubox-mcp")

register_tools(mcp, client)


async def health(request):
    return JSONResponse({"status": "ok", "service": "neubox-mcp", "version": "1.0"})


@contextlib.asynccontextmanager
async def lifespan(app):
    async with mcp.session_manager.run():
        logger.info("Servidor MCP iniciado en puerto %s", Config.MCP_PORT)
        yield
        logger.info("Cerrando servidor MCP...")


mcp_app = mcp.streamable_http_app(json_response=True)

app = Starlette(
    routes=[
        Route("/health", health, methods=["GET"]),
        Mount("/mcp", app=mcp_app),
    ],
    lifespan=lifespan,
)

app.add_middleware(RateLimitMiddleware, max_requests=Config.RATE_LIMIT_REQUESTS, window_seconds=Config.RATE_LIMIT_WINDOW)
app.add_middleware(APIKeyMiddleware, api_key=Config.MCP_API_KEY, exempt_paths=EXEMPT_PATHS)
app.add_middleware(IPWhitelistMiddleware, whitelist=Config.IP_WHITELIST, exempt_paths=EXEMPT_PATHS)


def graceful_shutdown(signum, frame):
    logger.info("Señal recibida (%s), cerrando servidor...", signum)
    sys.exit(0)


signal.signal(signal.SIGINT, graceful_shutdown)
signal.signal(signal.SIGTERM, graceful_shutdown)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=Config.MCP_PORT, log_level=Config.LOG_LEVEL.lower())