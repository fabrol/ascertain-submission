.PHONY: setup env up upf build down logs test test-docker test-cleanup prod prod-logs help

# Default target
help:
	@echo "Available commands:"
	@echo "  make setup       - Set up the development environment (first time setup)"
	@echo "  make env         - Set up environment variables from development template"
	@echo "  make up          - Start the application in Docker with hot-reloading"
	@echo "  make build       - Build and start the application in Docker with hot-reloading"
	@echo "  make upf         - Start the application in Docker foreground with logs"
	@echo "  make down        - Stop Docker services"
	@echo "  make logs        - View Docker logs"
	@echo "  make test        - Run tests locally (starts PostgreSQL in Docker)"
	@echo "  make test-docker - Run tests in Docker"
	@echo "  make test-cleanup - Stop PostgreSQL container after tests"
	@echo "  make prod        - Start the application in production mode"
	@echo "  make prod-logs   - View production logs"

# Setup development environment
setup:
	@echo "Setting up development environment..."
	@if ! command -v uv &> /dev/null; then \
		echo "Installing UV package manager..."; \
		pip install uv; \
	fi
	@if [ ! -d ".venv" ]; then \
		echo "Creating Python virtual environment with UV..."; \
		if ! uv venv .venv; then \
			echo "Error: Failed to create virtual environment."; \
			echo "This project requires Python as specified in pyproject.toml."; \
			echo "Please install a compatible Python version using pyenv or your system package manager."; \
			exit 1; \
		fi; \
	fi
	@echo "Installing dependencies with UV..."
	@uv pip install -e ".[dev]"
	@if [ ! -f ".env" ]; then \
		echo "Setting up environment variables..."; \
		cp .env.development .env; \
		echo "\033[0;33mNOTE: Please edit .env file to add your API keys (especially OPENAI_API_KEY)\033[0m"; \
	fi
	@echo "Setup complete! Run 'make test' to run tests and 'make up' to start the application in Docker"

# Set up environment variables
env:
	@if [ -f ".env" ]; then \
		echo "Environment file already exists. Do you want to overwrite it? (y/n)"; \
		read answer; \
		if [ "$$answer" = "y" ]; then \
			cp .env.development .env; \
			echo "Environment file has been reset to development template."; \
			echo "\033[0;33mNOTE: Please edit .env file to add your API keys (especially OPENAI_API_KEY)\033[0m"; \
		else \
			echo "Operation cancelled."; \
		fi; \
	else \
		cp .env.development .env; \
		echo "Environment file created from development template."; \
		echo "\033[0;33mNOTE: Please edit .env file to add your API keys (especially OPENAI_API_KEY)\033[0m"; \
	fi

# Start services in Docker with hot-reloading
up:
	docker-compose up -d

# Build and start services in Docker with hot-reloading
build:
	docker-compose up -d --build

# Start services in Docker in foreground (for debugging)
upf:
	docker-compose up

# Stop all Docker services
down:
	@echo "Stopping all services..."
	@docker-compose down
	@echo "All services stopped"

# View logs
logs:
	docker-compose logs -f

# Run tests locally
test:
	@echo "Starting PostgreSQL for tests..."
	@docker-compose up -d postgres
	@echo "Waiting for PostgreSQL to be ready..."
	@for i in {1..10}; do \
		if docker exec $$(docker-compose ps -q postgres 2>/dev/null) pg_isready -U postgres -h localhost &>/dev/null; then \
			echo "PostgreSQL is ready."; \
			break; \
		fi; \
		echo "Waiting for PostgreSQL..." && sleep 2; \
	done
	@echo "Running tests..."
	@uv run -m pytest

# Run tests in Docker
test-docker:
	@echo "Starting services for Docker tests..."
	@docker-compose up -d postgres
	@echo "Running tests in Docker..."
	@docker-compose run --rm app pytest

# Clean up after tests
test-cleanup:
	@echo "Stopping PostgreSQL container..."
	@docker-compose stop postgres
	@echo "PostgreSQL container stopped"

# Start in production mode
prod:
	docker-compose -f docker-compose.prod.yml up -d

# View production logs
prod-logs:
	docker-compose -f docker-compose.prod.yml logs -f 