Project: setuptools-scm

Purpose
- Extract and infer Python package versions from SCM metadata (Git/Mercurial) at build/runtime.
- Provide setuptools integrations (dynamic version, file finders) and fallbacks for archival/PKG-INFO.

Tech Stack
- Language: Python (3.8–3.13)
- Packaging/build: setuptools (>=61), packaging; console scripts via entry points
- Tooling: uv (dependency and run), pytest, mypy (strict), ruff (lint, isort), mkdocs (docs), tox (optional/matrix), wheel/build

Codebase Structure (high level)
- src/setuptools_scm/: library code
  - _cli.py, __main__.py: CLI entry (`python -m setuptools_scm`, `setuptools-scm`)
  - git.py, hg.py, hg_git.py: VCS parsing
  - _file_finders/: discover files for sdist
  - _integration/: setuptools and pyproject integration
  - version.py and helpers: version schemes/local version logic
  - discover.py, fallbacks.py: inference and archival fallbacks
- testing/: pytest suite and fixtures
- docs/: mkdocs documentation
- pyproject.toml: project metadata, pytest and ruff config
- tox.ini: alternate CI/matrix, flake8 defaults
- uv.lock: locked dependencies

Conventions
- Use uv to run commands (`uv run ...`); tests live under `testing/` per pytest config.
- Type hints throughout; strict mypy enforced; ruff governs lint rules and import layout (isort in ruff).
