# API Import Path Mapping

## Old → New Import Paths

### Public APIs (exported by both packages)

| Old (setuptools_scm) | New (vcs_versioning) | setuptools_scm re-exports? |
|---------------------|---------------------|---------------------------|
| `setuptools_scm.Configuration` | `vcs_versioning.Configuration` | Yes |
| `setuptools_scm.ScmVersion` | `vcs_versioning.ScmVersion` | Yes |
| `setuptools_scm.Version` | `vcs_versioning.Version` | Yes |
| `setuptools_scm.NonNormalizedVersion` | `vcs_versioning.NonNormalizedVersion` | Yes |
| `setuptools_scm.DEFAULT_VERSION_SCHEME` | `vcs_versioning.DEFAULT_VERSION_SCHEME` | Yes |
| `setuptools_scm.DEFAULT_LOCAL_SCHEME` | `vcs_versioning.DEFAULT_LOCAL_SCHEME` | Yes |

### Legacy APIs (setuptools_scm only)

| API | Location | Notes |
|-----|----------|-------|
| `setuptools_scm.get_version` | `setuptools_scm._get_version_impl` | Soft deprecated, wraps vcs_versioning |
| `setuptools_scm._get_version` | `setuptools_scm._get_version_impl` | Internal, wraps vcs_versioning |
| `setuptools_scm.dump_version` | `setuptools_scm._integration.dump_version` | Soft deprecated |

### Private Modules (moved to vcs_versioning)

| Old | New | Access |
|-----|-----|--------|
| `setuptools_scm.git` | `vcs_versioning._backends._git` | Private (entry points only) |
| `setuptools_scm.hg` | `vcs_versioning._backends._hg` | Private (entry points only) |
| `setuptools_scm.hg_git` | `vcs_versioning._backends._hg_git` | Private (entry points only) |
| `setuptools_scm.scm_workdir` | `vcs_versioning._backends._scm_workdir` | Private |
| `setuptools_scm.discover` | `vcs_versioning._discover` | Private |
| `setuptools_scm.version` | `vcs_versioning._version_schemes` | Private (entry points only) |
| `setuptools_scm.fallbacks` | `vcs_versioning._fallbacks` | Private (entry points only) |

### Backward Compatibility Stubs (setuptools_scm)

These modules re-export from vcs_versioning for backward compatibility:

- `setuptools_scm.git` → re-exports from `vcs_versioning._backends._git`
- `setuptools_scm.hg` → re-exports from `vcs_versioning._backends._hg`
- `setuptools_scm.version` → re-exports from `vcs_versioning._version_schemes`
- `setuptools_scm._config` → re-exports from `vcs_versioning.config`

### Utilities

| Module | New Location | Access |
|--------|-------------|--------|
| `_run_cmd` | `vcs_versioning._run_cmd` | Private |
| `_node_utils` | `vcs_versioning._node_utils` | Private |
| `_modify_version` | `vcs_versioning._modify_version` | Private |
| `_types` | `vcs_versioning._types` | Private |
| `_entrypoints` | `vcs_versioning._entrypoints` | Private |
| `_log` | `vcs_versioning._log` | Private |
| `_compat` | `vcs_versioning._compat` | Private |
| `_overrides` | `vcs_versioning._overrides` | Private |
| `_requirement_cls` | `vcs_versioning._requirement_cls` | Private |
| `_cli` | `vcs_versioning._cli` | Private (CLI entry point) |

### Entry Points

| Group | Old Package | New Package | Backward Compat |
|-------|------------|-------------|-----------------|
| `setuptools_scm.version_scheme` | setuptools_scm | vcs_versioning | Both register |
| `setuptools_scm.local_scheme` | setuptools_scm | vcs_versioning | Both register |
| `setuptools_scm.parse_scm` | setuptools_scm | vcs_versioning | Both register |
| `setuptools_scm.parse_scm_fallback` | setuptools_scm | vcs_versioning | Both register |
| `setuptools_scm.files_command` | setuptools_scm | stays in setuptools_scm | setuptools_scm only |
| `setuptools_scm.files_command_fallback` | setuptools_scm | stays in setuptools_scm | setuptools_scm only |

