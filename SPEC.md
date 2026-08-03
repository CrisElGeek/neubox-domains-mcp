# Especificación Técnica: MCP Neubox para OpenCode

---

## 1. Contexto y Objetivo

Desarrollar un servidor **MCP (Model Context Protocol)** escrito en **JavaScript (Node.js)** que integre la API REST de NEUBOX, permitiendo que OpenCode —y cualquier cliente MCP compatible— administre dominios directamente desde el asistente de IA, sin necesidad de interactuar manualmente con la plataforma web de NEUBOX.

**URL base de la API:** `https://api.neubox.com`

**Restricción de acceso:** La API de NEUBOX está disponible únicamente para Resellers, Domainers, Distribuidores o clientes con más de 50 dominios registrados.

---

## 2. Actores y Roles

| Actor | Descripción |
|---|---|
| Usuario de OpenCode | Persona que interactúa con el LLM para administrar dominios vía lenguaje natural |
| Servidor MCP Neubox | Proceso Node.js que traduce las intenciones del LLM en llamadas a la API de NEUBOX |
| API de NEUBOX | Sistema externo que ejecuta las operaciones reales sobre los dominios |

---

## 3. Requerimientos Funcionales

| ID | Requerimiento |
|---|---|
| FR-001 | El servidor MCP debe exponer la tool `list_domains` para obtener el listado de dominios registrados en la cuenta NEUBOX. |
| FR-002 | El servidor MCP debe exponer la tool `register_domain` para registrar uno o varios dominios nuevos con sus respectivos períodos de registro. |
| FR-003 | El servidor MCP debe exponer la tool `renew_domain` para renovar uno o varios dominios existentes con sus respectivos períodos de renovación. |
| FR-004 | El servidor MCP debe exponer la tool `search_domains` para buscar la disponibilidad de un dominio en uno o varios TLDs. |
| FR-005 | Cada tool debe validar los parámetros de entrada antes de ejecutar la llamada HTTP, retornando un mensaje de error descriptivo si faltan campos requeridos o tienen tipos incorrectos. |
| FR-006 | El email del usuario debe codificarse automáticamente en Base64 dentro del servidor antes de enviarse a la API, tanto en los headers como en el body cuando corresponda. |
| FR-007 | Los errores retornados por la API de NEUBOX (crédito insuficiente, usuario inexistente, rate limit, etc.) deben retornarse al LLM como mensajes de texto legibles, sin interrumpir el proceso del servidor MCP. |
| FR-008 | El servidor debe incluir el snippet de configuración exacto para registrarlo en OpenCode mediante `opencode.json`. |

---

## 4. Requerimientos No Funcionales

| ID | Requerimiento |
|---|---|
| NFR-001 | El servidor debe ejecutarse con **Node.js v18 o superior** para usar `fetch` nativo sin dependencias HTTP externas. |
| NFR-002 | Las credenciales (`API_KEY`, `API_SECRET`, `USER_EMAIL`) deben cargarse exclusivamente desde **variables de entorno**. El código fuente no debe contener credenciales en ninguna circunstancia. |
| NFR-003 | El transporte del servidor MCP debe ser **stdio**, compatible con el protocolo estándar de OpenCode. |
| NFR-004 | El `User-Agent` de todas las peticiones HTTP debe ser `neubox-mcp/1.0`. |
| NFR-005 | El tiempo de espera máximo por petición HTTP a la API de NEUBOX no debe superar **15 segundos**. |
| NFR-006 | La única dependencia externa permitida es `@modelcontextprotocol/sdk`. No se usarán librerías HTTP externas. |
| NFR-007 | El servidor debe manejar el cierre limpio del proceso ante señales `SIGINT` y `SIGTERM`. |

---

## 5. Estructura del Proyecto

```
neubox-mcp/
├── index.js          # Punto de entrada principal del servidor MCP
├── package.json      # Definición del paquete y dependencias
├── SPEC.md           # Este documento de especificación técnica
└── README.md         # Instrucciones de instalación, configuración y uso
```

---

## 6. Contratos de las Tools MCP

### 6.1 `list_domains`

**Descripción:** Retorna el listado completo de dominios registrados en la cuenta NEUBOX.

**Endpoint API:** `POST https://api.neubox.com/getdomains`

**inputSchema:**
```json
{
  "type": "object",
  "properties": {},
  "required": []
}
```
> No requiere parámetros del usuario. Las credenciales se toman de las variables de entorno.

**Headers de la petición:**
```
Accept: application/json
Content-Type: application/json
neubox-api-key: <NEUBOX_API_KEY>
neubox-api-secret: <NEUBOX_API_SECRET>
neubox-user-email: <base64(NEUBOX_USER_EMAIL)>
User-Agent: neubox-mcp/1.0
```

