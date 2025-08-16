Before considering a task done

- Code quality
  - Ruff clean: uv run ruff check .
  - Types clean: uv run mypy
- Tests
  - All tests green: uv run pytest
  - New/changed behavior covered with tests (use project fixtures)
- Docs
  - Update docs if user-facing behavior changed
  - Build docs cleanly: uv run mkdocs build --clean --strict
- Packaging
  - If relevant: uv run python -m build && uv run twine check dist/*
- Housekeeping
  - Follow existing naming and module structure; keep functions focused and typed
  - Update `CHANGELOG.md` when appropriate
