# Contributing

Thank you for helping improve `downloads-organizer`.

## Development Setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

On Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

## Quality Checks

Run these before opening a pull request:

```bash
ruff check .
pytest
```

## Pull Request Guidelines

- Keep changes focused and explain user-facing behavior.
- Add or update tests for behavior changes.
- Update documentation for CLI flags, config keys, and workflows.
- Avoid committing local environment files, generated coverage reports, or personal config.

## Reporting Issues

Please include your operating system, Python version, command used, expected result, and actual result.

