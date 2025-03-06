# AWS Entity Resolution Linting Configuration

This document describes the linting configuration used in the AWS Entity Resolution project. The project uses a **medium strictness** linting configuration, which strikes a balance between code quality and development speed.

## Linting Tools

The project uses the following linting tools:

1. **Ruff** - A fast Python linter written in Rust that combines functionality from multiple linting tools
2. **mypy** - Static type checker for Python
3. **flake8** - Python style guide enforcement
4. **pre-commit** - Framework for managing and maintaining pre-commit hooks

## Medium Strictness Configuration

The linting configuration is set to medium strictness, which means:

- Essential code quality rules are enforced
- Some flexibility is allowed for pragmatic development
- Critical security and bug-prevention rules are enforced
- Documentation is encouraged but not strictly required everywhere
- Type annotations are encouraged but not required for all functions

## Ruff Configuration

The Ruff configuration (`.ruff.toml`) includes:

- **Line length**: 100 characters
- **Target Python version**: 3.10
- **Selected rule sets**:
  - `E` - pycodestyle errors
  - `F` - pyflakes
  - `B` - flake8-bugbear
  - `I` - isort
  - `C4` - flake8-comprehensions
  - `UP` - pyupgrade
  - `S` - flake8-bandit
  - `BLE` - flake8-blind-except
  - `A` - flake8-builtins
  - `C90` - mccabe complexity
  - `N` - pep8-naming
  - `D` - pydocstyle
  - `ANN` - flake8-annotations (with many ignores)
  - `SIM` - flake8-simplify
  - `TRY` - tryceratops

- **Ignored rules**: Various rules are ignored to maintain medium strictness, including:
  - Line length and formatting rules that conflict with Black
  - Overly strict docstring requirements
  - Some type annotation requirements
  - Rules that would make development too cumbersome

- **Complexity threshold**: 12 (medium)
- **Docstring convention**: Google style

## mypy Configuration

The mypy configuration (in `.mypy.ini` and `pyproject.toml`) includes:

- **Python version**: 3.10
- **Type checking strictness**:
  - `disallow_untyped_defs = False` - Type annotations not required on all functions
  - `disallow_incomplete_defs = False` - Partial type annotations allowed
  - `check_untyped_defs = True` - Type check functions without annotations
  - `disallow_untyped_decorators = False` - Decorators without type annotations allowed
  - `no_implicit_optional = True` - Be explicit about Optional types
  - `strict_optional = True` - Enforce proper Optional handling

- **Error codes disabled**:
  - `no-any-return` - Allow returning Any type
  - `var-annotated` - Allow variable annotations
  - `assignment` - Allow certain assignment patterns
  - `no-untyped-def` - Allow untyped function definitions

## flake8 Configuration

The flake8 configuration (`.flake8`) includes:

- **Line length**: 100 characters
- **Complexity threshold**: 12 (medium)
- **Selected checks**: C, E, F, W, B, B950
- **Ignored checks**:
  - E203 - Whitespace before ':'
  - E231 - Missing whitespace after ','
  - E501 - Line too long
  - W503 - Line break before binary operator
  - W291 - Trailing whitespace
  - W391 - Blank line at end of file
  - E402 - Module level import not at top of file
  - E722 - Do not use bare except
  - B006 - Mutable value as argument default
  - F841 - Local variable is assigned to but never used

## pre-commit Configuration

The pre-commit configuration (`.pre-commit-config.yaml`) includes:

- **Basic checks**: trailing whitespace, end-of-file fixer, YAML/JSON validation
- **Ruff**: Configured with medium strictness settings
- **mypy**: Configured with medium strictness settings
- **Terraform**: Format and validate Terraform files
- **Custom hooks**: Fix type annotations, run tests
- **Security checks**: bandit, safety, detect-secrets

## Customizing Strictness

To adjust the strictness level:

- **Increase strictness**: Add more rule sets to the `select` list in `.ruff.toml` and remove items from the `ignore` list
- **Decrease strictness**: Add more rules to the `ignore` list in `.ruff.toml` and remove rule sets from the `select` list

## Running Linting Checks

You can run linting checks using:

```bash
# Run all pre-commit hooks
pre-commit run --all-files

# Run just Ruff
ruff check .

# Run just mypy
mypy .

# Run just flake8
flake8 .

# Fix Ruff issues automatically
ruff check --fix .

# Fix all linting issues (custom script)
pre-commit run fix-all --hook-stage manual
```
