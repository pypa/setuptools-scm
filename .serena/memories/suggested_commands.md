Environment
- Install deps (uses default groups test, docs):
  - uv sync

Core Dev
- Run tests:
  - uv run pytest
- Lint (ruff):
  - uv run ruff check .
  - uv run ruff check . --fix  # optional autofix
- Type check (mypy strict):
  - uv run mypy
- Build docs:
  - uv run mkdocs serve --dev-addr localhost:8000
  - uv run mkdocs build --clean --strict

Entrypoints / Tooling
- CLI version/debug:
  - uv run python -m setuptools_scm --help
  - uv run python -m setuptools_scm
  - uv run setuptools-scm --help
- Build dist and verify:
  - uv run python -m build
  - uv run twine check dist/*
- Optional matrix via tox:
  - uv run tox -q

Git/Linux Utilities (Linux host)
- git status / git log --oneline --graph --decorate
- ls -la; find . -name "pattern"; grep -R "text" .
