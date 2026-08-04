IMAGE_TAG   ?= neubox-mcp:1.0
EXPORT_NAME ?= neubox-mcp-1.0.tar.gz

.PHONY: build up down restart logs ps shell health clean export-image import-image

build:
	docker compose build

up:
	docker compose up -d --build

down:
	docker compose down

restart:
	docker compose restart

logs:
	docker compose logs -f --tail=100

ps:
	docker compose ps

shell:
	docker compose exec app /bin/bash

health:
	curl -sf http://localhost:8000/health && echo "" || echo "Service unhealthy"

clean:
	docker compose down -v --rmi local

export-image:
	docker save $(IMAGE_TAG) | gzip > $(EXPORT_NAME)
	@echo "Imagen exportada: $(EXPORT_NAME)"

import-image:
	docker load < $(EXPORT_NAME)
	@echo "Imagen importada: $(IMAGE_TAG)"