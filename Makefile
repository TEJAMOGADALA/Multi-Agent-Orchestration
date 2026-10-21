# ============================================================
# DevAgent — Multi-Agent Orchestration System
# Makefile — Developer shortcuts for common operations
# ============================================================
# Usage:
#   make install     — Create venv and install all dependencies
#   make run         — Start the FastAPI dev server
#   make test        — Run the test suite
#   make lint        — Lint and format code
#   make mcp-server  — Start the DevAgent MCP server
#
# Windows Users:
#   Install make via: scoop install make  OR  choco install make
#   Alternatively, run the commands directly from each target.
# ============================================================

# --- Configuration ---
PYTHON       := python
VENV_DIR     := .venv
PIP          := $(VENV_DIR)/Scripts/pip
PYTHON_VENV  := $(VENV_DIR)/Scripts/python
UVICORN      := $(VENV_DIR)/Scripts/uvicorn
PYTEST       := $(VENV_DIR)/Scripts/pytest
RUFF         := $(VENV_DIR)/Scripts/ruff
MYPY         := $(VENV_DIR)/Scripts/mypy
APP_MODULE   := src.api.main:create_app
MCP_MODULE   := src.mcp.server:run

# Default target
.DEFAULT_GOAL := help

# ============================================================
# HELP — Lists all available commands
# ============================================================
.PHONY: help
help: ## Show this help message
	@echo.
	@echo  DevAgent - Available Commands:
	@echo  ==============================
	@echo.
	@findstr /R "^[a-zA-Z_-]*:.*##" Makefile
	@echo.

# ============================================================
# SETUP & INSTALLATION
# ============================================================
.PHONY: install install-dev install-test clean

install: ## Create venv and install core dependencies
	$(PYTHON) -m venv $(VENV_DIR)
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -e .
	@echo.
	@echo [OK] Core dependencies installed. Activate venv:
	@echo      .venv\Scripts\activate

install-dev: ## Install with dev tools (linting, typing, debugging)
	$(PYTHON) -m venv $(VENV_DIR)
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -e ".[dev]"
	@echo.
	@echo [OK] Dev dependencies installed.

install-test: ## Install with test dependencies
	$(PYTHON) -m venv $(VENV_DIR)
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -e ".[test]"
	@echo.
	@echo [OK] Test dependencies installed.

install-all: ## Install everything (core + dev + test + docs)
	$(PYTHON) -m venv $(VENV_DIR)
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -e ".[dev,test,docs]"
	@echo.
	@echo [OK] All dependencies installed.

clean: ## Remove venv, caches, and build artifacts
	@if exist $(VENV_DIR) rmdir /s /q $(VENV_DIR)
	@if exist build rmdir /s /q build
	@if exist dist rmdir /s /q dist
	@if exist *.egg-info rmdir /s /q *.egg-info
	@if exist .pytest_cache rmdir /s /q .pytest_cache
	@if exist .mypy_cache rmdir /s /q .mypy_cache
	@if exist .ruff_cache rmdir /s /q .ruff_cache
	@if exist htmlcov rmdir /s /q htmlcov
	@for /r %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"
	@echo [OK] Cleaned all artifacts.

# ============================================================
# RUNNING THE APPLICATION
# ============================================================
.PHONY: run run-prod mcp-server

run: ## Start FastAPI dev server (auto-reload)
	$(UVICORN) $(APP_MODULE) --factory --host 0.0.0.0 --port 8000 --reload --log-level info
	@echo.
	@echo [SERVER] Running at http://localhost:8000
	@echo [DOCS]   Swagger UI at http://localhost:8000/docs

run-prod: ## Start FastAPI production server (no reload, multiple workers)
	$(UVICORN) $(APP_MODULE) --factory --host 0.0.0.0 --port 8000 --workers 4 --log-level warning

mcp-server: ## Start DevAgent MCP server
	$(PYTHON_VENV) -m src.mcp.server
	@echo.
	@echo [MCP] DevAgent MCP server running on port 8001

# ============================================================
# CODE QUALITY
# ============================================================
.PHONY: lint format check type-check

lint: ## Run ruff linter (check mode — no changes)
	$(RUFF) check src/ tests/
	@echo [OK] Lint passed.

format: ## Auto-format code with ruff
	$(RUFF) format src/ tests/
	$(RUFF) check --fix src/ tests/
	@echo [OK] Code formatted.

check: ## Run all checks (lint + type-check)
	$(RUFF) check src/ tests/
	$(MYPY) src/
	@echo [OK] All checks passed.

type-check: ## Run mypy type checking
	$(MYPY) src/
	@echo [OK] Type check passed.

# ============================================================
# TESTING
# ============================================================
.PHONY: test test-unit test-integration test-cov test-verbose

test: ## Run all tests (excluding slow)
	$(PYTEST)

test-unit: ## Run unit tests only
	$(PYTEST) tests/unit/ -m unit

test-integration: ## Run integration tests (requires Docker services)
	$(PYTEST) tests/integration/ -m integration

test-cov: ## Run tests with coverage report
	$(PYTEST) --cov=src --cov-report=html --cov-report=term-missing
	@echo.
	@echo [COVERAGE] HTML report: htmlcov/index.html

test-verbose: ## Run tests with verbose output
	$(PYTEST) -vvs --tb=long

test-all: ## Run ALL tests including slow ones
	$(PYTEST) -m ""

# ============================================================
# DATABASE
# ============================================================
.PHONY: db-migrate db-upgrade db-downgrade db-seed

db-migrate: ## Create a new Alembic migration
	$(PYTHON_VENV) -m alembic revision --autogenerate -m "$(msg)"

db-upgrade: ## Apply all pending migrations
	$(PYTHON_VENV) -m alembic upgrade head

db-downgrade: ## Rollback last migration
	$(PYTHON_VENV) -m alembic downgrade -1

db-seed: ## Seed the database with sample data
	$(PYTHON_VENV) scripts/seed_db.py

# ============================================================
# DOCKER
# ============================================================
.PHONY: docker-up docker-down docker-build docker-logs

docker-up: ## Start all services (PostgreSQL, Redis, API)
	docker compose up -d
	@echo [DOCKER] Services started. API at http://localhost:8000

docker-down: ## Stop all services
	docker compose down
	@echo [DOCKER] Services stopped.

docker-build: ## Build Docker images
	docker compose build
	@echo [DOCKER] Images built.

docker-logs: ## Tail logs from all services
	docker compose logs -f

docker-fresh: ## Full reset: stop, remove volumes, rebuild, start
	docker compose down -v
	docker compose build --no-cache
	docker compose up -d
	@echo [DOCKER] Fresh start complete.

# ============================================================
# MCP TOOLS
# ============================================================
.PHONY: mcp-discover mcp-list

mcp-discover: ## Discover all available MCP tools from configured servers
	$(PYTHON_VENV) -m src.mcp.discovery

mcp-list: ## List all registered tools (internal + MCP)
	$(PYTHON_VENV) -c "from src.tools import list_all_tools; list_all_tools()"

# ============================================================
# UTILITIES
# ============================================================
.PHONY: env-check tree

env-check: ## Validate .env file has all required variables
	$(PYTHON_VENV) -c "from src.config.settings import get_settings; s = get_settings(); print('[OK] Settings loaded:', s.APP_NAME)"

tree: ## Show project directory structure
	@tree /F /A src
