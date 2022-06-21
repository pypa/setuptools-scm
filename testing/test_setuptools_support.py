"""
integration tests that check setuptools version support
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys
from typing import Any
from typing import Callable

import _pytest.config
import pytest


def cli_run(*k: Any, **kw: Any) -> None:
    """this defers the virtualenv import
    it helps to avoid warnings from the furthermore imported setuptools
    """
    global cli_run
    from virtualenv.run import cli_run  # type: ignore

    cli_run(*k, **kw)


pytestmark = pytest.mark.filterwarnings(
    r"ignore:.*tool\.setuptools_scm.*", r"always:.*setup.py install is deprecated.*"
)


ROOT = pathlib.Path(__file__).parent.parent


class Venv:
    location: pathlib.Path

    def __init__(self, location: pathlib.Path):
        self.location = location

    @property
    def python(self) -> pathlib.Path:
        return self.location / "bin/python"


class VenvMaker:
    def __init__(self, base: pathlib.Path):
        self.base = base

    def __repr__(self) -> str:
        return f"<VenvMaker base={self.base}>"

    def get_venv(
        self, python: str, pip: str, setuptools: str, prefix: str = "scm"
    ) -> Venv:
        name = f"{prefix}-py={python}-pip={pip}-setuptools={setuptools}"
        path = self.base / name
        if not path.is_dir():
            cli_run(
                [
                    str(path),
                    "--python",
                    python,
                    "--pip",
                    pip,
                    "--setuptools",
                    setuptools,
                ],
                setup_logging=False,
            )
        venv = Venv(path)
        subprocess.run([venv.python, "-m", "pip", "install", "-e", str(ROOT)])
        # fixup pip
        subprocess.check_call([venv.python, "-m", "pip", "install", f"pip=={pip}"])
        subprocess.check_call(
            [venv.python, "-m", "pip", "install", f"setuptools~={setuptools}"]
        )
        return venv


@pytest.fixture
def venv_maker(pytestconfig: _pytest.config.Config) -> VenvMaker:
    if not pytestconfig.getoption("--test-legacy"):
        pytest.skip(
            "testing on legacy setuptools disabled, pass --test-legacy to run them"
        )
    assert pytestconfig.cache is not None
    path = pytestconfig.cache.mkdir("setuptools_scm_venvs")
    return VenvMaker(path)


SCRIPT = """
from __future__ import print_function
import sys
import setuptools
print(setuptools.__version__, 'expected', sys.argv[1])
import setuptools_scm.version
from setuptools_scm.__main__ import main
main()
"""


def check(venv: Venv, expected_version: str, **env: str) -> None:

    subprocess.check_call(
        [venv.python, "-c", SCRIPT, expected_version],
        env=dict(os.environ, **env),
    )


@pytest.mark.skipif(
    sys.version_info[:2] >= (3, 10), reason="old setuptools won't work on python 3.10"
)
def test_distlib_setuptools_works(venv_maker: VenvMaker) -> None:
    venv = venv_maker.get_venv(setuptools="45.0.0", pip="9.0", python="3.6")
    subprocess.run([venv.python, "-m", "pip", "install", "-e", str(ROOT)])

    check(venv, "45.0.0")


SETUP_PY_NAME = """
from setuptools import setup
setup(name='setuptools_scm_test_package')
"""

SETUP_PY_KEYWORD = """
from setuptools import setup
setup(use_scm_version={"write_to": "pkg_version.py"})
"""

PYPROJECT_TOML_WITH_KEY = """
[build-system]
# Minimum requirements for the build system to execute.
requires = ["setuptools>45"]  # PEP 508 specifications.
[tool.setuptools_scm]
write_to = "pkg_version.py"
"""

SETUP_CFG_NAME = """
[metadata]
name = setuptools_scm_test_package
"""


def prepare_expecting_pyproject_support(pkg: pathlib.Path) -> None:
    pkg.mkdir()
    pkg.joinpath("setup.py").write_text(SETUP_PY_NAME)
    pkg.joinpath("pyproject.toml").write_text(PYPROJECT_TOML_WITH_KEY)
    pkg.joinpath("PKG-INFO").write_text("Version: 1.0.0")


def prepare_setup_py_config(pkg: pathlib.Path) -> None:
    pkg.mkdir()
    pkg.joinpath("setup.py").write_text(SETUP_PY_KEYWORD)
    pkg.joinpath("setup.cfg").write_text(SETUP_CFG_NAME)

    pkg.joinpath("PKG-INFO").write_text("Version: 1.0.0")


@pytest.mark.skipif(
    sys.version_info[:2] >= (3, 10), reason="old setuptools won't work on python 3.10"
)
@pytest.mark.parametrize("setuptools", [f"{v}.0" for v in range(31, 45)])
@pytest.mark.parametrize(
    "project_create",
    [
        pytest.param(
            prepare_expecting_pyproject_support,
            marks=pytest.mark.xfail(reason="pyproject requires setuptools > 42"),
        ),
        prepare_setup_py_config,
    ],
)
def test_on_old_setuptools(
    venv_maker: VenvMaker,
    tmp_path: pathlib.Path,
    setuptools: str,
    project_create: Callable[[pathlib.Path], None],
) -> None:
    pkg = tmp_path.joinpath("pkg")
    project_create(pkg)
    venv = venv_maker.get_venv(setuptools=setuptools, pip="9.0", python="3.6")

    # monkeypatch.delenv("SETUPTOOLS_SCM_DEBUG", raising=False)

    def run_and_output(cmd: list[str | pathlib.Path]) -> bytes:
        res = subprocess.run(cmd, cwd=str(pkg), stdout=subprocess.PIPE)
        if not res.returncode:
            return res.stdout.strip()
        else:
            print(res.stdout)
            pytest.fail(str(cmd), pytrace=False)

    version = run_and_output([venv.python, "setup.py", "--version"])
    name = run_and_output([venv.python, "setup.py", "--name"])
    assert (name, version) == (b"setuptools_scm_test_package", b"1.0.0")

    # monkeypatch.setenv(
    # "SETUPTOOLS_SCM_PRETEND_VERSION_FOR_setuptools_scm_test_package", "2.0,0")

    # version_pretend = run_and_output([venv.python, "setup.py", "--version"])
    # assert version_pretend == b"2.0.0"
