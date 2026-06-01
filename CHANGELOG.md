# Changelog

All notable changes to `downloads-organizer` will be documented in this file.

## Unreleased

- Fixed recursive planning so files that would move to the same destination are renamed before any move occurs.
- Added regression coverage for same-run destination collisions and duplicate destination handling.
- Replaced README placeholder visuals with project-specific CLI and workflow diagrams.
- Hardened development and CI setup by upgrading pip before editable installs and enforcing a 90% coverage floor.

## 0.1.0 - 2026-06-01

- Initial Typer and Rich CLI for organizing folders by file type.
- Added dry-run previews, TOML configuration, duplicate detection, date-based renaming, and undo logs.
- Added pytest coverage, Ruff linting, GitHub Actions CI, issue templates, and documentation.
