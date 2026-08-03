import os
import sys
from typing import List


def get_required_env(key: str) -> str:
    value = os.getenv(key)
    if not value:
        print(f"ERROR: Variable de entorno requerida '{key}' no está definida", file=sys.stderr)
        sys.exit(1)
    return value


def get_optional_env(key: str, default: str = "") -> str:
    return os.getenv(key, default)


class Config:
    NEUBOX_API_KEY: str = get_required_env("NEUBOX_API_KEY")
    NEUBOX_API_SECRET: str = get_required_env("NEUBOX_API_SECRET")
    NEUBOX_USER_EMAIL: str = get_required_env("NEUBOX_USER_EMAIL")
    MCP_API_KEY: str = get_required_env("MCP_API_KEY")

    IP_WHITELIST_RAW: str = get_optional_env("IP_WHITELIST", "")
    IP_WHITELIST: List[str] = [ip.strip() for ip in IP_WHITELIST_RAW.split(",") if ip.strip()]

    RATE_LIMIT_REQUESTS: int = int(get_optional_env("RATE_LIMIT_REQUESTS", "60"))
    RATE_LIMIT_WINDOW: int = int(get_optional_env("RATE_LIMIT_WINDOW", "60"))

    MCP_PORT: int = int(get_optional_env("MCP_PORT", "8000"))
    LOG_LEVEL: str = get_optional_env("LOG_LEVEL", "INFO")

    NEUBOX_BASE_URL: str = "https://api.neubox.com"
    NEUBOX_TIMEOUT: float = 15.0
    USER_AGENT: str = "neubox-mcp-py/1.0"