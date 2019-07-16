
import pytest
import attr
from setuptools_scm.utils import do
import zipfile
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

pytestmark = pytest.mark.skipif(
    "sys.version_info[0] < 3", reason="the pip integration tests require python3"
)

FILE = "example_package.py", "import sys;print sys.version\n"
SETUP_PY_CLASSICAL = "setup.py", """\
from setuptools import setup

setup(
    name="example",
    setup_requires=["setuptools_scm"],
    use_scm_version=True)
"""

SETUP_CFG = "setup.cfg", """\
[metadata]
name  = example
[options]
setup_requires=setuptools_scm
"""


SETUP_PY_MINIMAL = "setup.py", """\
from setuptools import setup
setup(use_scm_version=True)
"""

PYPROJECT_SETUPTOOLS = "pyproject.toml", """\
[build-system]
requires = ["setuptools>=30.3.0", "wheel", "setuptools_scm"]

"""
PYPROJECT_SETUPTOOLS_SCM = "pyproject.toml", """\
[build-system]
requires = ["setuptools>=30.3.0", "wheel", "setuptools_scm"]

"""

PYPROJECT_FLIT = "pyproject.toml", ""


@attr.s
class PipVenv:
    path = attr.ib()

    @classmethod
    def create(cls, path):

        venv = pytest.importorskip("venv")
        builder = venv.EnvBuilder(with_pip=True)
        builder.create(str(path))

        self = cls(path)
        self.do("bin/pip install wheel -e {setuptools_scm}".format(setuptools_scm=ROOT))
        return self

    def do(self, cmd):
        return do(cmd, str(self.path))


@pytest.fixture
def pip_venv(tmp_path):
    return PipVenv.create(tmp_path / "pip_venv")


@pytest.fixture
def wd(wd):
    wd("git init")
    wd("git config user.email test@example.com")
    wd('git config user.name "a test"')
    wd.add_command = "git add ."
    wd.commit_command = "git commit -m test-{reason}"
    return wd


def with_filespecs(**kw):
    params = []
    for id, wanted_files in kw.items():
        actual_files = [x for x in wanted_files if isinstance(x, tuple)]
        marks = [x for x in wanted_files if not isinstance(x, tuple)]
        params.append(pytest.param(actual_files, id=id, marks=marks))

    return pytest.mark.parametrize("wanted_files", params)


def setup_package(wanted_files, wd):
    for name, content in wanted_files:
        wd.write(name, content)
    wd.add_and_commit("basic-file-setup-done")
    wd("git tag v0.1")


spec = with_filespecs(
    classical=[FILE, SETUP_PY_CLASSICAL],
    static_config=[FILE, SETUP_PY_MINIMAL, SETUP_CFG],
    basic_pep717=[FILE, SETUP_PY_MINIMAL, SETUP_CFG, PYPROJECT_SETUPTOOLS],
    integrated_pep517=[
        FILE,
        SETUP_CFG,
        PYPROJECT_SETUPTOOLS_SCM,
        pytest.mark.xfail(reason="integration not yet implemented"),
    ],
)


@spec
def test_package_installs(wanted_files, wd, pip_venv):  # NOQA
    setup_package(wanted_files, wd)
    pip_venv.do("./bin/pip install --no-build-isolation {wd.cwd}".format(wd=wd))
    metadata = pip_venv.do("./bin/pip show example")
    assert "Version: 0.1\n" in metadata


@spec
def test_package_builds_wheel(wanted_files, wd, pip_venv, tmp_path):  # NOQA
    setup_package(wanted_files, wd)

    wheel_dir = tmp_path.joinpath("wheels")
    wheel_dir.mkdir()
    pip_venv.do(
        "pip wheel {wd.cwd} --no-build-isolation --wheel-dir {wheel_dir}".format(
            wd=wd, wheel_dir=wheel_dir
        )
    )
    wheel = next(wheel_dir.glob("*.whl"))
    print(wheel)
    with zipfile.ZipFile(wheel, "r") as zfp:
        metadata = zfp.read("example-0.1.dist-info/METADATA")
        assert b"Version: 0.1\n" in metadata
