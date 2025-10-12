# Test Suite Status

## Tests to Move to vcs_versioning

- [ ] `test_git.py` - Git backend tests
- [ ] `test_mercurial.py` - Mercurial backend tests
- [ ] `test_hg_git.py` - HG-Git backend tests
- [ ] `test_version.py` - Version scheme tests
- [ ] `test_config.py` - Configuration tests
- [ ] `test_cli.py` - CLI tests
- [ ] `test_functions.py` - Core function tests
- [ ] `test_overrides.py` - Override tests
- [ ] `test_basic_api.py` - Basic API tests (parts)
- [ ] `conftest.py` - Shared fixtures
- [ ] `wd_wrapper.py` - Test helper

## Tests to Keep in setuptools_scm

- [ ] `test_integration.py` - Setuptools integration
- [ ] `test_pyproject_reading.py` - Pyproject reading (update imports)
- [ ] `test_version_inference.py` - Version inference
- [ ] `test_deprecation.py` - Deprecation warnings
- [ ] `test_regressions.py` - Regression tests
- [ ] `test_file_finder.py` - File finder (setuptools-specific)
- [ ] `test_internal_log_level.py` - Log level tests
- [ ] `test_main.py` - Main module tests
- [ ] `test_compat.py` - Compatibility tests
- [ ] `test_better_root_errors.py` - Error handling
- [ ] `test_expect_parse.py` - Parse expectations

## Test Execution Status

### vcs_versioning tests
```
Not yet run
```

### setuptools_scm tests
```
Not yet run
```

## Notes

- File finders stay in setuptools_scm (setuptools-specific)
- Update imports in all tests to use vcs_versioning where appropriate
- Ensure shared fixtures work for both test suites

