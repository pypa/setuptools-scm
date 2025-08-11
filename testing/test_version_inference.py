from __future__ import annotations

from setuptools_scm._integration.pyproject_reading import PyProjectData
from setuptools_scm._integration.version_inference import VersionInferenceConfig
from setuptools_scm._integration.version_inference import VersionInferenceError
from setuptools_scm._integration.version_inference import VersionInferenceException
from setuptools_scm._integration.version_inference import VersionInferenceNoOp
from setuptools_scm._integration.version_inference import get_version_inference_config


class TestVersionInferenceDecision:
    """Test the version inference decision logic."""

    def test_version_already_set_by_infer_with_overrides(self) -> None:
        """Test that we proceed when version was set by infer_version but overrides provided."""
        result = get_version_inference_config(
            dist_name="test_package",
            current_version="1.0.0",
            pyproject_data=PyProjectData.for_testing(True, True, True),
            overrides={"key": "value"},
            was_set_by_infer=True,
        )

        assert isinstance(result, VersionInferenceConfig)
        assert result.dist_name == "test_package"
        assert result.overrides == {"key": "value"}

    def test_version_already_set_by_infer_no_overrides(self) -> None:
        """Test that we allow re-inferring when version was set by infer_version and overrides=None (another infer_version call)."""
        result = get_version_inference_config(
            dist_name="test_package",
            current_version="1.0.0",
            pyproject_data=PyProjectData.for_testing(True, True, True),
            overrides=None,
            was_set_by_infer=True,
        )

        assert isinstance(result, VersionInferenceConfig)
        assert result.dist_name == "test_package"
        assert result.overrides is None

    def test_version_already_set_by_infer_empty_overrides(self) -> None:
        """Test that we don't re-infer when version was set by infer_version with empty overrides (version_keyword call)."""
        result = get_version_inference_config(
            dist_name="test_package",
            current_version="1.0.0",
            pyproject_data=PyProjectData.for_testing(True, True, True),
            overrides={},
            was_set_by_infer=True,
        )

        assert isinstance(result, VersionInferenceNoOp)

    def test_version_already_set_by_something_else(self) -> None:
        """Test that we return error when version was set by something else."""
        result = get_version_inference_config(
            dist_name="test_package",
            current_version="1.0.0",
            pyproject_data=PyProjectData.for_testing(True, True, True),
            overrides=None,
            was_set_by_infer=False,
        )

        assert isinstance(result, VersionInferenceError)
        assert result.message == "version of test_package already set"
        assert result.should_warn is True

    def test_setuptools_scm_package(self) -> None:
        """Test that we don't infer for setuptools-scm package itself."""
        result = get_version_inference_config(
            dist_name="setuptools-scm",
            current_version=None,
            pyproject_data=PyProjectData.for_testing(True, True, True),
        )

        assert isinstance(result, VersionInferenceNoOp)

    def test_no_pyproject_toml(self) -> None:
        """Test that we don't infer when no pyproject.toml exists."""
        # When no pyproject.toml exists, the integration points should return early
        # and not call get_version_inference_config at all.
        # This test is no longer needed as pyproject_data is always required.

    def test_no_setuptools_scm_config_infer_version(self) -> None:
        """Test that we don't infer when setuptools-scm is not configured and infer_version called."""
        result = get_version_inference_config(
            dist_name="test_package",
            current_version=None,
            pyproject_data=PyProjectData.for_testing(False, False, True),
            overrides=None,  # infer_version call
        )

        assert isinstance(result, VersionInferenceNoOp)

    def test_no_setuptools_scm_config_version_keyword(self) -> None:
        """Test that we DO infer when setuptools-scm is not configured but use_scm_version=True."""
        result = get_version_inference_config(
            dist_name="test_package",
            current_version=None,
            pyproject_data=PyProjectData.for_testing(False, False, True),
            overrides={},  # version_keyword call with use_scm_version=True
        )

        assert isinstance(result, VersionInferenceConfig)
        assert result.dist_name == "test_package"
        assert result.overrides == {}

    def test_setuptools_scm_required_no_project_section_infer_version(self) -> None:
        """Test that we don't infer when setuptools-scm is required but no project section and infer_version called."""
        result = get_version_inference_config(
            dist_name="test_package",
            current_version=None,
            pyproject_data=PyProjectData.for_testing(True, False, False),
            overrides=None,  # infer_version call
        )

        assert isinstance(result, VersionInferenceNoOp)

    def test_setuptools_scm_required_no_project_section_version_keyword(self) -> None:
        """Test that we DO infer when setuptools-scm is required but no project section and use_scm_version=True."""
        result = get_version_inference_config(
            dist_name="test_package",
            current_version=None,
            pyproject_data=PyProjectData.for_testing(True, False, False),
            overrides={},  # version_keyword call with use_scm_version=True
        )

        assert isinstance(result, VersionInferenceConfig)
        assert result.dist_name == "test_package"
        assert result.overrides == {}

    def test_setuptools_scm_required_no_project_section_version_keyword_with_config(
        self,
    ) -> None:
        """Test that we DO infer when setuptools-scm is required but no project section and use_scm_version={config}."""
        overrides = {"version_scheme": "calver"}
        result = get_version_inference_config(
            dist_name="test_package",
            current_version=None,
            pyproject_data=PyProjectData.for_testing(True, False, False),
            overrides=overrides,  # version_keyword call with use_scm_version={config}
        )

        assert isinstance(result, VersionInferenceConfig)
        assert result.dist_name == "test_package"
        assert result.overrides == overrides

    def test_setuptools_scm_required_with_project_section(self) -> None:
        """Test that we infer when setuptools-scm is required and project section exists."""
        result = get_version_inference_config(
            dist_name="test_package",
            current_version=None,
            pyproject_data=PyProjectData.for_testing(True, False, True),
        )

        assert isinstance(result, VersionInferenceConfig)
        assert result.dist_name == "test_package"

    def test_tool_section_present(self) -> None:
        """Test that we infer when tool section is present."""
        result = get_version_inference_config(
            dist_name="test_package",
            current_version=None,
            pyproject_data=PyProjectData.for_testing(False, True, False),
        )

        assert isinstance(result, VersionInferenceConfig)
        assert result.dist_name == "test_package"

    def test_both_required_and_tool_section(self) -> None:
        """Test that we infer when both required and tool section are present."""
        result = get_version_inference_config(
            dist_name="test_package",
            current_version=None,
            pyproject_data=PyProjectData.for_testing(True, True, True),
        )

        assert isinstance(result, VersionInferenceConfig)
        assert result.dist_name == "test_package"

    def test_none_dist_name(self) -> None:
        """Test that we handle None dist_name correctly."""
        result = get_version_inference_config(
            dist_name=None,
            current_version=None,
            pyproject_data=PyProjectData.for_testing(True, True, True),
        )

        assert isinstance(result, VersionInferenceConfig)
        assert result.dist_name is None

    def test_version_already_set_none_dist_name(self) -> None:
        """Test that we handle None dist_name in error case."""
        result = get_version_inference_config(
            dist_name=None,
            current_version="1.0.0",
            pyproject_data=PyProjectData.for_testing(True, True, True),
            overrides=None,
            was_set_by_infer=False,
        )

        assert isinstance(result, VersionInferenceError)
        assert result.message == "version of None already set"

    def test_overrides_passed_through(self) -> None:
        """Test that overrides are passed through to the config."""
        overrides = {"version_scheme": "calver"}
        result = get_version_inference_config(
            dist_name="test_package",
            current_version=None,
            pyproject_data=PyProjectData.for_testing(True, True, True),
            overrides=overrides,
        )

        assert isinstance(result, VersionInferenceConfig)
        assert result.overrides == overrides