**Body de la petición:**
```json
{
  "email": "<base64(NEUBOX_USER_EMAIL)>"
}
```

**Respuesta exitosa:**
```json
{
  "result": "success",
  "response": [
    {
      "domain": "midominio.com",
      "registrationdate": "2019-04-21",
      "recurringamount": 591.25,
      "expirydate": "2026-04-21",
      "status": "Active"
    }
  ]
}
```

**Respuesta de error:**
```json
{
  "result": "success",
  "error": "Bad Request",
  "response": "User doesnt exists"
}
```

---

### 6.2 `register_domain`

**Descripción:** Registra uno o varios dominios nuevos usando el saldo disponible en la cuenta NEUBOX.

**Endpoint API:** `POST https://api.neubox.com/registerdomain`

**inputSchema:**
```json
{
  "type": "object",
  "properties": {
    "domains": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Lista de nombres de dominio a registrar. Ejemplo: [\"example.com\", \"example.mx\"]"
    },
    "regperiod": {
      "type": "array",
      "items": { "type": "number" },
      "description": "Períodos de registro en años para cada dominio, en el mismo orden que el array domains. Ejemplo: [1, 2]"
    }
  },
  "required": ["domains", "regperiod"]
}
```

**Validaciones:**
- `domains` y `regperiod` deben tener la misma longitud.
- Cada elemento de `regperiod` debe ser un entero positivo mayor a 0.

**Body de la petición:**
```json
{
  "domains": ["example.com", "example.mx"],
  "regperiod": [1, 2]
}
```

**Respuesta exitosa:**
```json
{
  "result": "success",
  "response": {
    "result": "success",
    "invoiceid": 22333,
    "amount": 591.25,
    "invoicepaid": "true",
    "credit": "826.48",
    "example.com": "registered",
    "example.mx": "registered"
  }
}
```

**Respuesta de error (crédito insuficiente):**
```json
{
  "result": "success",
  "response": {
    "result": "error",
    "message": "Crédito insuficiente...",
    "credit": "$150.96",
    "invoiceid": 102013,
    "invoicepaid": "unpaid"
  }
}
```

---

### 6.3 `renew_domain`

**Descripción:** Renueva uno o varios dominios existentes en la cuenta NEUBOX.

**Endpoint API:** `POST https://api.neubox.com/renewdomain`

**inputSchema:**
```json
{
  "type": "object",
  "properties": {
    "domains": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Lista de nombres de dominio a renovar. Ejemplo: [\"example.com\", \"example.mx\"]"
    },
    "renewperiod": {
      "type": "array",
      "items": { "type": "number" },
      "description": "Períodos de renovación en años para cada dominio, en el mismo orden que el array domains. Ejemplo: [1, 2]"
    }
  },
  "required": ["domains", "renewperiod"]
}
```

**Validaciones:**
- `domains` y `renewperiod` deben tener la misma longitud.
- Cada elemento de `renewperiod` debe ser un entero positivo mayor a 0.

**Body de la petición:**
```json
{
  "domains": ["example.com", "example.mx"],
  "renewperiod": [1, 2]
}
```

**Respuesta exitosa:**
```json
{
  "result": "success",
  "response": {
    "result": "success",
    "invoiceid": 100231,
    "amount": 462.88,
    "invoicepaid": "true",
    "credit": "882.00",
    "example.com": "registered",
    "example.mx": "registered"
  }
}
```

---

### 6.4 `search_domains`

**Descripción:** Busca la disponibilidad de un nombre de dominio en uno o varios TLDs.

**Endpoint API:** `POST https://api.neubox.com/searchdomains`

**inputSchema:**
```json
{
  "type": "object",
  "properties": {
    "domain": {
      "type": "string",
      "description": "Nombre de dominio a buscar, con o sin TLD. Ejemplo: \"midominio.com\" o \"midominio\""
    },
    "tlds": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Lista de TLDs a consultar. Ejemplo: [\"com\", \"mx\", \"net\"]"
    }
  },
  "required": ["domain", "tlds"]
}
```

**Validaciones:**
- `tlds` debe ser un array con al menos 1 elemento.
- `domain` no debe estar vacío.

**Body de la petición:**
```json
{
  "domain": "midominio.com",
  "tlds": ["mx", "net"]
}
```

**Respuesta exitosa:**
```json
{
  "result": "success",
  "response": {
    "search": "midominio.com",
    "sld": "midominio",
    "tld": "com",
    "available": ["net", "com"],
    "unavailable": ["mx"]
  }
}
```

**Respuesta de error (rate limit):**
```json
{
  "result": "error",
  "error": "Only 10 requests per minute are allowed"
}
```

---

## 7. Flujos Principales

### Flujo general de una tool

