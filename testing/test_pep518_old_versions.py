from __future__ import annotations

import datetime
import os
import pathlib
import subprocess

import build
import pytest

from packaging.utils import parse_wheel_filename
from packaging.version import Version

PROJECT = pathlib.Path(__file__).parent.parent


class UVEnvMaker:
    root: pathlib.Path
    self_wheel: pathlib.Path

    def __init__(self, root: pathlib.Path, self_wheel: pathlib.Path):
        self.root = root
        self.self_wheel = self_wheel

    def make_builder_with(
        self, project: pathlib.Path, python: str, setuptools: str
    ) -> build.ProjectBuilder:
        venv = self.root.joinpath(f"{python}--{setuptools}")
        venv_python = venv.joinpath("bin/python")

        if not venv.exists():
            subprocess.run(["uv", "venv", venv, "--python", python], check=True)
            subprocess.run(
                [
                    "uv",
                    "pip",
                    "install",
                    "--python",
                    venv_python,
                    setuptools,
                    self.self_wheel,
                    "wheel",
                    "pip",
                    "typing-extensions",
                    "tomli",
                ],
                check=True,
            )
        return build.ProjectBuilder(project, python_executable=os.fspath(venv_python))


@pytest.fixture(scope="module")
def self_wheel(tmp_path_factory: pytest.TempPathFactory) -> pathlib.Path:
    wheelhouse = tmp_path_factory.mktemp("wheels", numbered=False)
    project_builder = build.ProjectBuilder(PROJECT)
    with pytest.MonkeyPatch.context() as cx:
        cx.delenv("SETUPTOOLS_SCM_DEBUG")
        dist = project_builder.build(
            distribution="editable", output_directory=wheelhouse
        )
    return pathlib.Path(dist)


@pytest.fixture(scope="module")
def uvmkr(pytestconfig: pytest.Config, self_wheel: pathlib.Path) -> UVEnvMaker:
    assert pytestconfig.cache is not None
    root = pytestconfig.cache.mkdir("uv_envs")
    uv_mkr = UVEnvMaker(root, self_wheel)
    return uv_mkr


MIN_SETUPTOOLS = 40

MISSING = {55}


HAS_NO_BUILD_BACKEND = {
    f"setuptools~={n}.0" for n in range(MIN_SETUPTOOLS, 61) if n not in MISSING
}


PYTHON_VERSIONS = [
    "python3.8",
    "python3.9",
    "python3.10",
    "python3.11",
    "python3.12",
    "python3.13",
]


PYTHON_COMPAT = {
    "setuptools~=40.0": PYTHON_VERSIONS[:1],
    "setuptools~=41.0": PYTHON_VERSIONS.copy(),
    "setuptools~=42.0": PYTHON_VERSIONS.copy(),
    "setuptools~=43.0": PYTHON_VERSIONS.copy(),
    "setuptools~=44.0": PYTHON_VERSIONS.copy(),
    "setuptools~=45.0": PYTHON_VERSIONS.copy(),
    "setuptools~=46.0": PYTHON_VERSIONS.copy(),
    "setuptools~=47.0": PYTHON_VERSIONS.copy(),
    "setuptools~=48.0": PYTHON_VERSIONS.copy(),
    "setuptools~=49.0": PYTHON_VERSIONS.copy(),
    "setuptools~=50.0": PYTHON_VERSIONS.copy(),
    "setuptools~=51.0": PYTHON_VERSIONS.copy(),
    "setuptools~=52.0": PYTHON_VERSIONS.copy(),
    "setuptools~=53.0": PYTHON_VERSIONS.copy(),
    "setuptools~=54.0": PYTHON_VERSIONS.copy(),
    "setuptools~=56.0": PYTHON_VERSIONS.copy(),
    "setuptools~=57.0": PYTHON_VERSIONS.copy(),
    "setuptools~=58.0": PYTHON_VERSIONS.copy(),
    "setuptools~=59.0": PYTHON_VERSIONS.copy(),
    "setuptools~=60.0": PYTHON_VERSIONS.copy(),
    "setuptools~=61.0": PYTHON_VERSIONS.copy(),
    "setuptools~=62.0": PYTHON_VERSIONS.copy(),
    "setuptools~=63.0": PYTHON_VERSIONS.copy(),
    "setuptools~=64.0": PYTHON_VERSIONS.copy(),
    "setuptools~=65.0": PYTHON_VERSIONS.copy(),
    "setuptools~=66.0": PYTHON_VERSIONS.copy(),
    "setuptools~=67.0": PYTHON_VERSIONS.copy(),
    "setuptools~=68.0": PYTHON_VERSIONS.copy(),
    "setuptools~=69.0": PYTHON_VERSIONS.copy(),
    "setuptools~=70.0": PYTHON_VERSIONS.copy(),
    "setuptools~=71.0": PYTHON_VERSIONS.copy(),
    "setuptools~=72.0": PYTHON_VERSIONS.copy(),
    "setuptools~=73.0": PYTHON_VERSIONS.copy(),
    "setuptools~=74.0": PYTHON_VERSIONS.copy(),
    "setuptools~=75.0": PYTHON_VERSIONS.copy(),
    "setuptools~=76.0": PYTHON_VERSIONS[1:],
}


