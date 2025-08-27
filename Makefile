
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

dev: venv
	"$(VENV_ROOT)/bin/pip" install -e '.[dev]'

test: dev
	"$(VENV_ROOT)/bin/pytest" -vvv

build: venv
	"$(VENV_ROOT)/bin/pip" install --upgrade build
	rm -rf ./dist/
	"$(VENV_ROOT)/bin/python" -m build --wheel --outdir ./dist/

run:
	"$(VENV_ROOT)/bin/python" -m 'app.main'


# Build the docker images for the services
docker-build:
	docker-compose -p $(PROJECT_NAME) build --no-cache

# Start the services in detached mode
docker-up:
	docker-compose -p $(PROJECT_NAME) up -d

# Stop and remove the services, networks, and volumes
docker-down:
	docker-compose -p $(PROJECT_NAME) down

# Restart the services
docker-restart: down up

# View the logs from the services
docker-logs:
	docker-compose -p $(PROJECT_NAME) logs -f

# Access a shell inside the running app container
docker-shell:
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
