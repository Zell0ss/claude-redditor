.PHONY: help install dev test clean cli scan scan-hn compare config cmonitor

# Python interpreter (uses venv if available)
PYTHON := $(shell if [ -d ".venv" ]; then echo ".venv/bin/python"; else echo "python3"; fi)
CLI := $(shell if [ -d ".venv" ]; then echo ".venv/bin/activate && ./reddit-analyzer"; else echo "./reddit-analyzer"; fi)

# Default target
help:
	@echo "Reddit Signal/Noise Analyzer - Makefile Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install    - Install dependencies"
	@echo "  make dev        - Install in development mode"
	@echo ""
	@echo "CLI Commands:"
	@echo "  make scan       - Quick scan of ClaudeAI (5 posts)"
	@echo "  make scan-hn    - Quick scan of HackerNews (5 posts)"
	@echo "  make compare    - Compare all subreddits (10 posts each)"
	@echo "  make config     - Show current configuration"
	@echo ""
	@echo "Testing:"
	@echo "  make test       - Run all test scripts"
	@echo "  make test-scraper   - Test scraper only"
	@echo "  make test-classifier - Test classifier only"
	@echo "  make test-analyzer  - Test analyzer only"
	@echo "  make test-e2e       - Test end-to-end pipeline"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean      - Remove generated files and caches"

# Installation
install:
	@echo "Installing dependencies..."
	pip install -r requirements.txt 2>/dev/null || pip install requests feedparser praw anthropic typer rich pandas pydantic pydantic-settings

dev:
	@echo "Installing in development mode..."
	pip install -e .


# Quick CLI commands (using venv)
scan:
	@echo "Running quick scan of r/ClaudeAI..."
	@bash -c "source .venv/bin/activate && ./reddit-analyzer scan ClaudeAI --limit 5 --no-details"

scan-hn:
	@echo "Running quick scan of HackerNews..."
	@bash -c "source .venv/bin/activate && ./reddit-analyzer scan-hn --limit 5"

compare:
	@echo "Comparing all configured subreddits..."
	@bash -c "source .venv/bin/activate && ./reddit-analyzer compare --limit 10"

config:
	@bash -c "source .venv/bin/activate && ./reddit-analyzer config"

# Testing (using venv)
test:
	@echo "Running all tests..."
	@$(PYTHON) test_scraper.py
	@$(PYTHON) test_classifier.py
	@$(PYTHON) test_analyzer.py
	@$(PYTHON) test_e2e.py

test-scraper:
	@echo "Testing scraper..."
	@$(PYTHON) test_scraper.py

test-classifier:
	@echo "Testing classifier..."
	@$(PYTHON) test_classifier.py

test-analyzer:
	@echo "Testing analyzer..."
	@$(PYTHON) test_analyzer.py

test-e2e:
	@echo "Testing end-to-end pipeline..."
	@$(PYTHON) test_e2e.py

test-e2e-compare:
	@echo "Testing multi-subreddit comparison..."
	@$(PYTHON) test_e2e.py compare

# Cleanup
clean:
	@echo "Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	rm -rf outputs/cache/* 2>/dev/null || true
	rm -rf outputs/classifications/* 2>/dev/null || true
	@echo "✓ Cleanup complete"

clean-all: clean
	@echo "Deep cleaning (includes reports)..."
	rm -rf outputs/ 2>/dev/null || true
	@echo "✓ Deep cleanup complete"

cmonitor:
	@echo "Monitoring claude consumption..."
	claude-monitor --plan pro