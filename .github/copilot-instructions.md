<!-- markdownlint-disable-file -->
# Agent Instructions for fitbit-to-kml

## Project Overview

This repository contains Python tools for exporting workouts with GPS data from the FitBit API and converting them to KML format for visualization and analysis. The project is in early development stages with basic scaffolding in place.

**Key Purpose**: Connect to FitBit API, download exercise data locally, and perform conversion/analysis operations.

## Technology Stack

### Core Technologies

- **Python**: 3.14 (latest version - brand new!)
- **Package Manager**: `uv` (modern, fast Python package manager)
- **Dependency Management**: `pyproject.toml` with `uv.lock` for reproducible builds
- **Testing Framework**: pytest (pytest flavor tests for all reasonable code)
- **Linting/Formatting**: Ruff (fast Python linter and formatter)
- **Pre-commit Hooks**: Automated checks for code quality

### Key Dependencies

- `structlog>=25.5.0` - Structured logging library
- `pytest>=9.0.0` - Testing framework (dev dependency)

## Development Environment Setup

### Prerequisites

1. Install Python 3.14 (check `.python-version` file)
2. Install `uv` package manager: `curl -LsSf https://astral.sh/uv/install.sh | sh`
3. Ensure you're in the project root directory

### Initial Setup

```bash
# Install Python 3.14 (uv will handle this)
uv python install

# Install project dependencies including dev dependencies
uv sync --all-extras --dev

# Install pre-commit hooks
pre-commit install
```

### Running the Application

```bash
# Run the main application
uv run python main.py

# Or use uv's run command
uv run main.py
```

## Code Standards and Style

### Type Annotations

- **REQUIRED**: All functions, methods, and public APIs must have complete type annotations
- Use modern Python 3.14 type hints (e.g., `list[str]` instead of `List[str]`)
- Use `from typing import` for advanced types like `Protocol`, `TypeVar`, etc.

### Code Style

- **Formatter**: Ruff (configured via `pyproject.toml`)
- **Linter**: Ruff (strict mode encouraged)
- **Line Length**: Follow project defaults (typically 88-100 characters)
- **Indentation**: 4 spaces (see `.editorconfig`)
- **Imports**: Follow Ruff's import sorting rules
- **File Encoding**: UTF-8 with LF line endings

### Code Quality Requirements

- No trailing whitespace
- Files must end with a newline
- YAML files must be valid
- JSON files must be valid (except VS Code config files)
- All Python code must pass Ruff linting and formatting checks

## Testing Guidelines

### Test Framework

- Use **pytest** for all tests
- Tests should be comprehensive - write tests for as much code as is reasonable

### Test Structure

```
tests/
├── test_<module_name>.py
├── conftest.py (for shared fixtures)
└── ...
```

### Test Naming

- Test files: `test_*.py`
- Test functions: `test_<descriptive_name>`
- Test classes: `Test<ClassName>`

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_example.py

# Run with coverage (if configured)
uv run pytest --cov
```

### Test Guidelines

- Write unit tests for individual functions/classes
- Write integration tests for API interactions and data conversions
- Mock external services (FitBit API) in tests
- Use fixtures for common test data
- Each test should test one thing and have a clear purpose
- Tests must be deterministic and not depend on external state

## Building and CI/CD

### Local Development Workflow

```bash
# 1. Make code changes
# 2. Run pre-commit checks
pre-commit run --all-files

# 3. Run linting
uv run ruff check .

# 4. Run formatting check
uv run ruff format --check --diff .

# 5. Auto-fix formatting
uv run ruff format .

# 6. Run tests
uv run pytest

