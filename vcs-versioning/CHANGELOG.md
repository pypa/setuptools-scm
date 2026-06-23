# Changelog

<!-- towncrier release notes start -->

## 2.1.2 (2026-06-23)

### Fixed

- Fix MetadataWorkdir crash when using custom `tag_regex` — stored tags are already parsed version strings and no longer re-parsed through the tag regex. ([#1439](https://github.com/pypa/setuptools-scm/issues/1439))

## 2.1.1 (2026-06-23)

### Fixed

- Fix spurious ``DeprecationWarning`` for ``tag_regex`` when using default value via ``get_version()``. ([#1434](https://github.com/pypa/setuptools-scm/issues/1434))

## 2.1.0 (2026-06-22)

### Added

- Add `VcsEnvironment.build_config_from_pyproject`, `build_config_from_data`, and `pyproject_tool_names` methods for canonical env-first configuration creation. ([#1424](https://github.com/pypa/setuptools-scm/issues/1424))


### Fixed

- Fix DeprecationWarning leak in pretend API by ensuring all public APIs attach VcsEnvironment to Configuration before accessing env-dependent properties. ([#1424](https://github.com/pypa/setuptools-scm/issues/1424))
- Fix fallback discovery so an unprocessed `.git_archival.txt` no longer shadows a valid `PKG-INFO` in PyPI sdists. ([#1431](https://github.com/pypa/setuptools-scm/issues/1431))

## 2.0.1 (2026-06-22)

### Fixed

- Update CI to use PyPy 3.11 as cryptography has no PyPy 3.10 build available ([#1421](https://github.com/pypa/setuptools-scm/issues/1421))

## 2.0.0 (2026-06-22)

### Removed

- Remove module-level accessor functions from ``vcs_versioning.overrides``: ``get_active_overrides()``, ``get_debug_level()``, ``get_subprocess_timeout()``, ``get_hg_command()``, ``get_source_date_epoch()``, and ``source_epoch_or_utc_now()``. Use ``VcsEnvironment.from_env()`` or ``config.env`` instead. External consumer audit confirmed no downstream usage of these functions. ([#removed-accessors](https://github.com/pypa/setuptools-scm/issues/removed-accessors))


### Added

- Introduce ``VcsEnvironment`` and the chained API (``env → config → workdir → version``) for explicit runtime settings. Add ``Configuration.env``, ``Configuration.discover_workdir()``, and the ``vcs_versioning.discover_workdir`` entry-point group. Integrators can now use ``VcsEnvironment.from_env("MY_TOOL").build_config()`` to thread timeout, hg command, and other settings without ambient globals. ([#chained-api](https://github.com/pypa/setuptools-scm/issues/chained-api))
- Warn when ``version_file`` or ``write_to`` targets a file that is tracked by version control. A tracked version file causes ``git describe --dirty`` to report a dirty tree after builds rewrite it, leading to unexpected dev-version bumps on tag checkouts. The warning advises removing the file from VCS and adding it to the ignore file. ([#468](https://github.com/pypa/setuptools-scm/issues/468))
- Add native Jujutsu (jj) VCS backend with version inference, file finder, and strict error when `.jj/` is detected but `jj` is not installed. The `SETUPTOOLS_SCM_DISABLE_JJ=1` environment variable can be used to opt out of jj discovery in environments where `jj` is not available. ([#1070](https://github.com/pypa/setuptools-scm/issues/1070))
- Add ``no-local-version-strict`` local scheme that combines ``no-local-version`` and ``fail-on-uncommitted-changes`` in a single entry-point. When the working tree is dirty the build fails with ``DirtyWorkingTreeError``; otherwise the local segment is stripped, producing PyPI-safe versions suitable for release builds. ([#1238](https://github.com/pypa/setuptools-scm/issues/1238))
- Modernize Mercurial backend to use `latesttag(pattern)` template instead of manual tag discovery with revsets, reducing subprocess calls and enabling tag.prefix/tag.strict support for Mercurial repositories. ([#1335](https://github.com/pypa/setuptools-scm/issues/1335))
- Add `tag.prefix` and `tag.strict` configuration options for controlling which VCS tags are considered version tags. `tag.prefix` filters and strips a literal prefix (for monorepo tag schemes like `hatchling-v1.0.0`). `tag.strict` (tri-state) requires tags to contain at least one dot, rejecting non-version tags like event markers. Both compose to generate the `git describe --match` glob automatically. ([#1411](https://github.com/pypa/setuptools-scm/issues/1411))


### Fixed

- Replace bare ``assert`` in ``ScmWorkdir.config`` and ``FallbackWorkdir.config`` with a ``RuntimeError`` that explains how to properly associate a ``Configuration`` with a workdir. ([#workdir-config-error](https://github.com/pypa/setuptools-scm/issues/workdir-config-error))
- Filter Mercurial pseudo-tags (tip, qbase, qtip, qparent) and iterate all tags when resolving versions, fixing spurious "no version found" warnings from MQ extension tags. ([#310](https://github.com/pypa/setuptools-scm/issues/310))
- The ``semver-pep440`` and ``semver-pep440-release-branch`` version schemes now
  correctly handle ``.dev0`` tags and pre-release tags. Exact checkout on a tag
  returns the tag as-is (``2.0.dev0`` stays ``2.0.dev0``, ``1.0.0rc1`` stays
  ``1.0.0rc1``). Non-exact ``.dev0`` tags are treated as explicit version anchors,
  producing ``X.Y.0.devN`` instead of incorrectly bumping past the anchored version. ([#523](https://github.com/pypa/setuptools-scm/issues/523))
- Replace git archive with git ls-files for file discovery, fixing freshly added files being hidden while still honoring export-ignore via gitattributes ([#662](https://github.com/pypa/setuptools-scm/issues/662))
- Fix git archivals from repositories with no tags failing to determine a version. ([#1288](https://github.com/pypa/setuptools-scm/issues/1288))
- Override user-defined shell aliases when invoking VCS commands, preventing alias expansions from corrupting subprocess output. ([#1359](https://github.com/pypa/setuptools-scm/issues/1359))
- Suppress spurious "toml section missing" warnings when setuptools-scm is used only for file finding or with simplified activation. The log message is now debug-level and only emitted when the package is actually a build requirement. ([#1368](https://github.com/pypa/setuptools-scm/issues/1368))
- Read towncrier fragment directory from `[tool.towncrier]` in `pyproject.toml` or the top-level `directory` key in `towncrier.toml` instead of hardcoding `changelog.d/`. ([#1380](https://github.com/pypa/setuptools-scm/issues/1380))
- Add the py.typed marker file. ([#1392](https://github.com/pypa/setuptools-scm/issues/1392))

## 1.1.1 (2026-03-27)

### Fixed

- Add MANIFEST.in to ensure sdist includes testing_vcs/ when the VCS file finder is unavailable. ([#1336](https://github.com/pypa/setuptools-scm/issues/1336))

## 1.1.0 (2026-03-27)

### Added

- Add ``fail-on-uncommitted-changes`` as a composable local scheme: raise when the working tree is dirty, otherwise defer to the next local scheme in the list so any ``version_scheme`` can be used. ([#1205](https://github.com/pypa/setuptools-scm/issues/1205))
- When ``HEAD`` is exactly on a tag (``git describe --exact-match``), shallow Git worktrees no longer trigger ``warn_on_shallow``, ``fail_on_shallow``, or ``fetch_on_shallow``—shallow clones are enough for tagged release builds and avoid unnecessary unshallow fetches. ([#1241](https://github.com/pypa/setuptools-scm/issues/1241))
- The "fetch_on_shallow" option for Git worktrees no longer fetches the contents of Git commits--
  only their tags and refs.
  It takes hardly any bandwidth as a result, and is quite fast. ([#1303](https://github.com/pypa/setuptools-scm/issues/1303))


### Miscellaneous

- Build ``vcs-versioning`` with setuptools instead of hatchling to avoid a bootstrap cycle (hatchling → pluggy → setuptools-scm → vcs-versioning) for downstream packagers. ([#1302](https://github.com/pypa/setuptools-scm/issues/1302))

## 1.0.1 (2026-03-09)

### Miscellaneous

- Simplify release tag creation to use a single ``createRelease`` API call instead of separate ``createTag``/``createRef``/``createRelease`` calls, avoiding dangling tag objects on partial failures. ([#release-pipeline](https://github.com/pypa/setuptools-scm/issues/release-pipeline))

## 1.0.0 (2026-02-26)

### Major Changes

- First stable release of vcs-versioning as a standalone package. ([#1228](https://github.com/pypa/setuptools-scm/issues/1228))


### Deprecated

- Rename `python-simplified-semver` to `semver-pep440` and `release-branch-semver` to `semver-pep440-release-branch` to prevent confusion with actual semver (which these schemes don't produce — they produce PEP 440-compliant versions). The old names still work but emit a deprecation warning. ([#679](https://github.com/pypa/setuptools-scm/issues/679))


### Added

- Add experimental integrator workflow API for composable configuration building. Allows build backends to progressively build Configuration objects from pyproject.toml, distribution metadata, and manual overrides. ([#1228](https://github.com/pypa/setuptools-scm/issues/1228))
- Add EnvReader class for structured reading of environment variable overrides with tool prefixes and distribution-specific variants (e.g., SETUPTOOLS_SCM_PRETEND vs VCS_VERSIONING_PRETEND). ([#1228](https://github.com/pypa/setuptools-scm/issues/1228))
- Requires Python 3.10 or newer. Modern type annotations and language features used throughout. ([#1228](https://github.com/pypa/setuptools-scm/issues/1228))
- Add towncrier-fragments version scheme that infers version bumps based on changelog fragment types (feature=minor, bugfix=patch, removal=major). ([#1228](https://github.com/pypa/setuptools-scm/issues/1228))
- Initial release of vcs-versioning as a standalone package. Core version inference logic extracted from setuptools-scm for reuse by other build backends and tools. ([#1228](https://github.com/pypa/setuptools-scm/issues/1228))


### Miscellaneous

- Improved CLI type safety with OutputData TypedDict and better type annotations throughout CLI handling. ([#1228](https://github.com/pypa/setuptools-scm/issues/1228))
- Modernized type annotations to Python 3.10+ syntax throughout codebase. Generated version files now use modern `tuple[int | str, ...]` syntax with `from __future__ import annotations`. ([#1228](https://github.com/pypa/setuptools-scm/issues/1228))
- Enhanced GlobalOverrides: env_reader is now a required validated field. additional_loggers changed from string to tuple of logger instances for better type safety. ([#1228](https://github.com/pypa/setuptools-scm/issues/1228))
- Converted _cli module into a package with improved structure. Archival templates moved to resource files. Added CliNamespace for typed arguments. ([#1228](https://github.com/pypa/setuptools-scm/issues/1228))

## 0.1.1

Initial release of vcs-versioning as a separate package extracted from setuptools-scm.

