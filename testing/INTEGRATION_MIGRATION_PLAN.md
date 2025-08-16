## Setuptools integration test migration plan

Purpose: streamline/simplify integration codepaths and make tests faster and easier to write by preferring unit-level inference over setuptools-driven E2E where possible.

Reference helper for unit tests:

```python
from setuptools_scm._integration.pyproject_reading import PyProjectData
from setuptools_scm._integration.version_inference import infer_version_string

version = infer_version_string(
    dist_name="pkg",
    pyproject_data=PyProjectData.for_testing(project_present=True, section_present=True, project_name="pkg"),
    overrides={"fallback_version": "1.2.3"},
)
```

### Completed
- [x] Introduced `infer_version_string` pure helper to compute versions without a `Distribution` or `setup.py`.

### Migration candidates (replace E2E/Distribution-hook tests with unit inference)
- [ ] `testing/test_integration.py::test_pyproject_support`
  - Proposed unit: `test_infer_fallback_version_from_pyproject`
  - Notes: Use `PyProjectData.for_testing(..., section_present=True, project_present=True)` + overrides `{fallback_version: "12.34"}`.

- [ ] `testing/test_integration.py::test_setuptools_version_keyword_ensures_regex`
  - Proposed unit: `test_infer_tag_regex_from_overrides`
  - Notes: Create repo/tag in `wd`, call `infer_version_string(..., overrides={"tag_regex": "(1.0)"})`.

- [ ] `testing/test_basic_api.py::test_parentdir_prefix`
  - Proposed unit: `test_infer_parentdir_prefix_version`
  - Notes: Use directory name prefix and `{parentdir_prefix_version: "projectname-"}`.

- [ ] `testing/test_basic_api.py::test_fallback`
  - Proposed unit: `test_infer_fallback_version`
  - Notes: `{fallback_version: "12.34"}`.

- [ ] `testing/test_basic_api.py::test_empty_pretend_version`
  - Proposed unit: `test_infer_with_empty_pretend_uses_fallback`
  - Notes: Set `SETUPTOOLS_SCM_PRETEND_VERSION=""`, infer with fallback.

- [ ] `testing/test_basic_api.py::test_empty_pretend_version_named`
  - Proposed unit: `test_infer_with_empty_named_pretend_uses_fallback`
  - Notes: Use named pretend env var and fallback.

- [ ] `testing/test_regressions.py::test_use_scm_version_callable`
  - Proposed unit: `test_infer_with_callable_version_scheme`
  - Notes: Pass callable via `overrides={"version_scheme": callable}` to `infer_version_string`.

- [ ] `testing/test_git.py::test_root_relative_to`
  - Proposed unit: `test_configuration_absolute_root_resolution`
  - Notes: Assert `Configuration.absolute_root` behavior or use `Configuration.from_data(..., root/relative_to)`; avoid `setup.py`.

- [ ] `testing/test_git.py::test_root_search_parent_directories`
  - Proposed unit: `test_configuration_search_parent_directories`
  - Notes: Prefer `Configuration(search_parent_directories=True)` + direct `_get_version` or `infer_version_string`.

### Tests to keep as integration/E2E
- `testing/test_integration.py::test_integration_function_call_order`
  - Validates precedence/ordering between `infer_version` and `version_keyword` hooks on `Distribution`.

- `testing/test_integration.py::test_distribution_provides_extras`
  - Verifies installed distribution metadata (extras exposure).

- `testing/test_integration.py::test_git_archival_plugin_ignored`
  - Entry point filtering behavior.

- `testing/test_git.py::test_git_version_unnormalized_setuptools` (parameterized)
  - Asserts difference between file write (`write_to` non-normalized) vs setuptools-normalized dist metadata. Requires setuptools behavior; not reproducible by pure helper.

- Maintain a minimal smoke test to ensure `setup.py --version` works end-to-end (one per major path).

### Already covered by unit-level decision tests (no action)
- `testing/test_version_inference.py` suite
  - Exercises `get_version_inference_config` across configuration matrices using `PyProjectData.for_testing`.

### New unit tests to add (pure inference)
- [ ] `test_infer_local_scheme_no_local_version`
  - Use `PyProjectData.for_testing(section_present=True, project_present=True, local_scheme="no-local-version")`.

- [ ] `test_infer_with_env_pretend_version_and_metadata`
  - Set pretend version + metadata env vars; assert combined result via `infer_version_string`.

- [ ] `test_infer_respects_nested_scm_git_config`
  - Provide nested TOML-equivalent via `overrides={"scm": {"git": {"pre_parse": "fail_on_missing_submodules"}}}`.

### Notes and pitfalls
- Some behaviors are specific to setuptools (normalization of dist metadata vs written file contents) and should remain integration tests.
- Prefer `PyProjectData.for_testing(...)` to avoid file I/O in new unit tests.
- For tests that assert version-file writing, call `infer_version_string(..., force_write_version_files=True)` and set `write_to`/`version_file` in overrides.


