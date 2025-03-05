.PHONY: help lint fix fix-all fix-mypy fix-ruff check check-full lint-fix-all

# Default target
help:
	@echo "Available commands:"
	@echo "  make lint         Run optimized pre-commit checks (fast)"
	@echo "  make fix          Run auto-fixes for common linting issues"
	@echo "  make fix-all      Run all fix scripts and linting (comprehensive)"
	@echo "  make fix-mypy     Run only mypy fixes"
	@echo "  make fix-ruff     Run only ruff fixes"
	@echo "  make check        Run pre-commit only on changed files"
	@echo "  make check-full   Run full pre-commit checks on all files (slow)"
	@echo "  make lint-fix-all Run the complete linting and fixing script"

# Run optimized pre-commit checks (faster)
lint:
	pre-commit run trailing-whitespace end-of-file-fixer check-yaml check-json check-merge-conflict debug-statements ruff ruff-format

# Run auto-fixes for common linting issues
fix:
	python scripts/fix_all.py

# Run all fix scripts and linting (comprehensive)
fix-all: fix check

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

lint-fix-all: ## Run the complete linting and fixing script
	@echo "Running complete linting and fixing script..."
	@./scripts/lint_fix_all.sh
