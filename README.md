# neubox-mcp

Servidor MCP (Model Context Protocol) para OpenCode que integra la API de administración de dominios de [NEUBOX](https://neubox.com).

Permite administrar dominios directamente desde el asistente de IA: listar, registrar, renovar y buscar disponibilidad de dominios, sin necesidad de acceder al panel web de NEUBOX.

---

## Requisitos

- Node.js v18 o superior
- Cuenta NEUBOX con acceso a API (Resellers, Domainers, Distribuidores o clientes con más de 50 dominios)
- API Key, API Secret y email de la cuenta NEUBOX

---

## Instalación

```bash
# 1. Clona o copia el proyecto
cd neubox-mcp

# 2. Instala las dependencias
npm install
```

---

## Configuración en OpenCode

Agrega la siguiente configuración a tu archivo `opencode.json` (en la raíz de tu proyecto o en `~/.config/opencode/opencode.json`):

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

> Reemplaza `/ruta/absoluta/neubox-mcp/index.js` con la ruta real donde clonaste el proyecto.
> Reemplaza los valores de `env` con tus credenciales de NEUBOX.

Reinicia OpenCode para que los cambios tomen efecto.

---

## Variables de Entorno

| Variable | Descripción |
|---|---|
| `NEUBOX_API_KEY` | API Key de tu cuenta NEUBOX |
| `NEUBOX_API_SECRET` | API Secret de tu cuenta NEUBOX |
| `NEUBOX_USER_EMAIL` | Email registrado en tu cuenta NEUBOX (en texto plano, el MCP lo codifica en Base64) |

---

## Tools disponibles

### `list_domains`
Obtiene el listado completo de dominios en tu cuenta NEUBOX.

**Ejemplo de uso en OpenCode:**
> "Lista todos mis dominios de NEUBOX"

---

### `register_domain`
Registra uno o varios dominios nuevos usando el saldo de tu cuenta.

**Parámetros:**
- `domains` — Array de dominios a registrar. Ej: `["example.com", "example.mx"]`
- `regperiod` — Array de períodos en años (mismo orden que domains). Ej: `[1, 2]`

**Ejemplo de uso en OpenCode:**
> "Registra example.com por 1 año y example.mx por 2 años en NEUBOX"

---

### `renew_domain`
Renueva uno o varios dominios existentes.

**Parámetros:**
- `domains` — Array de dominios a renovar. Ej: `["example.com", "example.mx"]`
- `renewperiod` — Array de períodos en años (mismo orden que domains). Ej: `[1, 1]`

**Ejemplo de uso en OpenCode:**
> "Renueva example.com por 1 año en NEUBOX"

---

### `search_domains`
Busca la disponibilidad de un dominio en uno o varios TLDs.

**Parámetros:**
- `domain` — Nombre de dominio a buscar. Ej: `"midominio.com"`
- `tlds` — Array de TLDs a consultar. Ej: `["com", "mx", "net"]`

**Ejemplo de uso en OpenCode:**
> "Busca si midominio está disponible en .com, .mx y .net en NEUBOX"

---

## Estructura del proyecto

```
neubox-mcp/
├── index.js      # Servidor MCP principal
├── package.json  # Dependencias y configuración del paquete
├── SPEC.md       # Especificación técnica completa
└── README.md     # Este archivo
```

---

## Notas importantes

- La API de NEUBOX tiene un límite de **10 peticiones por minuto** en el endpoint de búsqueda de dominios.
- Las operaciones de compra y renovación **descuentan saldo real** de tu cuenta. Úsalas con precaución.
- Nunca compartas tus credenciales de API con personas no autorizadas.
