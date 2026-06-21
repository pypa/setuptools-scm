from __future__ import annotations

import warnings

from types import SimpleNamespace
from typing import Any

import pytest

from setuptools_scm._integration.pyproject_reading import PyProjectData
from setuptools_scm._integration.version_inference import VersionAlreadySetWarning
from setuptools_scm._integration.version_inference import VersionInferenceConfig
from setuptools_scm._integration.version_inference import VersionInferenceNoOp
from setuptools_scm._integration.version_inference import VersionInferenceResult
from setuptools_scm._integration.version_inference import _should_write_to_source
from setuptools_scm._integration.version_inference import get_version_inference_config

# Common test data
PYPROJECT = SimpleNamespace(
    DEFAULT=PyProjectData.for_testing(
        tool_name="setuptools_scm",
        is_required=True,
        section_present=True,
        project_present=True,
    ),
    WITHOUT_TOOL_SECTION=PyProjectData.for_testing(
        tool_name="setuptools_scm",
        is_required=True,
        section_present=False,
        project_present=True,
    ),
    ONLY_REQUIRED=PyProjectData.for_testing(
        tool_name="setuptools_scm",
        is_required=True,
        section_present=False,
        project_present=False,
    ),
    WITHOUT_PROJECT=PyProjectData.for_testing(
        tool_name="setuptools_scm",
        is_required=True,
        section_present=True,
        project_present=False,
    ),
)

OVERRIDES = SimpleNamespace(
    NOT_GIVEN=None,
    EMPTY={},
    CALVER={"version_scheme": "calver"},
    UNRELATED={"key": "value"},
)


WARNING_PACKAGE = VersionAlreadySetWarning(dist_name="test_package")
WARNING_NO_PACKAGE = VersionAlreadySetWarning(dist_name=None)

NOOP = VersionInferenceNoOp()


def expect_config(
    *,
    dist_name: str | None = "test_package",
    current_version: str | None,
    pyproject_data: PyProjectData = PYPROJECT.DEFAULT,
    overrides: dict[str, Any] | None = None,
    expected: type[VersionInferenceConfig]
    | VersionAlreadySetWarning
    | VersionInferenceNoOp,
) -> None:
    """Helper to test get_version_inference_config and assert expected result type."""
    __tracebackhide__ = True
    result = get_version_inference_config(
        dist_name=dist_name,
        current_version=current_version,
        pyproject_data=pyproject_data,
        overrides=overrides,
    )

    expectation: VersionInferenceResult
    if expected == VersionInferenceConfig:
        expectation = VersionInferenceConfig(
            dist_name=dist_name,
            pyproject_data=pyproject_data,
            overrides=overrides,
        )
    else:
        assert isinstance(expected, (VersionInferenceNoOp, VersionAlreadySetWarning))
        expectation = expected

    assert result == expectation


infer_implied = pytest.mark.parametrize(
    ("overrides", "pyproject_data"),
    [
        pytest.param(
            OVERRIDES.EMPTY, PYPROJECT.DEFAULT, id="empty_overrides_default_pyproject"
        ),
        pytest.param(
            OVERRIDES.EMPTY,
            PYPROJECT.WITHOUT_TOOL_SECTION,
            id="empty_overrides_without_tool_section",
        ),
        pytest.param(
            OVERRIDES.NOT_GIVEN,
            PYPROJECT.DEFAULT,
            id="infer_version_default_pyproject",
        ),
    ],
)


@pytest.mark.parametrize("package_name", ["test_package", None])
@infer_implied
def test_implied_with_version_warns(
    package_name: str | None,
    overrides: dict[str, Any] | None,
    pyproject_data: PyProjectData,
) -> None:
    expect_config(
        dist_name=package_name,
        current_version="1.0.0",
        pyproject_data=pyproject_data,
        overrides=overrides,
        expected=WARNING_PACKAGE if package_name else WARNING_NO_PACKAGE,
    )


@pytest.mark.parametrize("package_name", ["test_package", None])
@infer_implied
def test_implied_without_version_infers(
    package_name: str | None,
    overrides: dict[str, Any] | None,
    pyproject_data: PyProjectData,
) -> None:
    expect_config(
        dist_name=package_name,
        current_version=None,
        pyproject_data=pyproject_data,
        overrides=overrides,
        expected=VersionInferenceConfig,
    )


def test_no_config_no_infer() -> None:
    expect_config(
        current_version=None,
        pyproject_data=PYPROJECT.WITHOUT_TOOL_SECTION,
        overrides=OVERRIDES.NOT_GIVEN,
        expected=NOOP,
    )


