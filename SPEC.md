# Especificación Técnica: MCP Neubox Python para N8N

---

## 1. Contexto y Objetivo

Servidor **MCP (Model Context Protocol)** escrito en **Python** que integra la API REST de NEUBOX (`https://api.neubox.com`). Diseñado para ser consumido por un **Agente de IA en N8N** mediante el transporte `streamable-http` del MCP Python SDK.

Desplegado en un contenedor Docker, expuesto públicamente vía Apache con SSL (Certbot), con tres capas de seguridad: API Key, IP Whitelist y Rate Limiting.

**URL base de la API:** `https://api.neubox.com`

**Referencia:** https://neubox.com/developers

---

## 2. Actores y Roles

| Actor | Descripción |
|---|---|
| Usuario final | Persona que interactúa con el agente de IA en N8N |
| Agente de IA (N8N) | Recibe el prompt, interpreta intención, llama tools del MCP, responde en español |
| Servidor MCP Python | Proceso en Docker que valida seguridad y traduce tools en llamadas a NEUBOX |
| Apache + Certbot | Reverse proxy con SSL que termina TLS y redirige al contenedor |
| API NEUBOX | Sistema externo que ejecuta operaciones reales sobre dominios |

---

## 3. Requerimientos Funcionales

| ID | Requerimiento | Prioridad |
|---|---|---|
| FR-001 | Exponer tool `list_domains` que retorna dominios registrados en la cuenta NEUBOX | Alta |
| FR-002 | Exponer tool `register_domain` para registrar dominios con períodos de registro | Alta |
| FR-003 | Exponer tool `renew_domain` para renovar dominios con períodos de renovación | Alta |
| FR-004 | Exponer tool `search_domains` para buscar disponibilidad en múltiples TLDs | Alta |
| FR-005 | Validar parámetros de entrada con Pydantic antes de cada llamada HTTP | Alta |
| FR-006 | Codificar email en Base64 automáticamente antes de enviarlo a la API | Alta |
| FR-007 | Retornar errores de NEUBOX como texto legible al agente sin interrumpir el servidor | Alta |
| FR-008 | Validar header `X-API-Key`; si falta o no coincide → HTTP 401 | Crítica |
| FR-009 | Validar IP del cliente contra whitelist; si no autorizada → HTTP 403 | Crítica |
| FR-010 | Aplicar rate limiting por IP configurable vía env vars | Alta |
| FR-011 | Exponer `GET /health` sin auth ni IP whitelist para health checks | Media |
| FR-012 | Usar transporte `streamable-http` del MCP Python SDK en path `/mcp` | Alta |
| FR-013 | Generar `N8N_AGENT_GUIDE.md` como system prompt para el agente de IA | Alta |
| FR-014 | El agente debe responder siempre en español en lenguaje natural | Alta |

---

## 4. Requerimientos No Funcionales

| ID | Requerimiento | Métrica |
|---|---|---|
| NFR-001 | Python >= 3.11 | — |
| NFR-002 | MCP Python SDK con transporte `streamable-http` | — |
| NFR-003 | Imagen Docker `python:3.12-slim` | — |
| NFR-004 | Puerto expuesto configurable, default 8000 | — |
| NFR-005 | Credenciales NEUBOX desde variables de entorno únicamente | Sin credenciales en código |
| NFR-006 | `MCP_API_KEY` desde variable de entorno | — |
| NFR-007 | `IP_WHITELIST` desde env, formato CSV con soporte CIDR | ej: `192.168.0.0/24,10.0.0.5` |
| NFR-008 | Rate limit: `RATE_LIMIT_REQUESTS` (default 60) y `RATE_LIMIT_WINDOW` (default 60s) | — |
| NFR-009 | Timeout 15s por petición a NEUBOX | — |
| NFR-010 | User-Agent: `neubox-mcp-py/1.0` | — |
| NFR-011 | Logging estructurado a stdout, nivel configurable con `LOG_LEVEL` | — |
| NFR-012 | Manejo graceful de SIGINT/SIGTERM | — |
| NFR-013 | Apache como reverse proxy con SSL vía Certbot | TLS terminado en Apache |
| NFR-014 | No TLS dentro del contenedor | — |

---

## 5. Arquitectura

```
┌──────────────────────────────────────────────────┐
│  Contenedor Docker (neubox-mcp-py)               │
│  Puerto: 8000                                     │
│                                                   │
│  ┌──────────────────────────────────────────────┐ │
│  │  Starlette App                               │ │
│  │  ├── Middleware: IP Whitelist (CIDR)          │ │
│  │  ├── Middleware: API Key (X-API-Key)        │ │
│  │  ├── Middleware: Rate Limiting (fixed window) │ │
│  │  ├── GET /health (sin auth)                  │ │
│  │  └── Mount /mcp → MCP streamable-http        │ │
│  │       ├── Tool: list_domains                 │ │
│  │       ├── Tool: register_domain              │ │
│  │       ├── Tool: renew_domain                 │ │
│  │       └── Tool: search_domains               │ │
│  └──────────────────────────────────────────────┘ │
│                       │                           │
│                       ▼ HTTPS (timeout 15s)       │
│              ┌─────────────────┐                   │
│              │ api.neubox.com  │                   │
│              └─────────────────┘                   │
└──────────────────────────────────────────────────┘
        ▲                          ▲
        │ HTTP + X-API-Key          │ HTTP + X-API-Key
        │                          │
  ┌─────┴─────┐            ┌──────┴──────┐
  │ N8N        │            │ Otros       │
  │ Agente IA  │            │ servidores  │
  └────────────┘            └─────────────┘
        ▲
        │ HTTPS (SSL via Certbot)
        │
  ┌─────┴─────┐
  │ Apache     │
  │ Reverse    │
  │ Proxy      │
  └────────────┘
```

