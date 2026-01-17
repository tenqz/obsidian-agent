.PHONY: help test test-quick lint format check docker-build docker-up docker-down docker-logs clean

# Docker command template for running commands in container
DOCKER_RUN = docker run --rm -v "$$(pwd):/app" -w /app python:3.12-slim bash -c "pip install -q poetry==1.8.0 && poetry install -q &&

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

test:  ## Run tests with coverage in Docker
	$(DOCKER_RUN) poetry run pytest -v --cov"

test-quick:  ## Run tests without coverage in Docker
	$(DOCKER_RUN) poetry run pytest -v"

lint:  ## Run all linters (ruff + mypy) in Docker
	$(DOCKER_RUN) poetry run ruff check . && poetry run mypy app/"

format:  ## Format code with ruff in Docker
	$(DOCKER_RUN) poetry run ruff check --fix . && poetry run ruff format ."

check:  ## Run all checks (linters + tests) in Docker
	@echo "=== Running all checks in Docker ==="
	$(DOCKER_RUN) \
		echo '=== Running ruff ===' && \
		poetry run ruff check . && \
		echo '=== Running mypy ===' && \
		poetry run mypy app/ && \
		echo '=== Running tests ===' && \
		poetry run pytest -v --cov && \
		echo '=== All checks passed! ==='"

docker-build:  ## Build production Docker image
	docker build -t obsidian-agent-mcp .

docker-up:  ## Start services with docker-compose
	docker compose up -d

docker-down:  ## Stop services with docker-compose
	docker compose down

docker-logs:  ## View docker-compose logs
	docker compose logs -f

clean:  ## Clean up build artifacts
	rm -rf .pytest_cache .ruff_cache htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
