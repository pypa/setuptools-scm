"""Tests for setuptools-scm specific dump_version functionality.

Core version scheme tests have been moved to vcs-versioning/testing_vcs/test_version_schemes.py
"""

from __future__ import annotations

import shutil
import subprocess

from datetime import datetime
from datetime import timezone
from pathlib import Path

import pytest

from vcs_versioning._overrides import PRETEND_KEY

from setuptools_scm import Configuration
from setuptools_scm import dump_version
from setuptools_scm import get_version
from setuptools_scm.version import meta

c = Configuration()

# Use explicit time to avoid triggering auto-creation of GlobalOverrides at import time
VERSIONS = {
    "exact": meta(
        "1.1",
        distance=0,
        dirty=False,
        config=c,
        time=datetime(2009, 2, 13, 23, 31, 30, tzinfo=timezone.utc),
    ),
}


def test_dump_version_doesnt_bail_on_value_error(tmp_path: Path) -> None:
    write_to = "VERSION"
    version = str(VERSIONS["exact"].tag)
    scm_version = meta(VERSIONS["exact"].tag, config=c)
    with pytest.raises(ValueError, match=r"^bad file format:"):
        dump_version(tmp_path, version, write_to, scm_version=scm_version)


@pytest.mark.parametrize(
    "version", ["1.0", "1.2.3.dev1+ge871260", "1.2.3.dev15+ge871260.d20180625"]
)
def test_dump_version_works_with_pretend(
    version: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(PRETEND_KEY, version)
    name = "VERSION.txt"
    target = tmp_path.joinpath(name)
    get_version(root=tmp_path, write_to=name)
    assert target.read_text(encoding="utf-8") == version


def test_dump_version_modern(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    version = "1.2.3"
    monkeypatch.setenv(PRETEND_KEY, version)
    name = "VERSION.txt"

    project = tmp_path.joinpath("project")
    target = project.joinpath(name)
    project.mkdir()

    get_version(root="..", relative_to=target, version_file=name)
    assert target.read_text(encoding="utf-8") == version


def dump_a_version(tmp_path: Path) -> None:
    from vcs_versioning._dump_version import write_version_to_path

    version = "1.2.3"
    scm_version = meta(version, config=c)
    write_version_to_path(
        tmp_path / "VERSION.py", template=None, version=version, scm_version=scm_version
    )


def test_dump_version_on_old_python(tmp_path: Path) -> None:
    python37 = shutil.which("python3.7")
    if python37 is None:
        pytest.skip("python3.7 not found")
    dump_a_version(tmp_path)
    subprocess.run(
        [python37, "-c", "import VERSION;print(VERSION.version)"],
        cwd=tmp_path,
        check=True,
    )


def test_dump_version_mypy(tmp_path: Path) -> None:
    uvx = shutil.which("uvx")
    if uvx is None:
        pytest.skip("uvx not found")
    dump_a_version(tmp_path)
    # Use mypy 1.11.2 - last version supporting Python 3.8
    subprocess.run(
        [uvx, "mypy==1.11.2", "--python-version=3.8", "--strict", "VERSION.py"],
        cwd=tmp_path,
        check=True,
    )


def test_dump_version_flake8(tmp_path: Path) -> None:
    flake8 = shutil.which("flake8")
    if flake8 is None:
        pytest.skip("flake8 not found")
    dump_a_version(tmp_path)
    subprocess.run([flake8, "VERSION.py"], cwd=tmp_path, check=True)


def test_dump_version_ruff(tmp_path: Path) -> None:
    ruff = shutil.which("ruff")
    if ruff is None:
        pytest.skip("ruff not found")
    dump_a_version(tmp_path)
    subprocess.run([ruff, "check", "--no-fix", "VERSION.py"], cwd=tmp_path, check=True)


def test_write_version_to_path_deprecation_warning_none(tmp_path: Path) -> None:
    """Test that write_version_to_path warns when scm_version=None is passed."""
    from vcs_versioning._dump_version import write_version_to_path

    target_file = tmp_path / "version.py"

    # This should raise a deprecation warning when scm_version=None is explicitly passed
    with pytest.warns(
        DeprecationWarning, match="write_version_to_path called without scm_version"
    ):
        write_version_to_path(
            target=target_file,
            template=None,  # Use default template
            version="1.2.3",
            scm_version=None,  # Explicitly passing None should warn
        )

    # Verify the file was created and contains the expected content
    assert target_file.exists()
    content = target_file.read_text(encoding="utf-8")

    # Check that the version is correctly formatted
    assert "__version__ = version = '1.2.3'" in content
    assert "__version_tuple__ = version_tuple = (1, 2, 3)" in content

    # Check that commit_id is set to None when scm_version is None
    assert "__commit_id__ = commit_id = None" in content


def test_write_version_to_path_deprecation_warning_missing(tmp_path: Path) -> None:
    """Test that write_version_to_path warns when scm_version parameter is not provided."""
    from vcs_versioning._dump_version import write_version_to_path

    target_file = tmp_path / "version.py"

    # This should raise a deprecation warning when scm_version is not provided
    with pytest.warns(
        DeprecationWarning, match="write_version_to_path called without scm_version"
    ):
        write_version_to_path(
            target=target_file,
            template=None,  # Use default template
            version="1.2.3",
            # scm_version not provided - should warn
        )

    # Verify the file was created and contains the expected content
    assert target_file.exists()
    content = target_file.read_text(encoding="utf-8")

    # Check that the version is correctly formatted
    assert "__version__ = version = '1.2.3'" in content
    assert "__version_tuple__ = version_tuple = (1, 2, 3)" in content

    # Check that commit_id is set to None when scm_version is None
    assert "__commit_id__ = commit_id = None" in content
