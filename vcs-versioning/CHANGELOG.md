# Changelog

<!-- towncrier release notes start -->

## 1.1.2 (2026-04-11)

### Fixed

- Filter Mercurial pseudo-tags (tip, qbase, qtip, qparent) and iterate all tags when resolving versions, fixing spurious "no version found" warnings from MQ extension tags. ([#310](https://github.com/pypa/setuptools-scm/issues/310))
- The ``semver-pep440`` and ``semver-pep440-release-branch`` version schemes now
  correctly handle ``.dev0`` tags and pre-release tags. Exact checkout on a tag
  returns the tag as-is (``2.0.dev0`` stays ``2.0.dev0``, ``1.0.0rc1`` stays
  ``1.0.0rc1``). Non-exact ``.dev0`` tags are treated as explicit version anchors,
  producing ``X.Y.0.devN`` instead of incorrectly bumping past the anchored version. ([#523](https://github.com/pypa/setuptools-scm/issues/523))

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

