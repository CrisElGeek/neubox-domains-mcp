# Manual de entorno de desarrollo — neubox-mcp

## Prerrequisitos

- Docker >= 24.0
- Docker Compose v2 (plugin incluido en Docker)
- `make` (opcional, pero recomendado)
- `curl` para healthchecks

---

## Primera vez: setup

### 1. Crear archivo `.env`

```bash
cp .env.example .env
```

Editar `.env` con valores reales:

```env
NEUBOX_API_KEY=tu_api_key_real
NEUBOX_API_SECRET=tu_api_secret_real
NEUBOX_USER_EMAIL=tu@email.com
MCP_API_KEY=genera_un_token_seguro_aqui

# Docker
IMAGE_TAG=neubox-mcp:1.0
MCP_HOST_PORT=8000
```

> **Importante:** `.env` está en `.dockerignore` y no se incluye en la imagen.
> Los secrets se inyectan en runtime via `env_file` en docker-compose.

### 2. Construir y arrancar

```bash
make up
# o sin make:
docker compose up -d --build
```

### 3. Verificar que está corriendo

```bash
make ps
make health
# o:
docker compose ps
curl http://localhost:8000/health
```

Respuesta esperada:
```json
{"status": "ok", "service": "neubox-mcp", "version": "1.0"}
```

---

## Comandos diarios

| Acción | Make | Docker Compose |
|---|---|---|
| Arrancar (dev) | `make up` | `docker compose up -d --build` |
| Detener | `make down` | `docker compose down` |
| Reiniciar | `make restart` | `docker compose restart` |
| Ver logs | `make logs` | `docker compose logs -f --tail=100` |
| Estado | `make ps` | `docker compose ps` |
| Shell en contenedor | `make shell` | `docker compose exec app /bin/bash` |
| Health check | `make health` | `curl http://localhost:8000/health` |
| Limpiar todo | `make clean` | `docker compose down -v --rmi local` |

---

## Modo desarrollo (hot-reload)

El archivo `docker-compose.override.yml` se aplica automáticamente al hacer `docker compose up` y proporciona:

- **Volume mount** de `./` a `/app` (cambios en vivo)
- **Uvicorn `--reload`** (reinicio automático al guardar)
- **LOG_LEVEL=DEBUG** (logs detallados)
- **IP_WHITELIST vacía** (permite todas las IPs en dev)

Para forzar modo producción localmente (sin override):

```bash
docker compose -f docker-compose.yml up -d --build
```

---

## Construcción de imagen para producción

### Build de imagen

```bash
make build
# o:
docker compose build
```

La imagen se taggea como `neubox-mcp:1.0` (configurable via `IMAGE_TAG` en `.env`).

### Verificar imagen construida

```bash
docker images neubox-mcp
docker run --rm neubox-mcp:1.0 python -c "import mcp, httpx, starlette, uvicorn; print('deps ok')"
```

---

## Exportar imagen para despliegue en servidor

### Método: docker save/load (sin registry)

**En local:**

```bash
make export-image
# Genera: neubox-mcp-1.0.tar.gz
```

**Transportar al servidor:**

```bash
scp neubox-mcp-1.0.tar.gz usuario@servidor:/opt/
```

**En el servidor (importar):**

```bash
docker load < /opt/neubox-mcp-1.0.tar.gz
# Verificar:
docker images neubox-mcp
```

### Despliegue en servidor de producción

**Opción A: docker run directo**

```bash
# Crear .env en el servidor
nano /opt/neubox-mcp/.env
# (copiar contenidos de .env.example con valores de producción)

# Arrancar
docker run -d \
  --name neubox-mcp \
  --restart unless-stopped \
  -p 8000:8000 \
  --env-file /opt/neubox-mcp/.env \
  neubox-mcp:1.0

# Verificar
docker ps
docker logs neubox-mcp --tail=50
curl http://localhost:8000/health
```

**Opción B: docker compose en servidor (sin override)**

```bash
# Copiar solo docker-compose.yml y .env al servidor
# En el servidor:
docker compose -f docker-compose.yml up -d
```

### Actualizar imagen en producción

