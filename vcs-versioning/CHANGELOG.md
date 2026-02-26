# Changelog

<!-- towncrier release notes start -->

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

