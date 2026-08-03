import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

// ---------------------------------------------------------------------------
// Configuration & startup validation
// ---------------------------------------------------------------------------

const REQUIRED_ENV_VARS = ["NEUBOX_API_KEY", "NEUBOX_API_SECRET", "NEUBOX_USER_EMAIL"];

for (const varName of REQUIRED_ENV_VARS) {
  if (!process.env[varName]) {
    console.error(
      `[neubox-mcp] ERROR: La variable de entorno "${varName}" es requerida pero no está definida.\n` +
      `Por favor configura las variables NEUBOX_API_KEY, NEUBOX_API_SECRET y NEUBOX_USER_EMAIL.`
    );
    process.exit(1);
  }
}

const API_KEY    = process.env.NEUBOX_API_KEY;
const API_SECRET = process.env.NEUBOX_API_SECRET;
const USER_EMAIL = process.env.NEUBOX_USER_EMAIL;
const BASE_URL   = "https://api.neubox.com";
const USER_AGENT = "neubox-mcp/1.0";
const TIMEOUT_MS = 15_000;

// ---------------------------------------------------------------------------
// HTTP helper
// ---------------------------------------------------------------------------

/**
 * Builds the common headers required by every NEUBOX API request.
 * The email is Base64-encoded as the API requires.
 */
function buildHeaders() {
  const emailB64 = Buffer.from(USER_EMAIL).toString("base64");
  return {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "neubox-api-key": API_KEY,
    "neubox-api-secret": API_SECRET,
    "neubox-user-email": emailB64,
    "User-Agent": USER_AGENT,
  };
}

/**
 * Performs a POST request to the NEUBOX API with a 15-second timeout.
 * Always returns a plain object; never throws — errors are returned as
 * { _mcpError: true, message: string } so the LLM can read them.
 *
 * @param {string} path  - API path, e.g. "/getdomains"
 * @param {object} body  - JSON body to send
 * @returns {Promise<object>}
 */