# 7. Commit changes (pre-commit hooks will run automatically)
git commit -m "Your message"
```

### GitHub Actions Workflows

The project uses several CI/CD workflows:

1. **Python Lint and Test** (`ci_python_lint_and_test.yaml`)
   - Runs on PRs that modify `.py` files
   - Steps: Ruff lint → Ruff format check → pytest
   - Must pass before merging

2. **Pre-commit** (`ci_pre-commit.yaml`)
   - Runs pre-commit hooks on all files
   - Checks trailing whitespace, YAML/JSON validity, markdown linting

3. **Zizmor** (`meta_zizmor.yaml`)
   - Security linting for GitHub Actions workflows

4. **Release Drafter** (`meta_release-drafter.yaml`)
   - Automatically drafts releases based on PR labels

5. **Cleanup** (`meta_cleanup.yaml`)
   - Cleans up old artifacts and caches

### CI Requirements

- All Python files must pass Ruff linting (no warnings)
- All Python files must pass Ruff formatting checks
- All tests must pass
- Pre-commit hooks must succeed
- No security issues in GitHub Actions workflows

## Project Structure

```
fitbit-to-kml/
├── .github/
│   ├── copilot-instructions.md    # This file
│   └── workflows/                 # CI/CD workflows
├── .vscode/                       # VS Code settings
├── tests/                         # Test files (to be created)
├── main.py                        # Main entry point
├── pyproject.toml                 # Project metadata and dependencies
├── uv.lock                        # Locked dependency versions
├── .python-version                # Python version (3.14)
├── .editorconfig                  # Editor configuration
├── .pre-commit-config.yaml        # Pre-commit hooks configuration
├── .markdownlint.yaml             # Markdown linting rules
├── renovate.json5                 # Dependency update automation
└── README.md                      # Project documentation
```

### Future Structure (Expected)

```
fitbit-to-kml/
├── fitbit_to_kml/                 # Main package directory
│   ├── __init__.py
│   ├── api/                       # FitBit API client
│   ├── converters/                # Data conversion modules
│   ├── exporters/                 # Export to various formats (KML, etc.)
│   └── utils/                     # Utility functions
├── tests/                         # Test files mirroring src structure
└── ...
```

## Common Tasks and Workflows

### Adding a New Dependency

```bash
# Add a production dependency
uv add <package-name>

# Add a development dependency
uv add --dev <package-name>

# Update lock file
uv lock

# Sync environment
uv sync --all-extras --dev
```

### Creating a New Module

1. Create the module file with proper type annotations
2. Add corresponding test file in `tests/` directory
3. Import and use in appropriate places
4. Run linting and tests
5. Update documentation if needed

### Working with FitBit API (Future)

- Store API credentials securely (never commit to repo)
- Use environment variables or secure configuration
- Mock API responses in tests
- Handle rate limiting gracefully
- Log API interactions with structlog

### Converting to KML (Future)

- Parse FitBit GPS data
- Transform to KML format
- Validate output
- Support batch conversion
- Provide progress feedback

## Important Conventions

### Logging

- Use `structlog` for all logging
- Log at appropriate levels (debug, info, warning, error)
- Include context in log messages
- Structure log data for easy parsing

### Error Handling

- Use specific exception types
- Provide clear error messages
- Handle API errors gracefully
- Don't swallow exceptions silently
- Add type hints for exceptions in docstrings

### Documentation

- Use docstrings for all public functions/classes
- Follow Google or NumPy docstring style (to be standardized)
- Include type information in docstrings
- Document parameters, return values, and exceptions
- Keep README.md updated with user-facing changes

### Git Workflow

- Work in feature branches
- Use conventional commit messages
- Keep commits atomic and focused
- Reference issues in commit messages
- Don't commit temporary files, build artifacts, or `__pycache__`

### Security

- Never commit API keys, tokens, or credentials
- Use environment variables for sensitive data
- Keep dependencies updated (Renovate handles this)
- Review security advisories
- Run Zizmor on workflow changes

## Python 3.14 Specific Features

Since this project uses Python 3.14 (brand new), be aware of and leverage:

- Latest type hinting improvements
- Performance enhancements
- New standard library features
- Improved error messages
- Updated syntax features

Stay informed about Python 3.14 specifics when writing code.

## Editor Configuration

The project includes `.editorconfig` for consistent editor behavior:

- UTF-8 encoding
- LF line endings
- 4-space indentation for Python, TOML, JSON, YAML
- Trim trailing whitespace (except Markdown)
- Insert final newline

Ensure your editor respects these settings.

## Troubleshooting

### Common Issues

1. **uv not found**: Install with `curl -LsSf https://astral.sh/uv/install.sh | sh`
2. **Python 3.14 not available**: Run `uv python install` to auto-install
3. **Import errors**: Run `uv sync --all-extras --dev` to sync dependencies
4. **Pre-commit failures**: Run `pre-commit run --all-files` to see all issues
5. **Ruff errors**: Run `uv run ruff check --fix .` to auto-fix where possible

### Getting Help

- Check existing issues on GitHub
- Review CI logs for detailed error messages
- Consult Ruff documentation for linting rules
- Review pytest documentation for test issues

## Additional Resources

- [uv Documentation](https://docs.astral.sh/uv/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [pytest Documentation](https://docs.pytest.org/)
- [structlog Documentation](https://www.structlog.org/)
- [Python 3.14 Release Notes](https://docs.python.org/3.14/whatsnew/3.14.html)
- [FitBit API Documentation](https://dev.fitbit.com/)