class TestVersionInferenceDecision:
    """Test the version inference decision logic."""

    def test_setuptools_scm_required_no_project_section_infer_version(self) -> None:
        """We don't infer without tool section even if required: infer_version path."""
        expect_config(
            current_version=None,
            pyproject_data=PYPROJECT.ONLY_REQUIRED,
            overrides=None,
            expected=NOOP,
        )

    def test_setuptools_scm_required_no_project_section_version_keyword(self) -> None:
        """Test that we DO infer when setuptools-scm is required but no project section and use_scm_version=True."""
        expect_config(
            current_version=None,
            pyproject_data=PYPROJECT.ONLY_REQUIRED,
            overrides=OVERRIDES.EMPTY,
            expected=VersionInferenceConfig,
        )

    def test_setuptools_scm_required_no_project_section_version_keyword_with_config(
        self,
    ) -> None:
        """Test that we DO infer when setuptools-scm is required but no project section and use_scm_version={config}."""
        expect_config(
            current_version=None,
            pyproject_data=PYPROJECT.ONLY_REQUIRED,
            overrides=OVERRIDES.CALVER,
            expected=VersionInferenceConfig,
        )

    def test_tool_section_present(self) -> None:
        """We infer when tool section is present."""
        expect_config(
            current_version=None,
            pyproject_data=PYPROJECT.WITHOUT_PROJECT,
            expected=VersionInferenceConfig,
        )

    def test_simple_extra_with_dynamic_version_infers(self) -> None:
        """We infer when setuptools-scm[simple] is in build-system.requires and version is dynamic."""
        pyproject_data = PyProjectData.for_testing(
            tool_name="setuptools_scm",
            is_required=True,
            section_present=False,
            project_present=True,
            has_dynamic_version=True,
            build_requires=["setuptools-scm[simple]"],
        )
        expect_config(
            current_version=None,
            pyproject_data=pyproject_data,
            expected=VersionInferenceConfig,
        )

    def test_simple_extra_without_dynamic_version_no_infer(self) -> None:
        """We don't infer when setuptools-scm[simple] is present but version is not dynamic."""
        pyproject_data = PyProjectData.for_testing(
            tool_name="setuptools_scm",
            is_required=True,
            section_present=False,
            project_present=True,
            has_dynamic_version=False,
            build_requires=["setuptools-scm[simple]"],
        )
        expect_config(
            current_version=None,
            pyproject_data=pyproject_data,
            expected=NOOP,
        )

    def test_no_simple_extra_with_dynamic_version_no_infer(self) -> None:
        """We don't infer when setuptools-scm (without simple extra) is present even with dynamic version."""
        pyproject_data = PyProjectData.for_testing(
            tool_name="setuptools_scm",
            is_required=True,
            section_present=False,
            project_present=True,
            has_dynamic_version=True,
            build_requires=["setuptools-scm"],
        )
        expect_config(
            current_version=None,
            pyproject_data=pyproject_data,
            expected=NOOP,
        )

    def test_simple_extra_no_project_section_no_infer(self) -> None:
        """We don't infer when setuptools-scm[simple] is present but no project section."""
        pyproject_data = PyProjectData.for_testing(
            tool_name="setuptools_scm",
            is_required=True,
            section_present=False,
            project_present=False,
            build_requires=["setuptools-scm[simple]"],
        )
        expect_config(
            current_version=None,
            pyproject_data=pyproject_data,
            expected=NOOP,
        )

    def test_simple_extra_with_version_warns(self) -> None:
        """We warn when setuptools-scm[simple] is present with dynamic version but version is already set."""
        pyproject_data = PyProjectData.for_testing(
            tool_name="setuptools_scm",
            is_required=True,
            section_present=False,
            project_present=True,
            has_dynamic_version=True,
            build_requires=["setuptools-scm[simple]"],
        )
        expect_config(
            current_version="1.0.0",
            pyproject_data=pyproject_data,
            expected=WARNING_PACKAGE,
        )


def _make_config(
    write_to_source: bool | None = None,
    tool_names: tuple[str, ...] = ("SETUPTOOLS_SCM", "VCS_VERSIONING"),
) -> Any:
    """Create a minimal Configuration-like object for _should_write_to_source tests."""
    from vcs_versioning._config import Configuration
    from vcs_versioning._environment import VcsEnvironment

    env = VcsEnvironment(tool_names=tool_names)
    config = Configuration(write_to_source=write_to_source, _env=env)
    return config


@pytest.mark.issue(1301)
class TestShouldWriteToSource:
    """Test the three-state write_to_source config + env var override."""

    def test_config_true_writes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("SETUPTOOLS_SCM_WRITE_TO_SOURCE", raising=False)
        config = _make_config(write_to_source=True)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            assert _should_write_to_source(config) is True
        assert not any(issubclass(x.category, DeprecationWarning) for x in w)

    def test_config_false_skips(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("SETUPTOOLS_SCM_WRITE_TO_SOURCE", raising=False)
        config = _make_config(write_to_source=False)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            assert _should_write_to_source(config) is False
        assert not any(issubclass(x.category, DeprecationWarning) for x in w)

    def test_config_unset_writes_with_deprecation_warning(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SETUPTOOLS_SCM_WRITE_TO_SOURCE", raising=False)
        monkeypatch.delenv("VCS_VERSIONING_WRITE_TO_SOURCE", raising=False)
        config = _make_config(write_to_source=None)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = _should_write_to_source(config)
        assert result is True
        dep_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
        assert len(dep_warnings) == 1
        assert "write_to_source" in str(dep_warnings[0].message)

    @pytest.mark.parametrize("env_val", ["1", "true", "yes", "True", "YES"])
    def test_env_var_truthy_overrides_config_false(
        self, monkeypatch: pytest.MonkeyPatch, env_val: str
    ) -> None:
        monkeypatch.setenv("SETUPTOOLS_SCM_WRITE_TO_SOURCE", env_val)
        config = _make_config(write_to_source=False)
        assert _should_write_to_source(config) is True

    @pytest.mark.parametrize("env_val", ["0", "false", "no", "False", "NO"])
    def test_env_var_falsy_overrides_config_true(
        self, monkeypatch: pytest.MonkeyPatch, env_val: str
    ) -> None:
        monkeypatch.setenv("SETUPTOOLS_SCM_WRITE_TO_SOURCE", env_val)
        config = _make_config(write_to_source=True)
        assert _should_write_to_source(config) is False

    def test_env_var_set_suppresses_deprecation_warning(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When env var is set, no deprecation warning even if config is unset."""
        monkeypatch.setenv("SETUPTOOLS_SCM_WRITE_TO_SOURCE", "1")
        config = _make_config(write_to_source=None)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            _should_write_to_source(config)
        assert not any(issubclass(x.category, DeprecationWarning) for x in w)