@pytest.mark.parametrize(
    "setuptools_version",
    [f"setuptools~={n}.0" for n in range(MIN_SETUPTOOLS, 77) if n not in MISSING],
)
@pytest.mark.parametrize("python", PYTHON_VERSIONS)
@pytest.mark.parametrize(
    "backend",
    [
        pytest.param(None, id="backend-was-not-set"),
        "setuptools.build_meta",
        "setuptools.build_meta:__legacy__",
    ],
)
@pytest.mark.parametrize(
    "version_scheme", ["calver-by-date", "python-simplified-semver", "guess-next-dev"]
)
def test_setuptools_project_with_versions(
    setuptools_version: str,
    version_scheme: str,
    python: str,
    backend: str | None,
    uvmkr: UVEnvMaker,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if python == "python3.8" and setuptools_version == "setuptools~=76.0":
        pytest.skip("no python38 on setuptools 76")

    if python not in PYTHON_COMPAT[setuptools_version]:
        pytest.skip(f"no {python} on {setuptools_version}")

    if python in ("python3.12", "python3.13") and Version(
        setuptools_version.split("~=")[-1]
    ) <= Version("65.0"):
        pytest.skip("no zipimport")

    project = tmp_path.joinpath("project")
    project.mkdir()

    output = tmp_path.joinpath("dist")
    output.mkdir()

    pyproject = project.joinpath("pyproject.toml")
    if backend is not None:
        pyproject.write_text(f"""
    [build-system]
    requires = ["setuptools", "setuptools_scm"]
    build-backend = {backend!r}
    [package]
    name = "test-version"
    dynamic = "version"
    [tool._setuptools_scm]
    """)
    else:
        pyproject.write_text("""
    [build-system]
    requires = ["setuptools", "setuptools_scm"]
    [package]
    name = "test-version"
    dynamic = "version"
    [tool._setuptools_scm]
    """)
    setup_py = project.joinpath("setup.py")
    setup_py.write_text(f"""if True:
        from setuptools import setup
        setup(use_scm_version={{"version_scheme": {version_scheme!r}}})
    """)

    builder = uvmkr.make_builder_with(project, python, setuptools_version)

    subprocess.run(
        [
            "git",
            "init",
        ],
        cwd=project,
        check=True,
    )

    result = subprocess.run(
        [builder.python_executable, "setup.py", "--version"],
        capture_output=True,
        cwd=project,
        encoding="utf-8",
    )
    if result.returncode:
        print(result.stderr)
        assert not result.returncode
    try:
        version = Version(result.stdout)
    except Exception:
        print(result.stderr)
        raise
    else:
        verify_version(version_scheme, version)

    if setuptools_version not in HAS_NO_BUILD_BACKEND:
        with monkeypatch.context() as xy:
            xy.chdir(project)
            res = builder.build("wheel", output_directory=output)
        version = parse_wheel_filename(pathlib.Path(res).name)[1]
        verify_version(version_scheme, version)


def verify_version(version_scheme: str, version: Version) -> None:
    expect_release: tuple[int, ...]
    if version_scheme == "calver-by-date":
        today = datetime.datetime.now(datetime.UTC).date()  # type: ignore[attr-defined]
        expect_release = (today.year % 1000, today.month, today.day, 0)
    elif version_scheme == "python-simplified-semver":
        expect_release = (0, 0, 1)
    else:
        expect_release = (0, 1)
    assert version.release == expect_release
