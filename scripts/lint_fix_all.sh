#!/bin/bash
# Comprehensive script to fix all linting issues and run all checks

set -e  # Exit on error

echo "🔍 Running comprehensive linting and fixing script..."

# Step 1: Fix type annotations
echo "🔧 Step 1: Fixing type annotations..."
python scripts/fix_all_annotations.py
python scripts/fix_typer_annotations.py

# Step 2: Fix mypy issues
echo "🔧 Step 2: Fixing mypy issues..."
python scripts/fix_mypy_issues.py

# Step 3: Fix ruff issues
echo "🔧 Step 3: Fixing ruff issues..."
python scripts/fix_ruff.py

# Step 4: Run pre-commit hooks
echo "🔧 Step 4: Running pre-commit hooks..."
pre-commit run --all-files

# Step 5: Run mypy
echo "🔧 Step 5: Running mypy type checking..."
poetry run mypy src || echo "⚠️ Mypy found issues, but continuing..."

# Step 6: Run ruff with all checks
echo "🔧 Step 6: Running ruff with all checks..."
poetry run ruff check . || echo "⚠️ Ruff found issues, but continuing..."

# Step 7: Run bandit security checks
echo "🔧 Step 7: Running bandit security checks..."
poetry run bandit -c pyproject.toml -r src || echo "⚠️ Bandit found issues, but continuing..."

# Step 8: Run fast tests
echo "🔧 Step 8: Running fast tests..."
poetry run pytest -xvs tests/ --durations=3 -m "not slow" || echo "⚠️ Some tests failed, but continuing..."

echo "✅ Linting and fixing complete!"
echo "Note: Some issues may still need manual fixing. Check the output above for details."
