# aws-primitives-tool - Project Specification

## Goal

A CLI that provides AWS serverless primitives as composable CLI commands

## What is aws-primitives-tool?

`aws-primitives-tool` is a command-line utility built with modern Python tooling and best practices.

## Technical Requirements

### Runtime

- Python 3.14+
- Installable globally with mise
- Cross-platform (macOS, Linux, Windows)

### Dependencies

- `click` - CLI framework

### Development Dependencies

- `ruff` - Linting and formatting
- `mypy` - Type checking
- `pytest` - Testing framework

## CLI Arguments

```bash
aws-primitives-tool [OPTIONS]
```

### Options

- `--help` / `-h` - Show help message
- `--version` - Show version

## Project Structure

```
aws-primitives-tool/
├── aws_primitives_tool/
│   ├── __init__.py
│   ├── cli.py           # Click CLI entry point
│   └── utils.py         # Utility functions
├── tests/
│   ├── __init__.py
│   └── test_utils.py
├── pyproject.toml       # Project configuration
├── README.md            # User documentation
├── CLAUDE.md            # This file
├── Makefile             # Development commands
├── LICENSE              # MIT License
├── .mise.toml           # mise configuration
└── .gitignore
```

## Code Style

- Type hints for all functions
- Docstrings for all public functions
- Follow PEP 8 via ruff
- 100 character line length
- Strict mypy checking

## Development Workflow

```bash
# Install dependencies
make install

# Run linting
make lint

# Format code
make format

# Type check
make typecheck

# Run unit tests
make test

# Run integration tests (requires AWS credentials)
make test-integration

# Run all checks
make check

# Full pipeline
make pipeline
```

## Testing

### Unit Tests

Unit tests are located in `tests/` and use pytest:

```bash
make test
```

### Integration Tests

Integration tests verify end-to-end functionality against a real DynamoDB table.
Located in `tests/integration/`:

```bash
# Run all integration tests
make test-integration

# Or run directly
./tests/integration/run_all_tests.sh

# Run specific test suite
./tests/integration/test_kv_operations.sh
./tests/integration/test_counter_operations.sh
./tests/integration/test_list_operations.sh
```

**Prerequisites:**
- Valid AWS credentials configured
- DynamoDB table creation permissions
- Test table: `aws-primitives-tool-kvstore-test` (auto-created)

**Coverage:**
- ✅ KV operations (set, get, delete, exists, list)
- ✅ Counter operations (inc, dec, get-counter)
- ✅ List operations (lpush, rpush, lpop, rpop, lrange)
- ✅ Lock operations (acquire, release, extend, check)
- ✅ Queue, Set, and Leader operations
- ✅ Edge cases and error handling

See `tests/integration/README.md` for detailed documentation.
```

## Installation Methods

### Global installation with mise

```bash
cd /path/to/aws-primitives-tool
mise use -g python@3.14
uv sync
uv tool install .
```

After installation, `aws-primitives-tool` command is available globally.

### Local development

```bash
uv sync
uv run aws-primitives-tool [args]
```