```bash
# Local: reconstruir y exportar nueva versión
make build
make export-image

# Transportar
scp neubox-mcp-1.0.tar.gz usuario@servidor:/opt/

# Servidor: importar y reiniciar
docker load < /opt/neubox-mcp-1.0.tar.gz
docker stop neubox-mcp && docker rm neubox-mcp
docker run -d \
  --name neubox-mcp \
  --restart unless-stopped \
  -p 8000:8000 \
  --env-file /opt/neubox-mcp/.env \
  neubox-mcp:1.0
```

---

## Apache reverse proxy (recomendado en producción)

```apache
<VirtualHost *:443>
    ServerName mcp.tudominio.com

    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/mcp.tudominio.com/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/mcp.tudominio.com/privkey.pem

    ProxyPreserveHost On
    ProxyPass / http://localhost:8000/
    ProxyPassReverse / http://localhost:8000/
</VirtualHost>
```

```bash
a2ensite mcp.tudominio.com
apachectl configtest && systemctl reload apache2
```

---

## Flujo completo resumido

```bash
# 1. LOCAL: Desarrollar
make up                           # arrancar en modo dev con hot-reload
# ... editar código, ver cambios en vivo ...

# 2. LOCAL: Construir imagen de producción
make build

# 3. LOCAL: Exportar
make export-image                 # → neubox-mcp-1.0.tar.gz

# 4. TRANSPORTAR
scp neubox-mcp-1.0.tar.gz usuario@servidor:/opt/

# 5. SERVIDOR: Importar
docker load < /opt/neubox-mcp-1.0.tar.gz

# 6. SERVIDOR: Desplegar
docker run -d --name neubox-mcp --restart unless-stopped \
  -p 8000:8000 --env-file /opt/neubox-mcp/.env neubox-mcp:1.0

# 7. SERVIDOR: Verificar
curl http://localhost:8000/health
```

---

## Troubleshooting

### El contenedor no arranca (salida inmediata)

```
ERROR: Variable de entorno requerida 'NEUBOX_API_KEY' no está definida
```

**Causa:** Falta una variable requerida en `.env`.
**Fix:** Verificar que `.env` existe y tiene todas las variables requeridas:

```bash
cat .env | grep -v "^#" | grep -v "^$"
```

Revisar que todas estas tengan valor:
- `NEUBOX_API_KEY`
- `NEUBOX_API_SECRET`
- `NEUBOX_USER_EMAIL`
- `MCP_API_KEY`

### Healthcheck falla

```bash
docker compose ps     # ver estado de healthcheck
docker compose logs --tail=50 app
docker compose exec app curl -f http://localhost:8000/health
```

### Puerto 8000 ya en uso

```bash
# Ver qué usa el puerto
sudo lnetstat -tlnp | grep 8000    # o: ss -tlnp | grep 8000

# Cambiar puerto host en .env
echo "MCP_HOST_PORT=8001" >> .env
make down && make up
```

### Imagen muy pesada

```bash
docker images neubox-mcp
docker history neubox-mcp:1.0 --no-trunc
```

### Limpiar estado de Docker

```bash
make clean                        # borra contenedores + imágenes locales
docker system prune -f            # limpia huérfanos
```

### Recuperar estado de red Docker corrupto

```bash
docker compose down
docker network prune -f
docker compose up -d --build
```

---

## Estructura de archivos Docker

```
neubox-mcp/
├── Dockerfile                    # Imagen de producción
├── .dockerignore                 # Exclusiones de build
├── docker-compose.yml            # Definición base del servicio
├── docker-compose.override.yml   # Override de desarrollo (hot-reload)
├── .env.example                  # Template de variables
├── .env                          # Variables reales (NO commitear)
├── Makefile                      # Comandos快捷os
├── DEV_ENV_MANUAL.md             # Este manual
└── README-docker.md              # Resumen Docker
```

---

## Notas de seguridad

- El contenedor corre como usuario **non-root** (`appuser`)
- `.env` está en `.dockerignore` — los secrets no se embeben en la imagen
- `.env` se inyecta en runtime via `env_file` — no se persiste en capas de imagen
- En producción, usar un reverse proxy (Apache/Nginx) con SSL
- El token `MCP_API_KEY` debe generarse de forma segura: `openssl rand -hex 32`