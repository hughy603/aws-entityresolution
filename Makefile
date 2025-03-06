.PHONY: help install dev lint fix fix-all fix-mypy fix-ruff check check-full test test-cov clean docs build publish

# Default target
help:
	@echo "Available commands:"
	@echo "  make install      Install production dependencies"
	@echo "  make dev          Install development dependencies"
	@echo "  make lint         Run optimized pre-commit checks (fast)"
	@echo "  make fix          Run auto-fixes for common linting issues"
	@echo "  make fix-all      Run all fix scripts and linting (comprehensive)"
	@echo "  make fix-mypy     Run only mypy fixes"
	@echo "  make fix-ruff     Run only ruff fixes"
	@echo "  make check        Run pre-commit only on changed files"
	@echo "  make check-full   Run full pre-commit checks on all files (slow)"
	@echo "  make test         Run tests without coverage"
	@echo "  make test-cov     Run tests with coverage"
	@echo "  make clean        Clean up build artifacts"
	@echo "  make docs         Generate documentation"
	@echo "  make build        Build package"
	@echo "  make publish      Publish package to PyPI"

# Install production dependencies
install:
	poetry install --no-dev

# Install development dependencies
dev:
	poetry install

# Run optimized pre-commit checks (faster)
lint:
	pre-commit run trailing-whitespace end-of-file-fixer check-yaml check-json check-merge-conflict debug-statements ruff ruff-format

# Run auto-fixes for common linting issues
fix:
	python scripts/fix_all.py

# Run all fix scripts and linting (comprehensive)
fix-all: check

# Run mypy fixes
fix-mypy:
	python scripts/fix_mypy_issues.py

# Run ruff fixes
fix-ruff:
	python scripts/fix_ruff.py

# Run pre-commit on changed files
check:
	pre-commit run

# Run full pre-commit checks on all files (slow)
check-full:
	pre-commit run --all-files

# Run tests without coverage
test:
	poetry run pytest -xvs

# Run tests with coverage
test-cov:
	poetry run pytest --cov=aws_entity_resolution --cov-report=term --cov-report=html

# Clean up build artifacts
clean:
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/
	rm -rf .ruff_cache/
	rm -rf .mypy_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +

# Generate documentation
docs:
	@echo "Documentation generation not yet implemented"

# Build package
build: clean
	poetry build

# Publish package to PyPI
publish: build
	poetry publish
