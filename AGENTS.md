# Instrucciones para agentes — neubox-mcp

## Qué es este repo

Servidor MCP (Model Context Protocol) en **Python** que conecta con la API de administración de dominios de NEUBOX (`https://api.neubox.com`). Diseñado para ser consumido por un Agente de IA en N8N mediante transporte HTTP `streamable-http`. Expone 4 tools: `list_domains`, `register_domain`, `renew_domain`, `search_domains`.

## Estructura

- `main.py` — punto de entrada: Starlette app + middlewares + MCP mount + uvicorn
- `neubox_client.py` — cliente HTTP async (httpx) para la API de NEUBOX
- `middleware.py` — 3 middlewares: IP Whitelist (CIDR), API Key, Rate Limiting (fixed window)
- `tools.py` — definición de las 4 tools MCP con schemas Pydantic
- `config.py` — carga y validación de variables de entorno
- `requirements.txt` — dependencias Python
- `Dockerfile` — imagen Docker `python:3.12-slim`
- `.env.example` — template de variables de entorno
- `SPEC.md` — especificación técnica completa
- `N8N_AGENT_GUIDE.md` — system prompt para el agente de IA de N8N
- `README.md` — documentación de usuario
- **No hay tests, linter, formatter, typecheck, build ni CI.**

## Requisitos y arranque

- Python >= 3.11
- Requiere variables de entorno al arrancar (ver `.env.example`):
  - `NEUBOX_API_KEY` (requerida)
  - `NEUBOX_API_SECRET` (requerida)
  - `NEUBOX_USER_EMAIL` (requerida, texto plano; el servidor la codifica a Base64)
  - `MCP_API_KEY` (requerida, token de acceso al MCP)
  - `IP_WHITELIST` (opcional, CSV con CIDR; vacío = permitir todas)
  - `RATE_LIMIT_REQUESTS` (opcional, default 60)
  - `RATE_LIMIT_WINDOW` (opcional, default 60 seg)
  - `MCP_PORT` (opcional, default 8000)
  - `LOG_LEVEL` (opcional, default INFO)
- Si falta una variable requerida, el proceso termina con código 1 y un mensaje en español.

```bash
pip install -r requirements.txt
python main.py
```

O con Docker:

```bash
docker build -t neubox-mcp .
docker run -d -p 8000:8000 --env-file .env neubox-mcp
```

## Despliegue

El contenedor expone el puerto 8000 por HTTP. Se recomienda usar Apache como reverse proxy con SSL vía Certbot. Ver `README.md` para la configuración completa de Apache.

## Gotchas importantes

- **Transporte HTTP, no stdio:** A diferencia de la versión anterior en Node.js, este MCP usa `streamable-http` del MCP Python SDK. El endpoint MCP está en `/mcp`.
- **Async:** El cliente HTTP usa `httpx.AsyncClient`. Todas las tools son `async`.
- **Middlewares encadenados:** Orden de ejecución: IP Whitelist → API Key → Rate Limit → handler. `/health` está exento de IP Whitelist y API Key pero no de Rate Limit.
- **Operaciones con dinero real:** `register_domain` y `renew_domain` descuentan saldo de la cuenta NEUBOX. Las tools incluyen warnings en su descripción para que el agente pida confirmación.
- **Rate limit NEUBOX:** el endpoint `searchdomains` tiene límite de 10 peticiones/minuto. El servidor no implementa reintentos.
- **Timeout fijo:** 15 segundos por petición a la API de NEUBOX.
- **User-Agent fijo:** `neubox-mcp-py/1.0`.
- **Codificación de email:** el servidor codifica `NEUBOX_USER_EMAIL` en Base64 para headers y body.
- **Rate limiting en memoria:** usa un dict en memoria (fixed window). Se reinicia al reiniciar el contenedor. No hay Redis.
- **IP Whitelist con CIDR:** soporta notación CIDR (ej: `192.168.0.0/24`). Usa la librería `ipaddress` de Python.
- **Errores de red:** se devuelven como texto al LLM, no lanzan excepciones fuera del handler.

## Cómo hacer cambios

- **Lógica del servidor o middlewares:** editar `main.py` o `middleware.py`
- **Lógica de tools o validaciones:** editar `tools.py`
- **Cliente HTTP a NEUBOX:** editar `neubox_client.py`
- **Variables de entorno:** editar `config.py`
- Si se agrega una tool nueva, mantener el patrón: schema Pydantic, validación, llamada a `NeuboxClient`, `_format_result`.
- Actualizar `SPEC.md`, `N8N_AGENT_GUIDE.md` y `README.md` si cambian los contratos o la config.
- No hay verificación automatizada: antes de considerar listo un cambio, arrancar el servidor con `python main.py` y comprobar que no falle la validación de variables de entorno.