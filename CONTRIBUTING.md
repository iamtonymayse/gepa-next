# Contributing to GEPA Next

Welcome, and thank you for taking the time to contribute! We value and encourage contributions from the community. Please follow these guidelines to help us maintain a high‑quality, sustainable project.

## Getting Started

1. **Open an issue**: Before starting work on a new feature or bug fix, please open an issue to discuss your idea. This helps avoid duplicate work and ensures alignment with the project roadmap.
2. **Fork or branch**: Use GitHub's workflow by forking the repository or, if you have push permissions, by creating a feature branch off of `main`. Name your branch descriptively (e.g. `feat/notes-crud` or `fix/validation-error`).
3. **Sync dependencies**: Use [uv](https://github.com/astral-sh/uv) to manage dependencies: run `uv sync` to install the pinned versions specified in `pyproject.toml`.

## Development Workflow

- **Run tests and QA**: Before committing, run `make qa` in your Codespace. This runs linting (`ruff`), formatting checks, type checking (`mypy --strict`), and the test suite with coverage. All checks should pass locally before you open a pull request.
- **Write tests**: New functionality should include appropriate unit tests in `tests/` or integration tests in `tests_e2e/`. Aim for at least 80% coverage.
- **Follow style guidelines**: We use [PEP 8](https://peps.python.org/pep-0008/) plus `ruff`'s default rules for formatting and linting. We also enforce type hints with `mypy --strict`. If you need to disable a rule, justify it with an inline comment.
- **Commit messages**: Use meaningful commit messages in the format `type: description` (e.g. `feat: add notes CRUD endpoint`). Keep commits small and focused.

## Opening a Pull Request

- Ensure your branch is up‑to‑date with `main` and that all QA checks pass locally (`make qa`).
- Include a clear description of the problem and the proposed solution. Reference any relevant issues.
- Update documentation (`README.md`, `docs/CHANGELOG.md`, etc.) as needed.
- When ready, open a pull request against `main` from the GitHub Codespaces panel. The CI workflow will run automatically.
- At least one approving review is required. The CI must be green before merge.

## Reporting Security Issues

If you discover a security vulnerability, please follow the process described in `SECURITY.md`. Do **not** create a public issue.

## Code of Conduct

This project adheres to the Contributor Covenant. By participating, you are expected to uphold the [Code of Conduct](CODE_OF_CONDUCT.md). Please report unacceptable behavior to the maintainers.

Thank you for helping make GEPA Next better!
