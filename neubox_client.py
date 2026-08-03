import base64
import logging
from typing import Any

import httpx

from config import Config

logger = logging.getLogger("neubox-mcp")


class NeuboxClient:
    def __init__(self, config: Config):
        self._config = config
        self._email_b64 = base64.b64encode(config.NEUBOX_USER_EMAIL.encode()).decode()
        self._headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "neubox-api-key": config.NEUBOX_API_KEY,
            "neubox-api-secret": config.NEUBOX_API_SECRET,
            "neubox-user-email": self._email_b64,
            "User-Agent": config.USER_AGENT,
        }

    async def post(self, endpoint: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self._config.NEUBOX_BASE_URL}/{endpoint}"
        payload = body or {}
        if "email" not in payload:
            payload["email"] = self._email_b64

        try:
            async with httpx.AsyncClient(timeout=self._config.NEUBOX_TIMEOUT) as client:
                response = await client.post(url, json=payload, headers=self._headers)
                return response.json()
        except httpx.TimeoutException:
            logger.error("Timeout al contactar la API de NEUBOX (%s)", endpoint)
            return {"result": "error", "error": f"Timeout: la API de NEUBOX no respondió en {self._config.NEUBOX_TIMEOUT}s"}
        except httpx.HTTPError as exc:
            logger.error("Error de red al contactar NEUBOX: %s", exc)
            return {"result": "error", "error": f"Error de conexión con la API de NEUBOX: {exc}"}
        except Exception as exc:
            logger.error("Respuesta no parseable de NEUBOX: %s", exc)
            return {"result": "error", "error": "Respuesta inesperada de la API de NEUBOX"}

    async def get_domains(self) -> dict[str, Any]:
        return await self.post("getdomains")

    async def register_domain(self, domains: list[str], regperiod: list[int]) -> dict[str, Any]:
        return await self.post("registerdomain", {"domains": domains, "regperiod": regperiod})

    async def renew_domain(self, domains: list[str], renewperiod: list[int]) -> dict[str, Any]:
        return await self.post("renewdomain", {"domains": domains, "renewperiod": renewperiod})

    async def search_domains(self, domain: str, tlds: list[str]) -> dict[str, Any]:
        return await self.post("searchdomains", {"domain": domain, "tlds": tlds})