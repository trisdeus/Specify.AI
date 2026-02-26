# Sprint 1: Project Setup & CLI Scaffold - Implementation Plan

## Overview

This plan covers Sprint 1 (Week 1) of the Specify.AI implementation, establishing the foundation for a local-first CLI tool that generates documentation from AI.

## Current State Analysis

### Existing Structure

```
Specify_AI/
├── .env.template           # API key placeholders
├── .gitignore              # Git ignore patterns (configured)
├── AGENTS.md               # Agent instructions
├── README.md               # Project readme
├── requirements.txt        # Current dependencies (Google APIs, scraping)
├── directives/             # SOPs in Markdown
├── execution/              # Python scripts
├── plans/                  # Planning documents
└── .tmp/                   # Temporary files
```

### Missing Components

- `specify/` package (main CLI application)
- `pyproject.toml` (project metadata, tool config)
- `setup.py` (package installation)
- `tests/` directory
- `.github/workflows/` (CI/CD)

## Target Structure (from Appendix A)

```
specify_ai/
├── .env                    # Local environment variables (gitignored)
├── .env.template           # Template for environment variables
├── .gitignore
├── README.md
├── requirements.txt        # Python dependencies
├── pyproject.toml          # Project metadata, tool config
├── setup.py                # Package installation
│
├── specify/                # Main package
│   ├── __init__.py
│   ├── cli.py              # Click CLI entry point
│   │
│   ├── core/               # Core functionality
│   │   └── __init__.py
│   │
│   ├── providers/          # LLM provider clients
│   │   └── __init__.py
│   │
│   ├── generators/         # Document generators
│   │   └── __init__.py
│   │
│   ├── rules/              # Document rules
│   │   └── __init__.py
│   │
│   ├── analysis/           # Consistency and recommendations
│   │   └── __init__.py
│   │
│   └── utils/              # Shared utilities
│       └── __init__.py
│
├── tests/                  # Test suite
│   ├── __init__.py
│   ├── conftest.py         # Pytest fixtures
│   └── test_cli.py
│
└── .github/                # GitHub workflows
    └── workflows/
        ├── test.yml        # Run tests on PR
        └── lint.yml        # Lint and format check
```

## Implementation Details

### 1. requirements.txt Updates

Add the following dependencies:

- `click` - CLI framework
- `pytest` - Testing framework
- `pytest-cov` - Coverage reporting
- `ruff` - Linting
- `black` - Code formatting
- `mypy` - Type checking
- `structlog` - Structured logging
- `pydantic` - Data validation
- `cryptography` - API key encryption
- `ollama` - Ollama Python SDK
- `aiohttp` - Async HTTP client

### 2. pyproject.toml Configuration

```toml
[project]
name = "specify-ai"
version = "0.1.0"
description = "Local-first CLI tool that generates documentation from AI"
requires-python = ">=3.11"

[tool.ruff]
line-length = 88
target-version = "py311"

[tool.black]
line-length = 88
target-version = ["py311"]

[tool.mypy]
python_version = "3.11"
strict = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
```

### 3. setup.py Configuration

- Package name: `specify-ai`
- Entry point: `specify = specify.cli:main`
- Packages: `specify`, `specify.core`, `specify.providers`, etc.

### 4. CLI Design (specify/cli.py)

```python
import click
from specify import __version__

@click.group()
@click.version_option(version=__version__, prog_name="specify-ai")
def main():
    """Specify.AI - Generate documentation from AI."""
    pass

# Placeholder commands for future implementation
@main.group()
def config():
    """Configuration commands."""
    pass

@main.command()
def generate():
    """Generate documentation."""
    pass
```

### 5. Test Fixtures (tests/conftest.py)

From Appendix C:

- `temp_config_dir` - Temporary config directory
- `sample_prompt` - Sample product prompt
- `mock_ollama_response` - Mock Ollama API response
- `mock_openai_response` - Mock OpenAI API response

### 6. CI/CD Workflows

#### test.yml

- Triggers: push, pull_request to main
- Steps: checkout, setup Python, install deps, run pytest with coverage

#### lint.yml

- Triggers: push, pull_request to main
- Steps: checkout, setup Python, run ruff, black, mypy

### 7. Pre-commit Hooks

- ruff (linting)
- black (formatting)
- mypy (type checking)

## Verification Checklist

After implementation, verify:

| Check           | Command                      | Expected Result                    |
| --------------- | ---------------------------- | ---------------------------------- |
| Package install | `pip install -e .`           | Success                            |
| CLI help        | `specify --help`             | Shows usage                        |
| CLI version     | `specify --version`          | Prints "specify-ai, version 0.1.0" |
| Package import  | `python -c "import specify"` | No error                           |
| Tests pass      | `pytest tests/ -v`           | All tests pass                     |
| Type check      | `mypy specify`               | 0 errors                           |
| Lint check      | `ruff check .`               | 0 errors                           |
| Format check    | `black --check .`            | All files formatted                |

## Edge Cases Handled

1. **Running `specify` with no arguments** - Shows help message (Click default)
2. **Running `specify --version`** - Prints version string
3. **Running `specify --help`** - Shows usage with commands
4. **Import specify package** - No ImportError
5. **pytest with no tests collected** - Passes with exit code 0
6. **ruff/black/mypy checks** - Pass with 0 errors

## File Creation Order

1. Update `requirements.txt`
2. Create `pyproject.toml`
3. Create `setup.py`
4. Create `specify/__init__.py`
5. Create `specify/cli.py`
6. Create all `specify/*/` subdirectories with `__init__.py`
7. Create `tests/` directory with test files
8. Create `.github/workflows/` with CI/CD files
9. Create `.pre-commit-config.yaml`

## Notes

- Preserve existing `directives/`, `execution/`, `plans/` directories
- CLI entry point must be `specify` (not `specify-ai`)
- Python 3.11+ required
- Windows 11 with cmd.exe compatibility required