---

## 6. Estructura del Proyecto

```
neubox-mcp/
├── main.py                 # Entrada: Starlette app + middlewares + MCP mount
├── neubox_client.py        # Cliente HTTP async para API NEUBOX
├── middleware.py           # API Key, IP Whitelist, Rate Limiting
├── tools.py                # 4 tools MCP + schemas Pydantic
├── config.py               # Carga de variables de entorno
├── requirements.txt        # Dependencias Python
├── Dockerfile              # Imagen Docker
├── .env.example            # Template de variables de entorno
├── SPEC.md                 # Este documento
├── N8N_AGENT_GUIDE.md      # System prompt para agente N8N
├── README.md               # Documentación de usuario
└── AGENTS.md               # Instrucciones para agentes de código
```

---

## 7. Contratos de las Tools MCP

### 7.1 `list_domains`

**Endpoint:** `POST https://api.neubox.com/getdomains`
**Parámetros:** Ninguno.

**Headers:**
```
Accept: application/json
Content-Type: application/json
neubox-api-key: <NEUBOX_API_KEY>
neubox-api-secret: <NEUBOX_API_SECRET>
neubox-user-email: <base64(NEUBOX_USER_EMAIL)>
User-Agent: neubox-mcp-py/1.0
```

**Body:** `{"email": "<base64(NEUBOX_USER_EMAIL)>"}`

**Respuesta exitosa:**
```json
{
  "result": "success",
  "response": [
    {"domain": "midominio.com", "registrationdate": "2019-04-21", "recurringamount": 591.25, "expirydate": "2026-04-21", "status": "Active"}
  ]
}
```

---

### 7.2 `register_domain`

**Endpoint:** `POST https://api.neubox.com/registerdomain`

**Parámetros:**
- `domains` (list[str]): Dominios a registrar. Ej: `["example.com"]`
- `regperiod` (list[int]): Períodos en años. Ej: `[1]`

**Validaciones:** BR-001, BR-002

**Body:** `{"domains": [...], "regperiod": [...]}`

**Respuesta exitosa:**
```json
{"result": "success", "response": {"result": "success", "invoiceid": 22333, "amount": 591.25, "invoicepaid": "true", "credit": "826.48", "example.com": "registered"}}
```

**Respuesta error (crédito insuficiente):**
```json
{"result": "success", "response": {"result": "error", "message": "Crédito insuficiente...", "credit": "$150.96", "invoiceid": 102013, "invoicepaid": "unpaid"}}
```

---

### 7.3 `renew_domain`

**Endpoint:** `POST https://api.neubox.com/renewdomain`

**Parámetros:**
- `domains` (list[str]): Dominios a renovar. Ej: `["example.com"]`
- `renewperiod` (list[int]): Períodos en años. Ej: `[1]`

**Validaciones:** BR-003, BR-004

**Body:** `{"domains": [...], "renewperiod": [...]}`

---

### 7.4 `search_domains`

**Endpoint:** `POST https://api.neubox.com/searchdomains`

**Parámetros:**
- `domain` (str): Nombre de dominio. Ej: `"midominio"`
- `tlds` (list[str]): TLDs a consultar. Ej: `["com", "mx", "net"]`

**Validaciones:** BR-005, BR-006

**Body:** `{"domain": "...", "tlds": [...]}`

**Respuesta exitosa:**
```json
{"result": "success", "response": {"search": "midominio.com", "sld": "midominio", "tld": "com", "available": ["net", "com"], "unavailable": ["mx"]}}
```

**Respuesta error (rate limit):**
```json
{"result": "error", "error": "Only 10 requests per minute are allowed"}
```

---

## 8. Middlewares de Seguridad

### 8.1 Orden de ejecución

```
Request → IP Whitelist → API Key → Rate Limit → /health or /mcp
```

### 8.2 IP Whitelist

| Aspecto | Detalle |
|---|---|
| Variable | `IP_WHITELIST` — CSV con soporte CIDR |
| Formato | `192.168.0.0/24,10.0.0.5,203.0.113.50` |
| Excepción | `/health` no se valida |
| Rechazo | HTTP 403 `{"error": "IP no autorizada"}` |
| IP vacía | Si `IP_WHITELIST` está vacía, se permite todo (modo desarrollo) |

### 8.3 API Key Auth

| Aspecto | Detalle |
|---|---|
| Variable | `MCP_API_KEY` |
| Header | `X-API-Key: <valor>` |
| Excepción | `/health` no se valida |
| Rechazo | HTTP 401 `{"error": "API Key inválida o ausente"}` |