async function neuboxPost(path, body) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);

  try {
    const response = await fetch(`${BASE_URL}${path}`, {
      method: "POST",
      headers: buildHeaders(),
      body: JSON.stringify(body),
      signal: controller.signal,
    });

    const text = await response.text();

    try {
      return JSON.parse(text);
    } catch {
      return {
        _mcpError: true,
        message: `La API de NEUBOX retornó una respuesta no válida (HTTP ${response.status}): ${text.slice(0, 200)}`,
      };
    }
  } catch (err) {
    if (err.name === "AbortError") {
      return {
        _mcpError: true,
        message: `La petición a ${BASE_URL}${path} superó el tiempo límite de ${TIMEOUT_MS / 1000} segundos.`,
      };
    }
    return {
      _mcpError: true,
      message: `Error de red al conectar con la API de NEUBOX: ${err.message}`,
    };
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Formats an API response (or an internal MCP error) into a plain string
 * that will be returned to the LLM as tool output.
 *
 * @param {object} data
 * @returns {string}
 */
function formatResult(data) {
  if (data && data._mcpError) {
    return `Error: ${data.message}`;
  }
  return JSON.stringify(data, null, 2);
}

// ---------------------------------------------------------------------------
// MCP Server setup
// ---------------------------------------------------------------------------

const server = new McpServer({
  name: "neubox-mcp",
  version: "1.0.0",
});

// ---------------------------------------------------------------------------
// Tool: list_domains
// ---------------------------------------------------------------------------

server.tool(
  "list_domains",
  "Obtiene el listado completo de dominios registrados en la cuenta NEUBOX, incluyendo fecha de registro, fecha de expiración, monto de renovación y estado de cada dominio.",
  {},
  async () => {
    const emailB64 = Buffer.from(USER_EMAIL).toString("base64");
    const data = await neuboxPost("/getdomains", { email: emailB64 });
    return {
      content: [{ type: "text", text: formatResult(data) }],
    };
  }
);

// ---------------------------------------------------------------------------
// Tool: register_domain
// ---------------------------------------------------------------------------

server.tool(
  "register_domain",
  "Registra uno o varios dominios nuevos en NEUBOX usando el saldo disponible en la cuenta. Requiere la lista de dominios y sus períodos de registro en años.",
  {
    domains: z
      .array(z.string().min(1))
      .min(1)
      .describe('Lista de nombres de dominio a registrar. Ejemplo: ["example.com", "example.mx"]'),
    regperiod: z
      .array(z.number().int().positive())
      .min(1)
      .describe('Períodos de registro en años para cada dominio, en el mismo orden que "domains". Ejemplo: [1, 2]'),
  },
  async ({ domains, regperiod }) => {
    // Validate arrays have the same length
    if (domains.length !== regperiod.length) {
      return {
        content: [
          {
            type: "text",
            text: `Error de validación: "domains" tiene ${domains.length} elemento(s) pero "regperiod" tiene ${regperiod.length}. Ambos arrays deben tener la misma longitud.`,
          },
        ],
      };
    }

    const data = await neuboxPost("/registerdomain", { domains, regperiod });
    return {
      content: [{ type: "text", text: formatResult(data) }],
    };
  }
);

// ---------------------------------------------------------------------------
// Tool: renew_domain
// ---------------------------------------------------------------------------

server.tool(
  "renew_domain",
  "Renueva uno o varios dominios existentes en NEUBOX usando el saldo disponible en la cuenta. Requiere la lista de dominios y sus períodos de renovación en años.",
  {
    domains: z
      .array(z.string().min(1))
      .min(1)
      .describe('Lista de nombres de dominio a renovar. Ejemplo: ["example.com", "example.mx"]'),
    renewperiod: z
      .array(z.number().int().positive())
      .min(1)
      .describe('Períodos de renovación en años para cada dominio, en el mismo orden que "domains". Ejemplo: [1, 2]'),
  },
  async ({ domains, renewperiod }) => {
    // Validate arrays have the same length
    if (domains.length !== renewperiod.length) {
      return {
        content: [
          {
            type: "text",
            text: `Error de validación: "domains" tiene ${domains.length} elemento(s) pero "renewperiod" tiene ${renewperiod.length}. Ambos arrays deben tener la misma longitud.`,
          },
        ],
      };
    }

    const data = await neuboxPost("/renewdomain", { domains, renewperiod });
    return {
      content: [{ type: "text", text: formatResult(data) }],
    };
  }
);

// ---------------------------------------------------------------------------
// Tool: search_domains
// ---------------------------------------------------------------------------

server.tool(
  "search_domains",
  "Busca la disponibilidad de un nombre de dominio en uno o varios TLDs (extensiones) en NEUBOX. Retorna qué TLDs están disponibles y cuáles no.",
  {
    domain: z
      .string()
      .min(1)
      .describe('Nombre de dominio a buscar, con o sin TLD. Ejemplo: "midominio.com" o "midominio"'),
    tlds: z
      .array(z.string().min(1))
      .min(1)
      .describe('Lista de TLDs a consultar. Ejemplo: ["com", "mx", "net"]'),
  },
  async ({ domain, tlds }) => {
    const data = await neuboxPost("/searchdomains", { domain, tlds });
    return {
      content: [{ type: "text", text: formatResult(data) }],
    };
  }
);

// ---------------------------------------------------------------------------
// Start server & graceful shutdown
// ---------------------------------------------------------------------------

const transport = new StdioServerTransport();

process.on("SIGINT", async () => {
  console.error("[neubox-mcp] Recibida señal SIGINT. Cerrando servidor...");
  await server.close();
  process.exit(0);
});

process.on("SIGTERM", async () => {
  console.error("[neubox-mcp] Recibida señal SIGTERM. Cerrando servidor...");
  await server.close();
  process.exit(0);
});

await server.connect(transport);
console.error("[neubox-mcp] Servidor MCP iniciado correctamente. Esperando conexiones via stdio.");
