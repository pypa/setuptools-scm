Style and Conventions

- Typing
  - mypy strict is enabled; add precise type hints for public functions/classes.
  - Prefer explicit/clear types; avoid `Any` and unsafe casts.
- Linting/Imports
  - Ruff is the canonical linter (config in pyproject). Respect its rules and isort settings (single-line imports, ordered, types grouped).
  - Flake8 config exists in tox.ini but ruff linting is primary.
- Formatting
  - Follow ruff guidance; keep lines <= 88 where applicable (flake8 reference).
- Testing
  - Pytest with `testing/` as testpath; default 5m timeout; warnings treated as errors.
  - Use existing fixtures; add `@pytest.mark` markers if needed (see pyproject markers).
- Logging
  - Tests run with log level info/debug; avoid noisy logs in normal library code.
- General
  - Small, focused functions; early returns; explicit errors. Keep APIs documented with concise docstrings.
