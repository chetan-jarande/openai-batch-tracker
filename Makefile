
# Use the project name for containers, networks, etc.
# This prevents conflicts if you have other projects.
PROJECT_NAME = OPENAI_BATCH_TRACKER

# Default command when you just type "make"
.DEFAULT_GOAL := help

# Build the docker images for the services
build:
	docker-compose -p $(PROJECT_NAME) build

# Start the services in detached mode
up:
	docker-compose -p $(PROJECT_NAME) up -d

# Stop and remove the services, networks, and volumes
down:
	docker-compose -p $(PROJECT_NAME) down

# Restart the services
restart: down up

# View the logs from the services
logs:
	docker-compose -p $(PROJECT_NAME) logs -f

# Access a shell inside the running app container
shell:
	docker-compose -p $(PROJECT_NAME) exec app /bin/bash

# Show this help message
help:
	@echo "Usage: make [command]"
	@echo "Commands:"
	@echo "  build    Build the Docker images"
	@echo "  up       Start the services in the background"
	@echo "  down     Stop and remove the services"
	@echo "  restart  Restart the services"
	@echo "  logs     Follow the service logs"
	@echo "  shell    Access a shell in the app container"

.PHONY: build up down restart logs shell help
