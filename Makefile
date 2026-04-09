# Agam Automation Hub — One-command setup & operations
# Usage: make setup | make run | make web | make test

.PHONY: setup install run web test lint clean help

PYTHON := python3
PIP    := pip3
VENV   := venv

help:
	@echo ""
	@echo "  Agam Automation Hub"
	@echo "  ─────────────────────────────────────────────"
	@echo "  make setup       Full first-time setup (venv + deps + env)"
	@echo "  make install     Install Python + frontend deps only"
	@echo "  make run         Run daily job discovery (CLI)"
	@echo "  make web         Start backend + React frontend"
	@echo "  make test        Run all tests"
	@echo "  make lint        Run ruff linter"
	@echo "  make clean       Remove venv, caches, output/"
	@echo ""

setup:
	@echo "▶ Creating virtual environment..."
	$(PYTHON) -m venv $(VENV)
	@echo "▶ Installing Python dependencies..."
	$(VENV)/bin/pip install --upgrade pip -q
	$(VENV)/bin/pip install -r requirements.txt -q
	@echo "▶ Installing frontend dependencies..."
	cd frontend && npm install --silent
	@echo "▶ Creating .env from template (edit it before running)..."
	@cp -n .env.example .env || echo "   .env already exists — skipping"
	@echo "▶ Creating output directories..."
	@mkdir -p output/jobs output/linkedin/queue output/briefings data
	@echo ""
	@echo "✅ Setup complete!"
	@echo "   Next: edit .env → add ANTHROPIC_API_KEY"
	@echo "   Then: make web   (or: make run)"
	@echo ""

install:
	$(VENV)/bin/pip install -r requirements.txt -q
	cd frontend && npm install --silent

run:
	$(VENV)/bin/python run.py --jobs

web:
	$(VENV)/bin/python run_web.py --mode both

backend:
	$(VENV)/bin/python run_web.py --mode backend

frontend-dev:
	cd frontend && npm run dev

test:
	$(VENV)/bin/pytest tests/ -v

lint:
	$(VENV)/bin/ruff check src/ tests/

clean:
	rm -rf $(VENV) __pycache__ .pytest_cache .ruff_cache
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
