# Scripts Directory

This directory contains utility scripts to help with development, testing, and maintaining code quality.

## Auto-fixing Scripts

| Script | Purpose |
|--------|---------|
| `fix_all.py` | Runs all the fix scripts in sequence |
| `fix_mypy_issues.py` | Resolves duplicate module conflicts and other mypy issues |
| `fix_ruff.py` | Auto-fixes common Ruff linting issues |
| `fix_test_loader.py` | Fixes imports in loader test files |
| `fix_test_processor.py` | Fixes imports in processor test files |
| `lint_fix_all.sh` | Shell script that runs all linting and fixing operations |

## Usage

The scripts can be run directly:

```bash
python scripts/fix_all.py
```

Or through the Makefile:

```bash
make fix-all
make fix-mypy
make fix-ruff
make lint-fix-all
```

Or via pre-commit:

```bash
pre-commit run --hook-stage manual fix-all
pre-commit run --hook-stage manual fix-mypy
pre-commit run --hook-stage manual fix-ruff
```

## Development

When adding new fix scripts:

1. Create your script in this directory
2. Ensure it has a clear purpose and follows the script design pattern
3. Add execution permission: `chmod +x scripts/your_script.py`
4. Add it to the `fix_all.py` script
5. Add it to the pre-commit configuration
6. Add it to the Makefile

## Script Design Pattern

Each script should:

1. Be executable (`#!/usr/bin/env python3`)
2. Include docstrings explaining its purpose
3. Have a clear `main()` function
4. Include proper error handling
5. Display helpful output to the user
6. Be idempotent (safe to run multiple times)

## Testing

The scripts should be tested manually before being committed. All scripts should be able to run successfully on the codebase and should not introduce new issues.

# Utility Scripts

This directory contains utility scripts for development and maintenance of the AWS Entity Resolution project.

## Fix Scripts

### fix_typer_annotations.py

Fixes type annotations in CLI files to use `Optional[Type]` instead of `Type | None` or `Union[Type, None]` to ensure compatibility with Typer.

Usage:
```bash
python3 scripts/fix_typer_annotations.py
```

This script is also run automatically as a pre-commit hook.

### fix_all.py

Runs all fix scripts to address common issues in the codebase.

Usage:
```bash
python3 scripts/fix_all.py
```

### fix_mypy_issues.py

Fixes common mypy type checking issues.

Usage:
```bash
python3 scripts/fix_mypy_issues.py
```

### fix_ruff.py

Fixes common Ruff linting issues.

Usage:
```bash
python3 scripts/fix_ruff.py
```

## Pre-commit Hooks

The project uses pre-commit hooks to ensure code quality. You can run them manually:

```bash
# Run all hooks
pre-commit run --all-files

# Run a specific hook
pre-commit run fix-typer-annotations --all-files
```

### Troubleshooting Pre-commit Hooks

If you encounter issues with pre-commit hooks not finding the Python executable, ensure:

1. All scripts have the correct shebang line: `#!/usr/bin/env python3`
2. All scripts are executable: `chmod +x scripts/*.py`
3. The pre-commit config uses `python3` instead of `python` in the entry points
4. Your environment has Python 3 installed and available in the PATH

## CI/CD Scripts

These scripts are used in the CI/CD pipeline to automate testing and deployment.

### lint.py

Runs linting checks on the codebase.

Usage:
```bash
python3 scripts/lint.py
```

### precommit.py

Runs pre-commit hooks programmatically.

Usage:
```bash
python3 scripts/precommit.py
```
