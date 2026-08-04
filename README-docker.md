# Docker — neubox-mcp

## Resumen

Stack single-service para el servidor MCP de NEUBOX. Imagen Python 3.12-slim con non-root user y healthcheck.

## Arranque rápido

```bash
cp .env.example .env
# Editar .env con tus credenciales
make up
make health
```

## Comandos principales

| Comando | Acción |
|---|---|
| `make build` | Construir imagen |
| `make up` | Construir y arrancar (dev con hot-reload) |
| `make down` | Detener |
| `make logs` | Ver logs en vivo |
| `make ps` | Estado de contenedores |
| `make shell` | Shell dentro del contenedor |
| `make health` | Health check |
| `make export-image` | Exportar imagen a `.tar.gz` |
| `make import-image` | Importar imagen desde `.tar.gz` |
| `make clean` | Limpiar contenedores e imágenes |

## Flujo de despliegue a producción

```bash
# 1. Local: construir y exportar
make build && make export-image

# 2. Transportar
scp neubox-mcp-1.0.tar.gz usuario@servidor:/opt/

# 3. Servidor: importar y desplegar
docker load < /opt/neubox-mcp-1.0.tar.gz
docker run -d --name neubox-mcp --restart unless-stopped \
  -p 8000:8000 --env-file .env neubox-mcp:1.0
```

## Archivos

- `Dockerfile` — imagen de producción (non-root, healthcheck)
- `docker-compose.yml` — servicio base
- `docker-compose.override.yml` — hot-reload para dev
- `.dockerignore` — exclusiones de build

Ver `DEV_ENV_MANUAL.md` para documentación completa.