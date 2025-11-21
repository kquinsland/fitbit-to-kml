# Repository Guidelines

## Project Structure & Module Organization

This repo is intentionally small: `main.py` is the current entry point and houses the CLI stub, while configuration lives in `pyproject.toml` and dependency locking in `uv.lock`. Add reusable parsing or export logic under a new `fitbit_to_kml/` package, reserve `tests/` for pytest suites, and keep sample GPX/KML fixtures or Fitbit exports under `assets/fixtures/` (git-ignored if sensitive). Update the README whenever you add modules so newcomers can map features quickly.

## Build, Test, and Development Commands

Use Python ≥3.14 and the `uv` toolchain that generated `uv.lock`. Run `uv sync` once to install dependencies, `uv run python main.py --help` to exercise the CLI, and `uv run pytest` for the fast test suite. During iterative work, `uv run python -m fitbit_to_kml.export <input.json>` is the preferred pattern so module imports stay consistent.

## Coding Style & Naming Conventions

Follow standard PEP 8 with 4-space indentation, type annotations on public functions, and `snake_case` for modules, functions, and variables. Keep user-facing CLI commands short and verbs-first (e.g., `export`, `summarize`). Use `structlog` for all logging—define a module-level logger via `structlog.get_logger()` and emit structured events (`logger.info("exported", workout_id=...)`) instead of printf debugging. Add docstrings to public APIs describing Fitbit schema expectations.

## Testing Guidelines

Pytest is the default test runner. Name test modules `test_<unit>.py`, and ensure each export path has fixture-backed tests that compare generated KML strings against golden files stored under `tests/data/`. When fixing regressions, include a regression test reproducing the issue, and run `uv run pytest -q` before opening a PR. Aim for coverage on parsing edge cases (paused workouts, split GPS tracks) even if overall coverage reporting is not yet enforced.

## Commit & Pull Request Guidelines

Commit messages mimic the existing history: short, imperative summaries, optionally prefixed with a scope (`init:`, `lint, ci:`). Keep each commit focused on a single concern. Pull requests should explain the Fitbit scenario being addressed, describe verification steps (commands run, sample files used), and link to any tracking issue. Include screenshots or attached KML snippets only when they add clarity; otherwise reference fixture names. Request review once CI (pytest) succeeds and dependencies remain unchanged unless intentionally updated.

## Security & Configuration Tips

Do not commit real Fitbit exports; scrub or anonymize JSON before uploading. Store API tokens or cookies via environment variables read at runtime (`FITBIT_SESSION=... uv run python main.py fetch`). If you add cloud integrations, document required settings in `.env.example` and keep secrets out of version control.
