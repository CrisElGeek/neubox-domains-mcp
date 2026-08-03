# neubox-mcp

Servidor MCP (Model Context Protocol) en **Python** que integra la API de administración de dominios de [NEUBOX](https://neubox.com). Diseñado para ser consumido por un Agente de IA en **N8N** mediante HTTP (`streamable-http`).

Permite administrar dominios desde lenguaje natural: listar, registrar, renovar y buscar disponibilidad, sin necesidad de acceder al panel web de NEUBOX.

---

## Características

- **Python 3.12** con MCP Python SDK (`streamable-http`)
- **Docker** con imagen `python:3.12-slim`
- **Seguridad por capas:**
  - API Key (`X-API-Key` header)
  - IP Whitelist con soporte CIDR
  - Rate Limiting configurable por IP
- **Reverse proxy** Apache con SSL vía Certbot
- **N8N Agent Guide** incluido (`N8N_AGENT_GUIDE.md`) como system prompt

---

## Requisitos

- Python >= 3.11 (si se ejecuta fuera de Docker)
- Docker (recomendado)
- Cuenta NEUBOX con acceso a API (Resellers, Domainers, Distribuidores o clientes con más de 50 dominios)
- API Key, API Secret y email de la cuenta NEUBOX
- Apache + Certbot para SSL (en el servidor host)

---

## Instalación con Docker

```bash
# 1. Clonar el proyecto
cd neubox-mcp

# 2. Copiar el template de variables de entorno
cp .env.example .env

# 3. Editar .env con tus credenciales
nano .env

# 4. Construir la imagen
docker build -t neubox-mcp .

# 5. Ejecutar el contenedor
docker run -d \
  --name neubox-mcp \
  -p 8000:8000 \
  --env-file .env \
  neubox-mcp
```

---

## Instalación sin Docker

```bash
cd neubox-mcp
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configurar variables de entorno
export NEUBOX_API_KEY="tu_api_key"
export NEUBOX_API_SECRET="tu_api_secret"
export NEUBOX_USER_EMAIL="tu@email.com"
export MCP_API_KEY="tu_token_de_acceso"

# Iniciar el servidor
python main.py
```

---

## Variables de Entorno

| Variable | Requerida | Default | Descripción |
|---|---|---|---|
| `NEUBOX_API_KEY` | ✅ | — | API Key de NEUBOX |
| `NEUBOX_API_SECRET` | ✅ | — | API Secret de NEUBOX |
| `NEUBOX_USER_EMAIL` | ✅ | — | Email NEUBOX (texto plano, el MCP lo codifica en Base64) |
| `MCP_API_KEY` | ✅ | — | Token de acceso al MCP (header `X-API-Key`) |
| `IP_WHITELIST` | ❌ | (vacío = todas) | Lista blanca de IPs, CSV con CIDR. Ej: `192.168.0.0/24,10.0.0.5` |
| `RATE_LIMIT_REQUESTS` | ❌ | 60 | Peticiones máximas por ventana por IP |
| `RATE_LIMIT_WINDOW` | ❌ | 60 | Tamaño de ventana en segundos |
| `MCP_PORT` | ❌ | 8000 | Puerto del servidor |
| `LOG_LEVEL` | ❌ | INFO | Nivel de logging (DEBUG, INFO, WARNING, ERROR) |

---

## Configuración de Apache + SSL (Certbot)

El contenedor expone el puerto 8000 por HTTP. Para exponerlo públicamente con SSL:

```bash
# 1. Instalar Certbot y obtener certificado
sudo certbot certonly --standalone -d mcp.tudominio.com

# 2. Configurar Apache como reverse proxy
sudo nano /etc/apache2/sites-available/mcp.tudominio.com.conf
```

Configuración de Apache:

```apache
<VirtualHost *:443>
    ServerName mcp.tudominio.com

    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/mcp.tudominio.com/cert.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/mcp.tudominio.com/privkey.pem
    SSLCertificateChainFile /etc/letsencrypt/live/mcp.tudominio.com/fullchain.pem

    ProxyPreserveHost On
    ProxyPass / http://localhost:8000/
    ProxyPassReverse / http://localhost:8000/

    RequestHeader set X-Forwarded-Proto "https"
</VirtualHost>

# Redirección HTTP → HTTPS
<VirtualHost *:80>
    ServerName mcp.tudominio.com
    Redirect permanent / https://mcp.tudominio.com/
</VirtualHost>
```

```bash
sudo a2ensite mcp.tudominio.com.conf
sudo a2enmod ssl proxy proxy_http headers
sudo systemctl reload apache2
```

---

## Integración con N8N

### Configuración del Agente de IA

1. El archivo `N8N_AGENT_GUIDE.md` contiene el system prompt completo para el agente.
2. Copia su contenido en el campo "System Prompt" del nodo de Agente de IA en N8N.
3. Configura el agente para que use el MCP en la URL: `https://mcp.tudominio.com/mcp`
4. Incluye el header `X-API-Key: <tu_token>` en cada petición.

### Endpoints del MCP

| Endpoint | Método | Auth | Descripción |
|---|---|---|---|
| `/health` | GET | Sin auth | Health check |
| `/mcp` | POST | X-API-Key + IP Whitelist | Endpoint MCP streamable-http |

---

## Tools disponibles

### `list_domains`
Obtiene el listado completo de dominios en tu cuenta NEUBOX.

### `register_domain`
Registra dominios nuevos. Requiere `domains` (array) y `regperiod` (array de enteros).

### `renew_domain`
Renueva dominios existentes. Requiere `domains` (array) y `renewperiod` (array de enteros).

### `search_domains`
Busca disponibilidad de un dominio en múltiples TLDs. Requiere `domain` (string) y `tlds` (array).

---

## Estructura del proyecto

```
neubox-mcp/
├── main.py                 # Entrada: Starlette app + middlewares + MCP
├── neubox_client.py        # Cliente HTTP async para NEUBOX
├── middleware.py           # IP Whitelist, API Key, Rate Limiting
├── tools.py                # 4 tools MCP + schemas Pydantic
├── config.py               # Variables de entorno
├── requirements.txt        # Dependencias
├── Dockerfile              # Imagen Docker
├── .env.example            # Template de variables
├── SPEC.md                 # Especificación técnica
├── N8N_AGENT_GUIDE.md      # System prompt para N8N
└── README.md               # Este archivo
```

---

## Notas importantes

- La API de NEUBOX tiene un límite de **10 peticiones por minuto** en el endpoint de búsqueda.
- Las operaciones de registro y renovación **descuentan saldo real** de la cuenta.
- Si `IP_WHITELIST` está vacía, se permiten todas las IPs (solo para desarrollo).
- El rate limiting se comparte entre todas las IPs por igual (sin distinción local/externo).
- Nunca compartas tus credenciales ni el `MCP_API_KEY` con personas no autorizadas.