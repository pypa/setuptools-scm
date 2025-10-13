from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from setuptools_scm._integration.pyproject_reading import PyProjectData
from setuptools_scm._integration.version_inference import VersionInferenceConfig
from setuptools_scm._integration.version_inference import VersionInferenceNoOp
from setuptools_scm._integration.version_inference import VersionInferenceResult
from setuptools_scm._integration.version_inference import VersionInferenceWarning
from setuptools_scm._integration.version_inference import get_version_inference_config

# Common test data
PYPROJECT = SimpleNamespace(
    DEFAULT=PyProjectData.for_testing(
        is_required=True, section_present=True, project_present=True
    ),
    WITHOUT_TOOL_SECTION=PyProjectData.for_testing(
        is_required=True, section_present=False, project_present=True
    ),
    ONLY_REQUIRED=PyProjectData.for_testing(
        is_required=True, section_present=False, project_present=False
    ),
    WITHOUT_PROJECT=PyProjectData.for_testing(
        is_required=True, section_present=True, project_present=False
    ),
)

OVERRIDES = SimpleNamespace(
    NOT_GIVEN=None,
    EMPTY={},
    CALVER={"version_scheme": "calver"},
    UNRELATED={"key": "value"},
)


WARNING_PACKAGE = VersionInferenceWarning(
    message="version of test_package already set",
)
WARNING_NO_PACKAGE = VersionInferenceWarning(
    message="version of None already set",
)

NOOP = VersionInferenceNoOp()


def expect_config(
    *,
    dist_name: str | None = "test_package",
    current_version: str | None,
    pyproject_data: PyProjectData = PYPROJECT.DEFAULT,
    overrides: dict[str, Any] | None = None,
    expected: type[VersionInferenceConfig]
    | VersionInferenceWarning
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
        assert isinstance(expected, (VersionInferenceNoOp, VersionInferenceWarning))
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
