#!/bin/bash
# Complete linting and fixing script for the AWS Entity Resolution project

set -e  # Exit immediately if a command exits with a non-zero status

echo "🔧 AWS Entity Resolution - Complete Linting & Fixing Script 🔧"
echo "============================================================="

# Function to print section header
section() {
  echo ""
  echo "📋 $1"
  echo "-------------------------------------------------------------"
}

# Fix mypy issues
section "Running mypy fixes"
python scripts/fix_mypy_issues.py

# Fix ruff issues
section "Running Ruff fixes"
python scripts/fix_ruff.py

# Fix test files
section "Fixing test files"
python scripts/fix_test_loader.py
python scripts/fix_test_processor.py

# Run essential linting
section "Running Ruff linting"
ruff check --fix --unsafe-fixes --extend-select=E,F,B,I,W,C90 .

# Run essential pre-commit hooks
section "Running pre-commit hooks"
pre-commit run trailing-whitespace --all-files
pre-commit run end-of-file-fixer --all-files
pre-commit run check-yaml --all-files
pre-commit run check-added-large-files --all-files
pre-commit run check-json --all-files
pre-commit run check-merge-conflict --all-files
pre-commit run debug-statements --all-files

# Final check
section "Final check - any remaining issues:"
ruff check .

echo ""
echo "✅ All linting and fixing completed!"
echo "💡 Most non-critical issues should be resolved."
echo "💡 Any remaining issues may require manual intervention."