```
Usuario (LLM) -> Tool call con parámetros
      |
      v
Servidor MCP (index.js)
      |
      +--> Validar parámetros de entrada
      |         |
      |         +--> Error de validación -> Retornar mensaje de error al LLM
      |
      +--> Leer variables de entorno (API_KEY, API_SECRET, USER_EMAIL)
      |         |
      |         +--> Variable faltante -> Retornar error de configuración al LLM
      |
      +--> Codificar email en Base64
      |
      +--> Construir headers y body HTTP
      |
      +--> POST a https://api.neubox.com/<endpoint>  (timeout: 15s)
      |         |
      |         +--> Error de red / timeout -> Retornar mensaje de error al LLM
      |
      +--> Parsear respuesta JSON
      |
      +--> Retornar resultado formateado al LLM
```

---

## 8. Variables de Entorno

| Variable | Tipo | Descripción | Requerida |
|---|---|---|---|
| `NEUBOX_API_KEY` | string | API Key de la cuenta NEUBOX | Si |
| `NEUBOX_API_SECRET` | string | API Secret de la cuenta NEUBOX | Si |
| `NEUBOX_USER_EMAIL` | string | Email de la cuenta NEUBOX en texto plano (el MCP lo codifica en Base64) | Si |

---

## 9. Configuración en OpenCode

El servidor se registra en OpenCode agregando lo siguiente al archivo `opencode.json`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "neubox": {
      "type": "local",
      "command": ["node", "/ruta/absoluta/neubox-mcp/index.js"],
      "enabled": true,
      "env": {
        "NEUBOX_API_KEY": "tu_api_key",
        "NEUBOX_API_SECRET": "tu_api_secret",
        "NEUBOX_USER_EMAIL": "tu@email.com"
      }
    }
  }
}
```

---

## 10. Manejo de Errores

| Escenario | Comportamiento esperado |
|---|---|
| Variable de entorno faltante al arrancar | El servidor lanza un error descriptivo en consola y termina el proceso con código 1 |
| Parámetros inválidos o faltantes en una tool | Retorna al LLM un mensaje de texto con el campo faltante o el error de tipo, sin interrumpir el servidor |
| Error de red o timeout en la petición HTTP | Retorna al LLM un mensaje indicando fallo de conexión con la API de NEUBOX |
| La API responde con error de autenticación | Retorna al LLM el mensaje de error de la API tal como fue recibido |
| Rate limit excedido (10 requests per minute) | Retorna al LLM el mensaje de rate limit de la API |
| Crédito insuficiente en compra o renovación | Retorna al LLM el mensaje completo con el estado de la factura generada y el crédito disponible |
| Respuesta no parseable como JSON | Retorna al LLM un mensaje indicando respuesta inesperada de la API |

---

## 11. Dependencias

```json
{
  "dependencies": {
    "@modelcontextprotocol/sdk": "latest"
  },
  "engines": {
    "node": ">=18.0.0"
  }
}
```

---

## 12. Criterios de Aceptación

| ID | Criterio |
|---|---|
| CA-001 | El servidor arranca sin errores cuando las 3 variables de entorno están definidas. |
| CA-002 | El servidor termina con un mensaje claro si alguna variable de entorno está ausente. |
| CA-003 | La tool `list_domains` retorna el listado de dominios de la cuenta cuando las credenciales son válidas. |
| CA-004 | La tool `register_domain` registra dominios correctamente y retorna el `invoiceid` y el crédito restante. |
| CA-005 | La tool `renew_domain` renueva dominios correctamente y retorna el `invoiceid` y el crédito restante. |
| CA-006 | La tool `search_domains` retorna correctamente los TLDs disponibles y no disponibles para un dominio dado. |
| CA-007 | Todas las peticiones incluyen el email codificado en Base64 en el header `neubox-user-email` y en el body cuando aplica. |
| CA-008 | Los errores de la API se retornan como texto legible al LLM sin romper el proceso del servidor. |
| CA-009 | El snippet de configuración de `opencode.json` permite que OpenCode descubra y use el MCP correctamente. |
| CA-010 | El `User-Agent` de todas las peticiones es `neubox-mcp/1.0`. |

---

## 13. Supuestos y Restricciones

- La API de NEUBOX no requiere autenticación OAuth ni tokens temporales; usa API Key + Secret estáticos.
- La API impone un límite de **10 peticiones por minuto** en el endpoint `searchdomains`. El MCP no implementa reintentos automáticos en esta versión.
- El MCP no implementa caché de respuestas; cada invocación de una tool genera una nueva petición HTTP.
- El MCP opera con una sola cuenta NEUBOX por instancia (definida por las variables de entorno).
- No se implementan tests automatizados en esta versión inicial.
