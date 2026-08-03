import json
import logging
from typing import Any

from pydantic import BaseModel, Field, field_validator

from neubox_client import NeuboxClient

logger = logging.getLogger("neubox-mcp")


class ListDomainsInput(BaseModel):
    pass


class RegisterDomainInput(BaseModel):
    domains: list[str] = Field(description="Lista de dominios a registrar. Ej: ['example.com', 'example.mx']")
    regperiod: list[int] = Field(description="Períodos de registro en años, mismo orden que domains. Ej: [1, 2]")

    @field_validator("regperiod")
    @classmethod
    def validate_regperiod(cls, v):
        if any(p <= 0 for p in v):
            raise ValueError("Cada período de registro debe ser un entero positivo mayor a 0")
        return v


class RenewDomainInput(BaseModel):
    domains: list[str] = Field(description="Lista de dominios a renovar. Ej: ['example.com', 'example.mx']")
    renewperiod: list[int] = Field(description="Períodos de renovación en años, mismo orden que domains. Ej: [1, 2]")

    @field_validator("renewperiod")
    @classmethod
    def validate_renewperiod(cls, v):
        if any(p <= 0 for p in v):
            raise ValueError("Cada período de renovación debe ser un entero positivo mayor a 0")
        return v


class SearchDomainsInput(BaseModel):
    domain: str = Field(description="Nombre de dominio a buscar, con o sin TLD. Ej: 'midominio.com' o 'midominio'")
    tlds: list[str] = Field(description="Lista de TLDs a consultar. Ej: ['com', 'mx', 'net']")

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v):
        if not v or not v.strip():
            raise ValueError("El dominio no puede estar vacío")
        return v.strip()

    @field_validator("tlds")
    @classmethod
    def validate_tlds(cls, v):
        if not v or len(v) < 1:
            raise ValueError("Debe especificar al menos un TLD")
        return v


def _format_result(result: dict[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=False, indent=2)


def register_tools(mcp, client: NeuboxClient):

    @mcp.tool()
    async def list_domains() -> str:
        """Obtiene el listado completo de dominios registrados en la cuenta NEUBOX.
        No requiere parámetros. Retorna un JSON con cada dominio, su fecha de registro,
        monto recurrente, fecha de vencimiento y estado.
        """
        result = await client.get_domains()
        return _format_result(result)

    @mcp.tool()
    async def register_domain(domains: list[str], regperiod: list[int]) -> str:
        """Registra uno o varios dominios nuevos usando el saldo de la cuenta NEUBOX.

        ⚠️ ADVERTENCIA: Esta operación descuenta saldo real de la cuenta.
        El agente debe confirmar con el usuario antes de ejecutar este tool.

        Parámetros:
        - domains: Lista de dominios a registrar. Ej: ['example.com']
        - regperiod: Períodos en años, mismo orden que domains. Ej: [1]

        Los arrays domains y regperiod deben tener la misma longitud.
        """
        try:
            data = RegisterDomainInput(domains=domains, regperiod=regperiod)
        except Exception as exc:
            return f"Error de validación: {exc}"

        if len(data.domains) != len(data.regperiod):
            return "Error: Los arrays 'domains' y 'regperiod' deben tener la misma longitud."

        result = await client.register_domain(data.domains, data.regperiod)
        return _format_result(result)

    @mcp.tool()
    async def renew_domain(domains: list[str], renewperiod: list[int]) -> str:
        """Renueva uno o varios dominios existentes en la cuenta NEUBOX.

        ⚠️ ADVERTENCIA: Esta operación descuenta saldo real de la cuenta.
        El agente debe confirmar con el usuario antes de ejecutar este tool.

        Parámetros:
        - domains: Lista de dominios a renovar. Ej: ['example.com']
        - renewperiod: Períodos en años, mismo orden que domains. Ej: [1]

        Los arrays domains y renewperiod deben tener la misma longitud.
        """
        try:
            data = RenewDomainInput(domains=domains, renewperiod=renewperiod)
        except Exception as exc:
            return f"Error de validación: {exc}"

        if len(data.domains) != len(data.renewperiod):
            return "Error: Los arrays 'domains' y 'renewperiod' deben tener la misma longitud."

        result = await client.renew_domain(data.domains, data.renewperiod)
        return _format_result(result)

    @mcp.tool()
    async def search_domains(domain: str, tlds: list[str]) -> str:
        """Busca la disponibilidad de un nombre de dominio en uno o varios TLDs.

        Parámetros:
        - domain: Nombre de dominio a buscar, con o sin TLD. Ej: 'midominio' o 'midominio.com'
        - tlds: Lista de TLDs a consultar. Ej: ['com', 'mx', 'net']

        Retorna dos arrays: 'available' (TLDs disponibles) y 'unavailable' (TLDs no disponibles).
        """
        try:
            data = SearchDomainsInput(domain=domain, tlds=tlds)
        except Exception as exc:
            return f"Error de validación: {exc}"

        result = await client.search_domains(data.domain, data.tlds)
        return _format_result(result)