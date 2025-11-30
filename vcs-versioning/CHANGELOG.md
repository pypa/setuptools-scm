# Changelog

<!-- towncrier release notes start -->

## 0.2.0 (2025-11-30)

### Added

- Add EnvReader class for structured reading of environment variable overrides with tool prefixes and distribution-specific variants (e.g., SETUPTOOLS_SCM_PRETEND vs VCS_VERSIONING_PRETEND). ([#env-reader](https://github.com/pypa/setuptools-scm/issues/env-reader))
- Initial release of vcs-versioning as a standalone package. Core version inference logic extracted from setuptools-scm for reuse by other build backends and tools. ([#initial-release](https://github.com/pypa/setuptools-scm/issues/initial-release))
- Add experimental integrator workflow API for composable configuration building. Allows build backends to progressively build Configuration objects from pyproject.toml, distribution metadata, and manual overrides. ([#integrator-api](https://github.com/pypa/setuptools-scm/issues/integrator-api))
- Add towncrier-fragments version scheme that infers version bumps based on changelog fragment types (feature=minor, bugfix=patch, removal=major). ([#towncrier-scheme](https://github.com/pypa/setuptools-scm/issues/towncrier-scheme))
- Requires Python 3.10 or newer. Modern type annotations and language features used throughout. ([#py310](https://github.com/pypa/setuptools-scm/issues/py310))


### Miscellaneous

- Converted _cli module into a package with improved structure. Archival templates moved to resource files. Added CliNamespace for typed arguments. ([#cli-package](https://github.com/pypa/setuptools-scm/issues/cli-package))
- Improved CLI type safety with OutputData TypedDict and better type annotations throughout CLI handling. ([#cli-typesafety](https://github.com/pypa/setuptools-scm/issues/cli-typesafety))
- Modernized type annotations to Python 3.10+ syntax throughout codebase. Generated version files now use modern `tuple[int | str, ...]` syntax with `from __future__ import annotations`. ([#modernize-types](https://github.com/pypa/setuptools-scm/issues/modernize-types))
- Enhanced GlobalOverrides: env_reader is now a required validated field. additional_loggers changed from string to tuple of logger instances for better type safety. ([#overrides-validation](https://github.com/pypa/setuptools-scm/issues/overrides-validation))

## 0.1.1

Initial release of vcs-versioning as a separate package extracted from setuptools-scm.

