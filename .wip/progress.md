# Migration Progress

## Phase Completion Checklist

- [x] Phase 1: Setup vcs_versioning Package Structure
  - [x] Update pyproject.toml with dependencies
  - [x] Add entry points
  - [x] Create directory structure

- [x] Phase 2: Move Core Functionality to vcs_versioning
  - [x] Move core APIs (config, scm_version, version_cls)
  - [x] Move VCS backends (git, hg, hg_git, scm_workdir)
  - [x] Move discovery module
  - [x] Move utilities
  - [x] Move CLI
  - [x] Split pyproject reading

- [x] Phase 3: Create Backward Compatibility Layer in vcs_versioning
  - [x] Create compat.py module
  - [x] Handle legacy entry point names
  - [x] Support both tool.setuptools_scm and tool.vcs-versioning

- [x] Phase 4: Update vcs_versioning Public API
  - [x] Update __init__.py exports
  - [x] Export Configuration, ScmVersion, Version classes
  - [x] Export default constants

- [x] Phase 5: Rebuild setuptools_scm as Integration Layer
  - [x] Update dependencies to include vcs-versioning
  - [x] Create re-export stubs
  - [x] Update _integration/ imports
  - [x] Update entry points

- [x] Phase 6: Move and Update Tests
  - [x] Move VCS/core tests to vcs_versioning
  - [x] Update imports in moved tests
  - [x] Keep integration tests in setuptools_scm
  - [x] Update integration test imports

- [x] Phase 7: Progress Tracking & Commits
  - [x] Create .wip/ directory
  - [x] Make phase commits
  - [x] Test after each commit

- [x] Phase 8: CI/CD Updates
  - [x] Update GitHub Actions (if exists)
  - [x] Validate local testing

## Current Status

Phase 1: Completed - Package structure set up
Phase 2: In progress - Core functionality moved, imports being updated

### Phase 1 Completed
- ✅ Updated pyproject.toml with dependencies
- ✅ Added entry points for version_scheme, local_scheme, parse_scm, parse_scm_fallback
- ✅ Created directory structure (_backends/)

### Phase 2 Progress
- ✅ Moved utility files (_run_cmd, _node_utils, _modify_version, _types, _entrypoints, _log, _compat, _overrides, _requirement_cls, _version_cls)
- ✅ Moved VCS backends (git, hg, hg_git) to _backends/
- ✅ Moved scm_workdir to _backends/
- ✅ Moved discover
- ✅ Moved fallbacks (as _fallbacks)
- ✅ Moved CLI modules
- ✅ Moved config (as public config.py)
- ✅ Moved version (as _version_schemes.py)
- ✅ Created scm_version.py (currently re-exports from _version_schemes)
- ✅ Moved _get_version_impl
- ✅ Moved integration utility (_integration.py)
- ✅ Moved toml utility (_toml.py)
- ✅ Created _pyproject_reading.py with core functionality
- ✅ Updated imports in moved files (partially done)
- ✅ Created public __init__.py with API exports

### Next Steps
- Fix remaining import errors
- Test basic imports
- Commit Phase 1 & 2 work

## Latest Status (October 12, 2025 - Updated)

### ✅ COMPLETED - ALL PHASES
- **Phase 1-2**: Package structure and code movement complete
- **Phase 3**: Backward compatibility layer complete
  - Circular imports resolved, ScmVersion in _version_schemes
  - Re-export stubs in setuptools_scm for backward compatibility
- **Phase 4**: Public API properly exported
  - vcs_versioning exports Configuration, ScmVersion, Version
  - setuptools_scm re-exports for backward compatibility
- **Phase 5**: Integration layer rebuilt
  - setuptools_scm depends on vcs-versioning
  - Entry points properly distributed between packages
  - File finders remain in setuptools_scm
- **Phase 6**: Test migration complete
  - VCS-agnostic tests moved to vcs-versioning (79 tests)
  - Integration tests remain in setuptools_scm (329 tests)
  - All test imports fixed to use correct modules
- **Phase 7**: Progress tracked with regular commits
- **Phase 8**: CI/CD ready
  - uv workspace configured
  - Both packages build successfully
  - Test suite passes locally

### 🎉 Logging Unification Complete
- **Separate root loggers** for vcs_versioning and setuptools_scm
- **Entry point configuration** at CLI and setuptools integration
- **Central logger registry** with LOGGER_NAMES
- **Environment variables**: VCS_VERSIONING_DEBUG and SETUPTOOLS_SCM_DEBUG
- **Standard logging pattern**: All modules use logging.getLogger(__name__)

### 📦 Build Status
- `uv sync` successful
- setuptools-scm: version 9.2.2.dev20+g6e22672.d20251012
- vcs-versioning: version 0.0.1
- Both packages install and import correctly

### 🧪 Test Results - ALL PASSING ✅
- **vcs-versioning**: 79 passed
- **setuptools_scm**: 329 passed, 10 skipped, 1 xfailed
- **Total**: 408 tests passing
- Test run time: ~15s with parallel execution

### 🔧 Key Fixes Applied
1. Empty tag regex deprecation warning properly emitted
2. Test mocks patching actual module locations
3. Missing backward compat imports (strip_path_suffix, __main__.py)
4. setuptools.dynamic.version conflict warning
5. Test patches for _git module vs re-exported git

