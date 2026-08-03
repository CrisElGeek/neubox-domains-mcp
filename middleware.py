import ipaddress
import logging
import time
from collections import defaultdict
from typing import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from config import Config

logger = logging.getLogger("neubox-mcp")


class IPWhitelistMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, whitelist: list[str], exempt_paths: list[str]):
        super().__init__(app)
        self._networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
        for entry in whitelist:
            try:
                if "/" in entry:
                    self._networks.append(ipaddress.ip_network(entry, strict=False))
                else:
                    net = ipaddress.ip_network(entry, strict=False)
                    self._networks.append(ipaddress.ip_network(f"{entry}/32", strict=False))
            except ValueError:
                logger.warning("IP whitelist: entrada inválida '%s', ignorada", entry)
        self._whitelist_enabled = len(self._networks) > 0
        self._exempt_paths = exempt_paths

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        if request.url.path in self._exempt_paths:
            return await call_next(request)

        if not self._whitelist_enabled:
            return await call_next(request)

        client_ip = request.client.host if request.client else None
        if not client_ip:
            return JSONResponse({"error": "No se pudo determinar la IP del cliente"}, status_code=403)

        try:
            ip = ipaddress.ip_address(client_ip)
        except ValueError:
            return JSONResponse({"error": "IP inválida"}, status_code=403)

        if not any(ip in net for net in self._networks):
            logger.warning("IP rechazada por whitelist: %s", client_ip)
            return JSONResponse({"error": "IP no autorizada"}, status_code=403)

        return await call_next(request)


class APIKeyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, api_key: str, exempt_paths: list[str]):
        super().__init__(app)
        self._api_key = api_key
        self._exempt_paths = exempt_paths

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        if request.url.path in self._exempt_paths:
            return await call_next(request)

        provided_key = request.headers.get("X-API-Key", "")
        if not provided_key or provided_key != self._api_key:
            logger.warning("API Key inválida o ausente desde %s", request.client.host if request.client else "?")
            return JSONResponse({"error": "API Key inválida o ausente"}, status_code=401)

        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int, window_seconds: int):
        super().__init__(app)
        self._max_requests = max_requests
        self._window = window_seconds
        self._buckets: dict[str, list[float]] = defaultdict(list)
        self._last_cleanup = time.monotonic()

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        now = time.monotonic()

        if now - self._last_cleanup > self._window * 2:
            self._buckets = {ip: ts for ip, ts in self._buckets.items() if now - ts[-1] < self._window}
            self._last_cleanup = now

        timestamps = self._buckets[client_ip]
        while timestamps and now - timestamps[0] > self._window:
            timestamps.pop(0)

        if len(timestamps) >= self._max_requests:
            retry_after = int(self._window - (now - timestamps[0])) + 1
            logger.warning("Rate limit excedido para IP %s", client_ip)
            return JSONResponse(
                {"error": "Rate limit excedido"},
                status_code=429,
                headers={"Retry-After": str(max(retry_after, 1))},
            )

        timestamps.append(now)
        return await call_next(request)