PROJECT_NAME = openai-batch-tracker
# Default command when you just type "make"
.DEFAULT_GOAL := help

PYTHON_VERSION=3.13.3
VENV_ROOT=./.venv

ifeq ($(shell command -v 'pyenv'),)
	PYENV_BIN=$(HOME)/.pyenv/bin/pyenv
else
	PYENV_BIN=pyenv
endif

export CONF_ENV?=local

venv:
	@echo "Using pyenv from '$(PYENV_BIN)'"
	find . -type d -name '*__pycache__*' | xargs rm -rf
	"$(PYENV_BIN)" install --skip-existing "$(PYTHON_VERSION)"
	"$(PYENV_BIN)" local "$(PYTHON_VERSION)"
	"$(PYENV_BIN)" exec python -m venv --clear --upgrade-deps "$(VENV_ROOT)"
	"$(PYENV_BIN)" local --unset

deps: venv
	"$(VENV_ROOT)/bin/pip" install -e '.'

dev: venv
	"$(VENV_ROOT)/bin/pip" install -e '.[dev]'

test: dev
	"$(VENV_ROOT)/bin/pytest" -vvv

build: venv
	"$(VENV_ROOT)/bin/pip" install --upgrade build
	rm -rf ./dist/
	"$(VENV_ROOT)/bin/python" -m build --wheel --outdir ./dist/

# Generic run command for use inside Docker containers
run:
	python -m app.main

# Command for local venv usage
run-local:
	"$(VENV_ROOT)/bin/python" -m 'app.main'

# Build the docker images for the services, using cache by default
docker-build:
	docker-compose -p $(PROJECT_NAME) --profile prod build

# Build the docker images without using cache
docker-build-fresh:
	docker-compose -p $(PROJECT_NAME) --profile prod build --no-cache

# Build the development docker image
docker-build-dev:
	docker-compose -p $(PROJECT_NAME) --profile dev build

# Start the services in detached mode
docker-up:
	docker-compose -p $(PROJECT_NAME) --profile prod up -d

# Start the development service in detached mode
docker-up-dev:
	docker-compose -p $(PROJECT_NAME) --profile dev up -d

# Stop and remove the services, networks, and volumes for a clean slate
docker-down:
	docker-compose -p $(PROJECT_NAME) down --volumes

# Restart the services
docker-restart: docker-down docker-up

# View the logs from the services
docker-logs:
	docker-compose -p $(PROJECT_NAME) --profile prod logs -f

# View the logs from the development service
docker-logs-dev:
	docker-compose -p $(PROJECT_NAME) --profile dev logs -f

# Access a shell inside the running app container
docker-shell:
	docker-compose -p $(PROJECT_NAME) --profile prod exec app-prod /bin/bash

# Access a shell inside the running development app container
docker-shell-dev:
	docker-compose -p $(PROJECT_NAME) --profile dev exec app-dev /bin/bash

# Show this help message
help:
	@echo "Usage: make [command]"
	@echo "Production Commands:"
	@echo "  docker-build        Build the production Docker image (uses cache)"
	@echo "  docker-build-fresh  Build the production Docker image from scratch"
	@echo "  docker-up           Start the production service in the background"
	@echo "  docker-down         Stop and remove all services and volumes"
	@echo "  docker-restart      Restart the production service"
	@echo "  docker-logs         Follow the production service logs"
	@echo "  docker-shell        Access a shell in the production app container"
	@echo ""
	@echo "Development Commands:"
	@echo "  docker-build-dev    Build the development Docker image"
	@echo "  docker-up-dev       Start the development service in the background"
	@echo "  docker-logs-dev     Follow the development service logs"
	@echo "  docker-shell-dev    Access a shell in the development app container"
	@echo ""
	@echo "Local Commands:"
	@echo "  dev                 Create a venv and install all dependencies"
	@echo "  run-local           Run the application locally (uses logic in main.py)"

.PHONY: docker-build docker-build-fresh docker-build-dev docker-up docker-up-dev docker-down docker-restart docker-logs docker-logs-dev docker-shell docker-shell-dev help run run-local
