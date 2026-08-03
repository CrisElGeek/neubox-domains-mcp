# Instrucciones para agentes — neubox-mcp

## Qué es este repo

Servidor MCP (Model Context Protocol) de un solo archivo para OpenCode. Conecta con la API de administración de dominios de NEUBOX (`https://api.neubox.com`) y expone 4 tools: `list_domains`, `register_domain`, `renew_domain`, `search_domains`.

## Estructura

- `index.js` — punto de entrada único del servidor MCP (ESM, no TypeScript).
- `package.json` — única dependencia declarada: `@modelcontextprotocol/sdk` (versión `latest`).
- `README.md` — documentación de usuario.
- `SPEC.md` — contratos de API, flujos y criterios de aceptación.
- **No hay tests, linter, formatter, typecheck, build ni CI.**

## Requisitos y arranque

- Node.js >= 18.0.0 (necesario para `fetch` nativo).
- Requiere 3 variables de entorno al arrancar:
  - `NEUBOX_API_KEY`
  - `NEUBOX_API_SECRET`
  - `NEUBOX_USER_EMAIL` (texto plano; el servidor la codifica a Base64).
- Si falta alguna variable, el proceso termina con código 1 y un mensaje en español.

```bash
npm install
npm start          # alias de `node index.js`
```

## Configuración en OpenCode

El servidor se registra como MCP local por stdio. Ejemplo en `opencode.json`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "neubox": {
      "type": "local",
      "command": ["node", "/ruta/absoluta/neubox-mcp/index.js"],
      "enabled": true,
      "env": {
        "NEUBOX_API_KEY": "...",
        "NEUBOX_API_SECRET": "...",
        "NEUBOX_USER_EMAIL": "..."
      }
    }
  }
}
```

## Gotchas importantes

- **ESM implícito:** `package.json` tiene `"type": "module"`. No usar `require()`.
- **Zod no está en `dependencies` explícitas:** `index.js` importa `zod`, pero está disponible como dependencia transitiva de `@modelcontextprotocol/sdk`. Si se actualizan o reinstalan paquetes, considera declarar `zod` en `dependencies` para evitar romper la importación.
- **Operaciones con dinero real:** `register_domain` y `renew_domain` descuentan saldo de la cuenta NEUBOX. No ejecutar con dominios de prueba sin confirmar primero.
- **Rate limit:** el endpoint `searchdomains` tiene límite de 10 peticiones/minuto. El servidor no implementa reintentos ni cola.
- **Timeout fijo:** 15 segundos por petición a la API de NEUBOX.
- **User-Agent fijo:** todas las peticiones envían `User-Agent: neubox-mcp/1.0`.
- **Codificación de email:** el servidor codifica `NEUBOX_USER_EMAIL` en Base64 para los headers y el body cuando aplica.
- **Errores de red:** se devuelven como texto al LLM, no lanzan excepciones fuera del handler; esto evita que el proceso MCP se rompa.

## Cómo hacer cambios

- Editar únicamente `index.js` para lógica del servidor o tools.
- Si se agrega una tool nueva, mantener el mismo patrón: validación de inputs con Zod, llamada a `neuboxPost`, y respuesta con `formatResult`.
- Actualizar `README.md` y `SPEC.md` si cambian los contratos de las tools o la configuración de OpenCode.
- No hay verificación automatizada: antes de considerar listo un cambio, arrancar el servidor con `npm start` y comprobar que no falle la validación de variables de entorno.
