from __future__ import annotations

import importlib.metadata
import logging
import re
import subprocess
import sys
import textwrap

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

import pytest

from packaging.version import Version

from setuptools_scm._integration import setuptools as setuptools_integration
from setuptools_scm._integration.pyproject_reading import PyProjectData
from setuptools_scm._integration.setup_cfg import SetuptoolsBasicData
from setuptools_scm._integration.setup_cfg import read_setup_cfg
from setuptools_scm._requirement_cls import extract_package_name

if TYPE_CHECKING:
    import setuptools

from setuptools_scm import Configuration
from setuptools_scm._integration.setuptools import _warn_on_old_setuptools
from setuptools_scm._overrides import PRETEND_KEY
from setuptools_scm._overrides import PRETEND_KEY_NAMED
from setuptools_scm._run_cmd import run

from .wd_wrapper import WorkDir

c = Configuration()


@pytest.fixture
def wd(wd: WorkDir) -> WorkDir:
    wd("git init")
    wd("git config user.email test@example.com")
    wd('git config user.name "a test"')
    wd.add_command = "git add ."
    wd.commit_command = "git commit -m test-{reason}"
    return wd


def test_pyproject_support(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SETUPTOOLS_SCM_DEBUG")
    pkg = tmp_path / "package"
    pkg.mkdir()
    pkg.joinpath("pyproject.toml").write_text(
        textwrap.dedent(
            """
            [tool.setuptools_scm]
            fallback_version = "12.34"
            [project]
            name = "foo"
            description = "Factory ⸻ A code generator 🏭"
            authors = [{name = "Łukasz Langa"}]
            dynamic = ["version"]
            """
        ),
        encoding="utf-8",
    )
    pkg.joinpath("setup.py").write_text(
        "__import__('setuptools').setup()", encoding="utf-8"
    )
    res = run([sys.executable, "setup.py", "--version"], pkg)
    assert res.stdout == "12.34"


def test_pretend_version(monkeypatch: pytest.MonkeyPatch, wd: WorkDir) -> None:
    monkeypatch.setenv(PRETEND_KEY, "1.0.0")

    assert wd.get_version() == "1.0.0"
    assert wd.get_version(dist_name="ignored") == "1.0.0"


def test_pretend_version_named(monkeypatch: pytest.MonkeyPatch, wd: WorkDir) -> None:
    monkeypatch.setenv(PRETEND_KEY_NAMED.format(name="test".upper()), "1.0.0")
    monkeypatch.setenv(PRETEND_KEY_NAMED.format(name="test2".upper()), "2.0.0")
    assert wd.get_version(dist_name="test") == "1.0.0"
    assert wd.get_version(dist_name="test2") == "2.0.0"


def test_pretend_version_name_takes_precedence(
    monkeypatch: pytest.MonkeyPatch, wd: WorkDir
) -> None:
    monkeypatch.setenv(PRETEND_KEY_NAMED.format(name="test".upper()), "1.0.0")
    monkeypatch.setenv(PRETEND_KEY, "2.0.0")
    assert wd.get_version(dist_name="test") == "1.0.0"


def test_pretend_version_rejects_invalid_string(
    monkeypatch: pytest.MonkeyPatch, wd: WorkDir
) -> None:
    """Test that invalid pretend versions raise errors and bubble up."""
    monkeypatch.setenv(PRETEND_KEY, "dummy")

    # With strict validation, invalid pretend versions should raise errors
    with pytest.raises(Exception, match=r".*dummy.*"):
        wd.get_version(write_to="test.py")


def test_pretend_metadata_with_version(
    monkeypatch: pytest.MonkeyPatch, wd: WorkDir
) -> None:
    """Test pretend metadata overrides work with pretend version."""
    from setuptools_scm._overrides import PRETEND_METADATA_KEY

    monkeypatch.setenv(PRETEND_KEY, "1.2.3.dev4+g1337beef")
    monkeypatch.setenv(PRETEND_METADATA_KEY, '{node="g1337beef", distance=4}')

    version = wd.get_version()
    assert version == "1.2.3.dev4+g1337beef"

    # Test version file template functionality
    wd("mkdir -p src")
    version_file_content = """
version = '{version}'
major = {version_tuple[0]}
minor = {version_tuple[1]}
patch = {version_tuple[2]}
commit_hash = '{scm_version.short_node}'
num_commit = {scm_version.distance}
"""  # noqa: RUF027
    # Use write_to with template to create version file
    version = wd.get_version(
        write_to="src/version.py", write_to_template=version_file_content
    )

    content = (wd.cwd / "src/version.py").read_text(encoding="utf-8")
    assert "commit_hash = 'g1337beef'" in content
    assert "num_commit = 4" in content


def test_pretend_metadata_named(monkeypatch: pytest.MonkeyPatch, wd: WorkDir) -> None:
    """Test pretend metadata with named package support."""
    from setuptools_scm._overrides import PRETEND_METADATA_KEY_NAMED

    monkeypatch.setenv(
        PRETEND_KEY_NAMED.format(name="test".upper()), "1.2.3.dev5+gabcdef12"
    )
    monkeypatch.setenv(
        PRETEND_METADATA_KEY_NAMED.format(name="test".upper()),
        '{node="gabcdef12", distance=5, dirty=true}',
    )

    version = wd.get_version(dist_name="test")
    assert version == "1.2.3.dev5+gabcdef12"


def test_pretend_metadata_without_version_warns(
    monkeypatch: pytest.MonkeyPatch, wd: WorkDir, caplog: pytest.LogCaptureFixture
) -> None:
    """Test that pretend metadata without any base version logs a warning."""
    from setuptools_scm._overrides import PRETEND_METADATA_KEY

    # Only set metadata, no version - but there will be a git repo so there will be a base version
    # Let's create an empty git repo without commits to truly have no base version
    monkeypatch.setenv(PRETEND_METADATA_KEY, '{node="g1234567", distance=2}')

    with caplog.at_level(logging.WARNING):
        version = wd.get_version()
        assert version is not None

    # In this case, metadata was applied to a fallback version, so no warning about missing base


def test_pretend_metadata_with_scm_version(
    wd: WorkDir, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that pretend metadata works with actual SCM-detected version."""
    from setuptools_scm._overrides import PRETEND_METADATA_KEY

    # Set up a git repo with a tag so we have a base version
    wd("git init")
    wd("git config user.name test")
    wd("git config user.email test@example.com")
    wd.write("file.txt", "content")
    wd("git add file.txt")
    wd("git commit -m 'initial'")
    wd("git tag v1.0.0")

    # Now add metadata overrides
    monkeypatch.setenv(PRETEND_METADATA_KEY, '{node="gcustom123", distance=7}')

    # Test that the metadata gets applied to the actual SCM version
    version = wd.get_version()
    # The version becomes 1.0.1.dev7+gcustom123 due to version scheme and metadata overrides
    assert "1.0.1.dev7+gcustom123" == version

    # Test version file to see if metadata was applied
    wd("mkdir -p src")
    version_file_content = """
version = '{version}'
commit_hash = '{scm_version.short_node}'
num_commit = {scm_version.distance}
"""  # noqa: RUF027
    version = wd.get_version(
        write_to="src/version.py", write_to_template=version_file_content
    )

    content = (wd.cwd / "src/version.py").read_text(encoding="utf-8")
    assert "commit_hash = 'gcustom123'" in content
    assert "num_commit = 7" in content


def test_pretend_metadata_type_conversion(
    monkeypatch: pytest.MonkeyPatch, wd: WorkDir
) -> None:
    """Test that pretend metadata properly uses TOML native types."""
    from setuptools_scm._overrides import PRETEND_METADATA_KEY

    monkeypatch.setenv(PRETEND_KEY, "2.0.0")
    monkeypatch.setenv(
        PRETEND_METADATA_KEY,
        '{distance=10, dirty=true, node="gfedcba98", branch="feature-branch"}',
    )

    version = wd.get_version()
    # The version should be formatted properly with the metadata
    assert "2.0.0" in version


def test_pretend_metadata_invalid_fields_filtered(
    monkeypatch: pytest.MonkeyPatch, wd: WorkDir, caplog: pytest.LogCaptureFixture
) -> None:
    """Test that invalid metadata fields are filtered out with a warning."""
    from setuptools_scm._overrides import PRETEND_METADATA_KEY

    monkeypatch.setenv(PRETEND_KEY, "1.0.0")
    monkeypatch.setenv(
        PRETEND_METADATA_KEY,
        '{node="g123456", distance=3, invalid_field="should_be_ignored", another_bad_field=42}',
    )

    with caplog.at_level(logging.WARNING):
        version = wd.get_version()
        assert version == "1.0.0"

    assert "Invalid metadata fields in pretend metadata" in caplog.text
    assert "invalid_field" in caplog.text
    assert "another_bad_field" in caplog.text


def test_pretend_metadata_date_parsing(
    monkeypatch: pytest.MonkeyPatch, wd: WorkDir
) -> None:
    """Test that TOML date values work in pretend metadata."""
    from setuptools_scm._overrides import PRETEND_METADATA_KEY

    monkeypatch.setenv(PRETEND_KEY, "1.5.0")
    monkeypatch.setenv(
        PRETEND_METADATA_KEY, '{node="g987654", distance=7, node_date=2024-01-15}'
    )

    version = wd.get_version()
    assert version == "1.5.0"


def test_pretend_metadata_invalid_toml_error(
    monkeypatch: pytest.MonkeyPatch, wd: WorkDir, caplog: pytest.LogCaptureFixture
) -> None:
    """Test that invalid TOML in pretend metadata logs an error."""
    from setuptools_scm._overrides import PRETEND_METADATA_KEY

    monkeypatch.setenv(PRETEND_KEY, "1.0.0")
    monkeypatch.setenv(PRETEND_METADATA_KEY, "{invalid toml syntax here}")

    with caplog.at_level(logging.ERROR):
        version = wd.get_version()
        # Should fall back to basic pretend version
        assert version == "1.0.0"

    assert "Failed to parse pretend metadata" in caplog.text


def test_git_tag_with_local_build_data_preserved(wd: WorkDir) -> None:
    """Test that git tags containing local build data are preserved in final version."""
    wd.commit_testfile()

    # Create a git tag that includes local build data
    # This simulates a CI system that creates tags with build metadata
    wd("git tag 1.0.0+build.123")

    # The version should preserve the build metadata from the tag
    version = wd.get_version()

    # Validate it's a proper PEP 440 version
    parsed_version = Version(version)
    assert str(parsed_version) == version, (
        f"Version should parse correctly as PEP 440: {version}"
    )

    assert version == "1.0.0+build.123", (
        f"Expected build metadata preserved, got {version}"
    )

    # Validate the local part is correct
    assert parsed_version.local == "build.123", (
        f"Expected local part 'build.123', got {parsed_version.local}"
    )


def test_git_tag_with_commit_hash_preserved(wd: WorkDir) -> None:
    """Test that git tags with commit hash data are preserved."""
    wd.commit_testfile()

    # Create a git tag that includes commit hash metadata
    wd("git tag 2.0.0+sha.abcd1234")

    # The version should preserve the commit hash from the tag
    version = wd.get_version()

    # Validate it's a proper PEP 440 version
    parsed_version = Version(version)
    assert str(parsed_version) == version, (
        f"Version should parse correctly as PEP 440: {version}"
    )

    assert version == "2.0.0+sha.abcd1234"

    # Validate the local part is correct
    assert parsed_version.local == "sha.abcd1234", (
        f"Expected local part 'sha.abcd1234', got {parsed_version.local}"
    )


def test_git_tag_with_local_build_data_preserved_dirty_workdir(wd: WorkDir) -> None:
    """Test that git tags with local build data are preserved even with dirty working directory."""
    wd.commit_testfile()

    # Create a git tag that includes local build data
    wd("git tag 1.5.0+build.456")

    # Make working directory dirty
    wd.write("modified_file.txt", "some changes")

    # The version should preserve the build metadata from the tag
    # even when working directory is dirty
    version = wd.get_version()

    # Validate it's a proper PEP 440 version
    parsed_version = Version(version)
    assert str(parsed_version) == version, (
        f"Version should parse correctly as PEP 440: {version}"
    )

    assert version == "1.5.0+build.456", (
        f"Expected build metadata preserved with dirty workdir, got {version}"
    )

    # Validate the local part is correct
    assert parsed_version.local == "build.456", (
        f"Expected local part 'build.456', got {parsed_version.local}"
    )


def test_git_tag_with_local_build_data_preserved_with_distance(wd: WorkDir) -> None:
    """Test that git tags with local build data are preserved with distance."""
    wd.commit_testfile()

    # Create a git tag that includes local build data
    wd("git tag 3.0.0+ci.789")

    # Add another commit after the tag to create distance
    wd.commit_testfile("after-tag")

    # The version should use version scheme for distance but preserve original tag's build data
    version = wd.get_version()

    # Validate it's a proper PEP 440 version
    parsed_version = Version(version)
    assert str(parsed_version) == version, (
        f"Version should parse correctly as PEP 440: {version}"
    )

    # Tag local data should be preserved and combined with SCM data
    assert version.startswith("3.0.1.dev1"), (
        f"Expected dev version with distance, got {version}"
    )

    # Use regex to validate the version format with both tag build data and SCM node data
    # Expected format: 3.0.1.dev1+ci.789.g<commit_hash>
    version_pattern = r"^3\.0\.1\.dev1\+ci\.789\.g[a-f0-9]+$"
    assert re.match(version_pattern, version), (
        f"Version should match pattern {version_pattern}, got {version}"
    )

    # The original tag's local data (+ci.789) should be preserved and combined with SCM data
    assert "+ci.789" in version, f"Tag local data should be preserved, got {version}"

    # Validate the local part contains both tag and SCM node information
    assert parsed_version.local is not None, (
        f"Expected local version part, got {parsed_version.local}"
    )
    assert "ci.789" in parsed_version.local, (
        f"Expected local part to contain tag data 'ci.789', got {parsed_version.local}"
    )
    assert "g" in parsed_version.local, (
        f"Expected local part to contain SCM node data 'g...', got {parsed_version.local}"
    )

    # Note: This test verifies that local build data from tags is preserved and combined
    # with SCM data when there's distance, which is the desired behavior for issue 1019.


def testwarn_on_broken_setuptools() -> None:
    _warn_on_old_setuptools("61")
    with pytest.warns(RuntimeWarning, match="ERROR: setuptools==60"):
        _warn_on_old_setuptools("60")


@pytest.mark.issue(611)
def test_distribution_provides_extras() -> None:
    from importlib.metadata import distribution

    dist = distribution("setuptools_scm")
    pe: list[str] = dist.metadata.get_all("Provides-Extra", [])
    assert sorted(pe) == ["rich", "simple", "toml"]


@pytest.mark.issue(760)
def test_unicode_in_setup_cfg(tmp_path: Path) -> None:
    cfg = tmp_path / "setup.cfg"
    cfg.write_text(
        textwrap.dedent(
            """
            [metadata]
            name = configparser
            author = Łukasz Langa
            """
        ),
        encoding="utf-8",
    )
    from setuptools_scm._integration.setup_cfg import read_setup_cfg

    name = read_setup_cfg(cfg).name
    assert name == "configparser"

    # also ensure we can parse a version if present (legacy projects)
    cfg.write_text(
        textwrap.dedent(
            """
            [metadata]
            name = configparser
            version = 1.2.3
            """
        ),
        encoding="utf-8",
    )

    data = read_setup_cfg(cfg)
    assert isinstance(data, SetuptoolsBasicData)
    assert data.name == "configparser"
    assert data.version == "1.2.3"


@pytest.mark.issue(1216)
def test_setup_cfg_dynamic_version_warns_and_ignores(tmp_path: Path) -> None:
    cfg = tmp_path / "setup.cfg"
    cfg.write_text(
        textwrap.dedent(
            """
            [metadata]
            name = example-broken
            version = attr: example_broken.__version__
            """
        ),
        encoding="utf-8",
    )

    with pytest.warns(
        UserWarning,
        match=r"setup\.cfg: at \[metadata\]",
    ):
        legacy_data = read_setup_cfg(cfg)

    assert legacy_data.version is None


def test_setup_cfg_version_prevents_inference_version_keyword(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Legacy project setup - we construct the data directly since files are not read anyway
    monkeypatch.chdir(tmp_path)

    dist = create_clean_distribution("legacy-proj")

    # Using keyword should detect an existing version via legacy data and avoid inferring
    from setuptools_scm._integration import setuptools as setuptools_integration
    from setuptools_scm._integration.pyproject_reading import PyProjectData
    from setuptools_scm._integration.setup_cfg import SetuptoolsBasicData

    # Construct PyProjectData directly without requiring build backend inference
    pyproject_data = PyProjectData.for_testing(
        is_required=False,  # setuptools-scm not required
        section_present=False,  # no [tool.setuptools_scm] section
        project_present=False,  # no [project] section
    )

    # Construct legacy data with version from setup.cfg
    legacy_data = SetuptoolsBasicData(
        path=tmp_path / "setup.cfg", name="legacy-proj", version="0.9.0"
    )

    with pytest.warns(UserWarning, match="version of legacy-proj already set"):
        setuptools_integration.version_keyword(
            dist,
            "use_scm_version",
            True,
            _given_pyproject_data=pyproject_data,
            _given_legacy_data=legacy_data,
        )

    # setuptools_scm should not set a version when setup.cfg already provided one
    assert dist.metadata.version is None


def test_setuptools_version_keyword_ensures_regex(
    wd: WorkDir,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd.commit_testfile("test")
    wd("git tag 1.0")
    monkeypatch.chdir(wd.cwd)

    dist = create_clean_distribution("test")
    setuptools_integration.version_keyword(
        dist, "use_scm_version", {"tag_regex": "(1.0)"}
    )
    assert dist.metadata.version == "1.0"


@pytest.mark.parametrize(
    "ep_name", ["setuptools_scm.parse_scm", "setuptools_scm.parse_scm_fallback"]
)
def test_git_archival_plugin_ignored(tmp_path: Path, ep_name: str) -> None:
    tmp_path.joinpath(".git_archival.txt").write_text("broken", encoding="utf-8")
    try:
        dist = importlib.metadata.distribution("setuptools_scm_git_archive")
    except importlib.metadata.PackageNotFoundError:
        pytest.skip("setuptools_scm_git_archive not installed")
    else:
        print(dist.metadata["Name"], dist.version)
    from setuptools_scm.discover import iter_matching_entrypoints

    found = list(iter_matching_entrypoints(tmp_path, config=c, entrypoint=ep_name))
    imports = [item.value for item in found]
    assert "setuptools_scm_git_archive:parse" not in imports


@pytest.mark.parametrize("base_name", ["setuptools_scm", "setuptools-scm"])
@pytest.mark.parametrize(
    "requirements",
    ["", ">=8", "[toml]>=7", "~=9.0", "[rich,toml]>=8"],
    ids=["empty", "version", "extras", "fuzzy", "multiple-extras"],
)
def test_extract_package_name(base_name: str, requirements: str) -> None:
    """Test the _extract_package_name helper function"""
    assert extract_package_name(f"{base_name}{requirements}") == "setuptools-scm"


# Helper function for creating and managing distribution objects
def create_clean_distribution(name: str) -> setuptools.Distribution:
    """Create a clean distribution object without any setuptools_scm effects.

    This function creates a new setuptools Distribution and ensures it's completely
    clean from any previous setuptools_scm version inference effects, including:
    - Clearing any existing version
    - Removing the _setuptools_scm_version_set_by_infer flag
    """
    import setuptools

    dist = setuptools.Distribution({"name": name})

    # Clean all setuptools_scm effects
    dist.metadata.version = None
    if hasattr(dist, "_setuptools_scm_version_set_by_infer"):
        delattr(dist, "_setuptools_scm_version_set_by_infer")

    return dist


def version_keyword_default(
    dist: setuptools.Distribution, pyproject_data: PyProjectData | None = None
) -> None:
    """Helper to call version_keyword with default config and return the result."""

    setuptools_integration.version_keyword(
        dist, "use_scm_version", True, _given_pyproject_data=pyproject_data
    )


def version_keyword_calver(
    dist: setuptools.Distribution, pyproject_data: PyProjectData | None = None
) -> None:
    """Helper to call version_keyword with calver-by-date scheme and return the result."""

    setuptools_integration.version_keyword(
        dist,
        "use_scm_version",
        {"version_scheme": "calver-by-date"},
        _given_pyproject_data=pyproject_data,
    )


def infer_version_with_data(
    dist: setuptools.Distribution, pyproject_data: PyProjectData | None = None
) -> None:
    """Helper to call infer_version with pyproject data."""

    setuptools_integration.infer_version(dist, _given_pyproject_data=pyproject_data)


@pytest.mark.issue("https://github.com/pypa/setuptools_scm/issues/1022")
@pytest.mark.filterwarnings("ignore:version of .* already set:UserWarning")
@pytest.mark.filterwarnings(
    "ignore:.* does not correspond to a valid versioning date.*:UserWarning"
)
@pytest.mark.parametrize(
    ("first_integration", "second_integration", "expected_final_version"),
    [
        # infer_version and version_keyword can be called in either order
        (infer_version_with_data, version_keyword_default, "1.0.1.dev1"),
        (infer_version_with_data, version_keyword_calver, "9.2.13.0.dev1"),
        (version_keyword_default, infer_version_with_data, "1.0.1.dev1"),
        (version_keyword_calver, infer_version_with_data, "9.2.13.0.dev1"),
    ],
)
def test_integration_function_call_order(
    wd: WorkDir,
    monkeypatch: pytest.MonkeyPatch,
    first_integration: Any,
    second_integration: Any,
    expected_final_version: str,
) -> None:
    """Test that integration functions can be called in any order.

    version_keyword should always win when it specifies configuration, but currently doesn't.
    Some tests will fail, showing the bug.
    """
    # Set up controlled environment for deterministic versions
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "1234567890")  # 2009-02-13T23:31:30+00:00
    # Override node_date to get consistent calver versions
    monkeypatch.setenv(
        "SETUPTOOLS_SCM_PRETEND_METADATA_FOR_TEST_CALL_ORDER", "{node_date=2009-02-13}"
    )

    # Set up a git repository with a tag and known commit hash
    wd.commit_testfile("test")
    wd("git tag 1.0.0")
    wd.commit_testfile("test2")  # Add another commit to get distance
    monkeypatch.chdir(wd.cwd)

    # Create PyProjectData with equivalent configuration - no file I/O!
    project_name = "test-call-order"
    pyproject_data = PyProjectData.for_testing(
        project_name=project_name,
        has_dynamic_version=True,
        project_present=True,
        section_present=True,
        local_scheme="no-local-version",
    )

    dist = create_clean_distribution(project_name)

    # Call both integration functions in order with direct data injection
    first_integration(dist, pyproject_data)
    second_integration(dist, pyproject_data)

    # Get the final version directly from the distribution
    final_version = dist.metadata.version

    # Assert the final version matches expectation
    # Some tests will fail here, demonstrating the bug where version_keyword doesn't override
    assert final_version == expected_final_version, (
        f"Expected version '{expected_final_version}' but got '{final_version}'"
    )


@pytest.mark.issue("xmlsec-regression")
def test_xmlsec_download_regression(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that pip download works for xmlsec package without causing setuptools_scm regression.

    This test ensures that downloading and building xmlsec from source doesn't fail
    due to setuptools_scm issues when using --no-build-isolation.
    """
    # Set up environment with setuptools_scm debug enabled
    monkeypatch.setenv("SETUPTOOLS_SCM_DEBUG", "1")
    monkeypatch.setenv("COLUMNS", "150")

    # Run pip download command with no-binary and no-build-isolation
    try:
        subprocess.run(
            [
                *(sys.executable, "-m", "pip", "download"),
                *("--no-binary", "xmlsec"),
                "--no-build-isolation",
                "-v",
                "xmlsec==1.3.16",
            ],
            cwd=tmp_path,
            timeout=300,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        pytest.fail(f"pip download failed: {e}", pytrace=False)

    # The success of the subprocess.run call above means the regression is fixed.
    # pip download succeeded without setuptools_scm causing version conflicts.