### 8.4 Rate Limiting

| Aspecto | Detalle |
|---|---|
| Variables | `RATE_LIMIT_REQUESTS` (default 60), `RATE_LIMIT_WINDOW` (default 60s) |
| Algoritmo | Fixed window en memoria (dict por IP) |
| Sin distinción | Contenedores locales y externos tienen el mismo límite |
| Excepción | `/health` sí está sujeto a rate limiting |
| Rechazo | HTTP 429 `{"error": "Rate limit excedido"}` + header `Retry-After` |

---

## 9. Variables de Entorno

| Variable | Requerida | Default | Descripción |
|---|---|---|---|
| `NEUBOX_API_KEY` | ✅ | — | API Key de NEUBOX |
| `NEUBOX_API_SECRET` | ✅ | — | API Secret de NEUBOX |
| `NEUBOX_USER_EMAIL` | ✅ | — | Email NEUBOX (texto plano, se codifica a Base64) |
| `MCP_API_KEY` | ✅ | — | API Key de acceso al MCP |
| `IP_WHITELIST` | ❌ | (vacío = permitir todo) | Lista blanca de IPs (CSV, soporta CIDR) |
| `RATE_LIMIT_REQUESTS` | ❌ | 60 | Peticiones máximas por ventana |
| `RATE_LIMIT_WINDOW` | ❌ | 60 | Tamaño de ventana en segundos |
| `MCP_PORT` | ❌ | 8000 | Puerto del servidor MCP |
| `LOG_LEVEL` | ❌ | INFO | Nivel de logging |

---

## 10. Reglas de Negocio

| ID | Regla |
|---|---|
| BR-001 | `register_domain`: `domains` y `regperiod` misma longitud |
| BR-002 | `register_domain`: cada `regperiod` entero > 0 |
| BR-003 | `renew_domain`: `domains` y `renewperiod` misma longitud |
| BR-004 | `renew_domain`: cada `renewperiod` entero > 0 |
| BR-005 | `search_domains`: `tlds` mínimo 1 elemento |
| BR-006 | `search_domains`: `domain` no vacío |
| BR-007 | `register_domain` y `renew_domain` incluyen warning en su descripción |
| BR-008 | El agente debe pedir confirmación al usuario antes de register/renew |

---

## 11. Manejo de Errores

| Escenario | Comportamiento |
|---|---|
| Variable de entorno faltante | El proceso termina con código 1 y mensaje en español |
| Parámetros inválidos | Retorna al agente mensaje de error de validación, sin interrumpir el servidor |
| Error de red o timeout | Retorna al agente mensaje indicando fallo de conexión |
| Error de autenticación NEUBOX | Retorna el mensaje de error de la API tal como fue recibido |
| Rate limit NEUBOX excedido | Retorna el mensaje de rate limit de la API |
| Crédito insuficiente | Retorna estado de factura y crédito disponible |
| Respuesta no JSON | Retorna mensaje indicando respuesta inesperada |
| API Key inválida/ausente | HTTP 401 JSON |
| IP no autorizada | HTTP 403 JSON |
| Rate limit del MCP excedido | HTTP 429 JSON + Retry-After |

---

## 12. Dependencias

```
mcp>=1.0.0
httpx>=0.27.0
pydantic>=2.0.0
starlette>=0.37.0
uvicorn>=0.30.0
```

---

## 13. Criterios de Aceptación

| ID | Criterio |
|---|---|
| AC-001 | `list_domains` retorna dominios cuando las credenciales son válidas |
| AC-002 | `register_domain` registra dominios y retorna invoiceid + credit |
| AC-003 | `renew_domain` renueva dominios y retorna invoiceid + credit |
| AC-004 | `search_domains` retorna TLDs disponibles y no disponibles |
| AC-005 | Parámetros inválidos → mensaje de error descriptivo |
| AC-006 | Petición sin X-API-Key → HTTP 401 |
| AC-007 | IP no autorizada → HTTP 403 |
| AC-008 | Exceder rate limit → HTTP 429 + Retry-After |
| AC-009 | `GET /health` → 200 sin auth |
| AC-010 | N8N_AGENT_GUIDE.md existe y describe las 4 tools |
| AC-011 | Timeout 15s → error legible |
| AC-012 | SIGTERM → cierre graceful |
| AC-013 | Email codificado en Base64 en headers y body |
| AC-014 | User-Agent: `neubox-mcp-py/1.0` |

---

## 14. Supuestos y Restricciones

- La API de NEUBOX usa API Key + Secret estáticos (sin OAuth).
- Rate limit del endpoint `searchdomains`: 10 peticiones/minuto (impuesto por NEUBOX).
- No hay caché de respuestas; cada invocación genera una nueva petición HTTP.
- Una instancia del MCP opera con una sola cuenta NEUBOX.
- No se implementan tests automatizados en esta versión inicial.
- TLS se termina en Apache; el contenedor no maneja HTTPS.
- El algoritmo de rate limiting es fixed window en memoria (sin Redis).