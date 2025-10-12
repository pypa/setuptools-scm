# Migration Progress

## Phase Completion Checklist

- [ ] Phase 1: Setup vcs_versioning Package Structure
  - [ ] Update pyproject.toml with dependencies
  - [ ] Add entry points
  - [ ] Create directory structure

- [ ] Phase 2: Move Core Functionality to vcs_versioning
  - [ ] Move core APIs (config, scm_version, version_cls)
  - [ ] Move VCS backends (git, hg, hg_git, scm_workdir)
  - [ ] Move discovery module
  - [ ] Move utilities
  - [ ] Move CLI
  - [ ] Split pyproject reading

- [ ] Phase 3: Create Backward Compatibility Layer in vcs_versioning
  - [ ] Create compat.py module
  - [ ] Handle legacy entry point names
  - [ ] Support both tool.setuptools_scm and tool.vcs-versioning

- [ ] Phase 4: Update vcs_versioning Public API
  - [ ] Update __init__.py exports
  - [ ] Export Configuration, ScmVersion, Version classes
  - [ ] Export default constants

- [ ] Phase 5: Rebuild setuptools_scm as Integration Layer
  - [ ] Update dependencies to include vcs-versioning
  - [ ] Create re-export stubs
  - [ ] Update _integration/ imports
  - [ ] Update entry points

- [ ] Phase 6: Move and Update Tests
  - [ ] Move VCS/core tests to vcs_versioning
  - [ ] Update imports in moved tests
  - [ ] Keep integration tests in setuptools_scm
  - [ ] Update integration test imports

- [ ] Phase 7: Progress Tracking & Commits
  - [x] Create .wip/ directory
  - [ ] Make phase commits
  - [ ] Test after each commit

- [ ] Phase 8: CI/CD Updates
  - [ ] Update GitHub Actions (if exists)
  - [ ] Validate local testing

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

