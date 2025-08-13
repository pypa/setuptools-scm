from __future__ import annotations

from typing import Any

import pytest

from setuptools_scm._integration.pyproject_reading import PyProjectData
from setuptools_scm._integration.version_inference import VersionInferenceConfig
from setuptools_scm._integration.version_inference import VersionInferenceNoOp
from setuptools_scm._integration.version_inference import VersionInferenceWarning
from setuptools_scm._integration.version_inference import get_version_inference_config

# Common test data
DEFAULT_PYPROJECT_DATA = PyProjectData.for_testing(
    is_required=True, section_present=True, project_present=True
)


def expect_config(
    *,
    dist_name: str | None = "test_package",
    current_version: str | None,
    pyproject_data: PyProjectData = DEFAULT_PYPROJECT_DATA,
    overrides: dict[str, Any] | None = None,
    expected_type: type = VersionInferenceConfig,
    expected_message: str | None = None,
) -> None:
    """Helper to test get_version_inference_config and assert expected result type."""
    __tracebackhide__ = True
    result = get_version_inference_config(
        dist_name=dist_name,
        current_version=current_version,
        pyproject_data=pyproject_data,
        overrides=overrides,
    )

    if not isinstance(result, expected_type):
        pytest.fail(f"{type(result).__name__} != {expected_type.__name__}")

    if expected_type == VersionInferenceWarning and expected_message:
        assert isinstance(result, VersionInferenceWarning)
        assert expected_message in result.message
    elif expected_type == VersionInferenceConfig:
        assert isinstance(result, VersionInferenceConfig)
        assert result.dist_name == dist_name
        assert result.overrides == overrides


class TestVersionInferenceDecision:
    """Test the version inference decision logic."""

    def test_missing_version_with_overrides_triggers(self) -> None:
        """Test that version_keyword context with overrides infers when no existing version."""
        expect_config(
            current_version=None,  # version_keyword passes None when version was set by infer
            overrides={"key": "value"},
        )

    def test_overrides_on_existing_version_warns(self) -> None:
        """note: version_keyword opts out of inference if
        version is set by something else or overrides are empty"""
        expect_config(
            current_version="1.0.0",  # version set by something else (setup.cfg, etc.)
            overrides={"key": "value"},
            expected_type=VersionInferenceWarning,
            expected_message="version of test_package already set",
        )

    def test_version_already_set_no_overrides(self) -> None:
        """infer_version call with existing version warns when inference is implied."""
        expect_config(
            current_version="1.0.0",
            overrides=None,
            expected_type=VersionInferenceWarning,
            expected_message="version of test_package already set",
        )

    def test_version_keyword_with_empty_overrides(self) -> None:
        """Test that version_keyword context with empty overrides infers when no existing version."""
        expect_config(
            current_version=None,  # version_keyword handles early exit, so this is what we see
            overrides={},
        )

    def test_version_keyword_empty_overrides_existing_version(self) -> None:
        """Test that version_keyword context with empty overrides and existing version errors."""
        expect_config(
            current_version="1.0.0",  # version set by something else (setup.cfg, etc.)
            overrides={},
            expected_type=VersionInferenceWarning,
            expected_message="version of test_package already set",
        )

    def test_version_already_set_by_something_else(self) -> None:
        """infer_version call with existing version warns when inference is implied."""
        expect_config(
            current_version="1.0.0",
            overrides=None,
            expected_type=VersionInferenceWarning,
            expected_message="version of test_package already set",
        )

    def test_no_setuptools_scm_config_infer_version(self) -> None:
        """Test that we don't infer when setuptools-scm is not configured and infer_version called."""
        expect_config(
            current_version=None,
            pyproject_data=PyProjectData.for_testing(
                is_required=False, section_present=False, project_present=True
            ),
            overrides=None,
            expected_type=VersionInferenceNoOp,
        )

    def test_no_setuptools_scm_config_version_keyword(self) -> None:
        """We infer when setuptools-scm is not configured but use_scm_version=True."""
        expect_config(
            current_version=None,
            pyproject_data=PyProjectData.for_testing(
                is_required=False, section_present=False, project_present=True
            ),
            overrides={},
        )

    def test_setuptools_scm_required_no_project_section_infer_version(self) -> None:
        """We don't infer without tool section even if required: infer_version path."""
        expect_config(
            current_version=None,
            pyproject_data=PyProjectData.for_testing(
                is_required=True, section_present=False, project_present=False
            ),
            overrides=None,
            expected_type=VersionInferenceNoOp,
        )

    def test_setuptools_scm_required_no_project_section_version_keyword(self) -> None:
        """Test that we DO infer when setuptools-scm is required but no project section and use_scm_version=True."""
        expect_config(
            current_version=None,
            pyproject_data=PyProjectData.for_testing(
                is_required=True, section_present=False, project_present=False
            ),
            overrides={},
        )

    def test_setuptools_scm_required_no_project_section_version_keyword_with_config(
        self,
    ) -> None:
        """Test that we DO infer when setuptools-scm is required but no project section and use_scm_version={config}."""
        expect_config(
            current_version=None,
            pyproject_data=PyProjectData.for_testing(
                is_required=True, section_present=False, project_present=False
            ),
            overrides={"version_scheme": "calver"},
        )

    def test_setuptools_scm_required_with_project_section(self) -> None:
        """We only infer when tool section present, regardless of required/project presence."""
        expect_config(
            current_version=None,
            pyproject_data=PyProjectData.for_testing(
                is_required=True, section_present=False, project_present=True
            ),
            expected_type=VersionInferenceNoOp,
        )

    def test_tool_section_present(self) -> None:
        """We infer when tool section is present."""
        expect_config(
            current_version=None,
            pyproject_data=PyProjectData.for_testing(
                is_required=False, section_present=True, project_present=False
            ),
        )

    def test_both_required_and_tool_section(self) -> None:
        """Test that we infer when both required and tool section are present."""
        expect_config(
            current_version=None,
        )

    def test_none_dist_name(self) -> None:
        """Test that we handle None dist_name correctly."""
        expect_config(
            dist_name=None,
            current_version=None,
        )

    def test_version_already_set_none_dist_name(self) -> None:
        """infer_version call with None dist_name and existing version warns when inference is implied."""
        expect_config(
            dist_name=None,
            current_version="1.0.0",
            overrides=None,
            expected_type=VersionInferenceWarning,
            expected_message="version of None already set",
        )
