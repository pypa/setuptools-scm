# Test Suite Status

## ✅ Tests Moved to vcs_versioning (testingB/)

- [x] `test_git.py` - Git backend tests
- [x] `test_mercurial.py` - Mercurial backend tests
- [x] `test_hg_git.py` - HG-Git backend tests
- [x] `test_version.py` - Version scheme tests
- [x] `test_config.py` - Configuration tests
- [x] `test_functions.py` - Core function tests
- [x] `test_overrides.py` - Override tests
- [x] `test_basic_api.py` - Basic API tests
- [x] `conftest.py` - Shared fixtures (via pytest plugin)

## ✅ Tests Kept in setuptools_scm (testing/)

- [x] `test_integration.py` - Setuptools integration
- [x] `test_pyproject_reading.py` - Pyproject reading
- [x] `test_version_inference.py` - Version inference
- [x] `test_deprecation.py` - Deprecation warnings
- [x] `test_regressions.py` - Regression tests
- [x] `test_file_finder.py` - File finder (setuptools-specific)
- [x] `test_internal_log_level.py` - Log level tests
- [x] `test_main.py` - Main module tests
- [x] `test_compat.py` - Compatibility tests
- [x] `test_better_root_errors.py` - Error handling (updated imports)
- [x] `test_expect_parse.py` - Parse expectations
- [x] `test_cli.py` - CLI tests (updated imports)

## Test Execution Status

### Combined test suite
```
408 passed, 10 skipped, 1 xfailed in 16-17s
```

## Notes

- ✅ File finders stay in setuptools_scm (setuptools-specific)
- ✅ All test imports updated to use vcs_versioning where appropriate
- ✅ Shared test fixtures work via `vcs_versioning.test_api` pytest plugin
- ✅ Test directory renamed to `testingB/` in vcs-versioning to avoid conftest conflicts
- ✅ Pytest plugin properly configured in both `pyproject.toml` files