class TestPyProjectData:
    """Test the PyProjectData dataclass."""

    def test_pyproject_data_creation(self) -> None:
        """Test creating PyProjectData instances."""
        data = PyProjectData.for_testing(True, False, True)
        assert data.is_required is True
        assert data.section_present is False
        assert data.project_present is True

    def test_pyproject_data_equality(self) -> None:
        """Test PyProjectData equality."""
        data1 = PyProjectData.for_testing(True, False, True)
        data2 = PyProjectData.for_testing(True, False, True)
        data3 = PyProjectData.for_testing(False, False, True)

        assert data1 == data2
        assert data1 != data3


class TestVersionInferenceConfig:
    """Test the VersionInferenceConfig dataclass."""

    def test_config_creation(self) -> None:
        """Test creating VersionInferenceConfig instances."""
        pyproject_data = PyProjectData.for_testing(True, True, True)
        config = VersionInferenceConfig(
            dist_name="test_package",
            pyproject_data=pyproject_data,
            overrides={"key": "value"},
        )

        assert config.dist_name == "test_package"
        assert config.pyproject_data == pyproject_data
        assert config.overrides == {"key": "value"}


class TestVersionInferenceError:
    """Test the VersionInferenceError dataclass."""

    def test_error_creation(self) -> None:
        """Test creating VersionInferenceError instances."""
        error = VersionInferenceError("test message", should_warn=True)
        assert error.message == "test message"
        assert error.should_warn is True

    def test_error_default_warn(self) -> None:
        """Test VersionInferenceError default should_warn value."""
        error = VersionInferenceError("test message")
        assert error.should_warn is False


class TestVersionInferenceException:
    """Test the VersionInferenceException dataclass."""

    def test_exception_creation(self) -> None:
        """Test creating VersionInferenceException instances."""
        original_exception = ValueError("test error")
        wrapper = VersionInferenceException(original_exception)
        assert wrapper.exception == original_exception
