.PHONY: help install test lint format docker-build docker-test clean

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies with Poetry
	poetry install

test:  ## Run tests with coverage
	poetry run pytest -v --cov

test-quick:  ## Run tests without coverage
	poetry run pytest -v

lint:  ## Run all linters
	poetry run ruff check .
	poetry run mypy app/

format:  ## Format code with ruff
	poetry run ruff check --fix .
	poetry run ruff format .

docker-build:  ## Build production Docker image
	docker build -t obsidian-agent-mcp .

docker-build-dev:  ## Build development Docker image
	docker build -f Dockerfile.dev -t obsidian-agent-dev .

docker-test:  ## Run tests in Docker
	docker run --rm obsidian-agent-dev poetry run pytest -v

docker-lint:  ## Run linters in Docker
	docker run --rm obsidian-agent-dev poetry run ruff check .

clean:  ## Clean up build artifacts
	rm -rf .pytest_cache .ruff_cache htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
