import itertools
import os

import pytest

# 2009-02-13T23:31:30+00:00
os.environ["SOURCE_DATE_EPOCH"] = "1234567890"
os.environ["SETUPTOOLS_SCM_DEBUG"] = "1"
VERSION_PKGS = ["setuptools", "setuptools_scm"]


def pytest_report_header():
    import pkg_resources

    res = []
    for pkg in VERSION_PKGS:
        version = pkg_resources.get_distribution(pkg).version
        path = __import__(pkg).__file__
        res.append(f"{pkg} version {version} from {path!r}")
    return res


def pytest_addoption(parser):
    group = parser.getgroup("setuptools_scm")
    group.addoption(
        "--test-legacy", dest="scm_test_virtualenv", default=False, action="store_true"
    )


class Wd:
    commit_command = None
    add_command = None

    def __repr__(self):
        return f"<WD {self.cwd}>"

    def __init__(self, cwd):
        self.cwd = cwd
        self.__counter = itertools.count()

    def __call__(self, cmd, **kw):
        if kw:
            cmd = cmd.format(**kw)
        from setuptools_scm.utils import do

        return do(cmd, self.cwd)

    def write(self, name, value, **kw):
        filename = self.cwd / name
        if kw:
            value = value.format(**kw)
        if isinstance(value, bytes):
            filename.write_bytes(value)
        else:
            filename.write_text(value)
        return filename

    def _reason(self, given_reason):
        if given_reason is None:
            return f"number-{next(self.__counter)}"
        else:
            return given_reason

    def add_and_commit(self, reason=None):
        self(self.add_command)
        self.commit(reason)

    def commit(self, reason=None):
        reason = self._reason(reason)
        self(self.commit_command, reason=reason)

    def commit_testfile(self, reason=None):
        reason = self._reason(reason)
        self.write("test.txt", "test {reason}", reason=reason)
        self(self.add_command)
        self.commit(reason=reason)

    def get_version(self, **kw):
        __tracebackhide__ = True
        from setuptools_scm import get_version

        version = get_version(root=str(self.cwd), fallback_root=str(self.cwd), **kw)
        print(version)
        return version

    @property
    def version(self):
        __tracebackhide__ = True
        return self.get_version()


@pytest.fixture(autouse=True)
def debug_mode():
    from setuptools_scm import utils

    utils.DEBUG = True
    yield
    utils.DEBUG = False


@pytest.fixture
def wd(tmp_path):
    target_wd = tmp_path.resolve() / "wd"
    target_wd.mkdir()
    return Wd(target_wd)


@pytest.fixture
def repositories_hg_git(tmp_path):
    from setuptools_scm.utils import do

    tmp_path = tmp_path.resolve()
    path_git = tmp_path / "repo_git"
    path_git.mkdir()

    wd = Wd(path_git)
    wd("git init")
    wd("git config user.email test@example.com")
    wd('git config user.name "a test"')
    wd.add_command = "git add ."
    wd.commit_command = "git commit -m test-{reason}"

    path_hg = tmp_path / "repo_hg"
    do(f"hg clone {path_git} {path_hg} --config extensions.hggit=")
    assert path_hg.exists()

    with open(path_hg / ".hg/hgrc", "a") as file:
        file.write("[extensions]\nhggit =\n")

    wd_hg = Wd(path_hg)
    wd_hg.add_command = "hg add ."
    wd_hg.commit_command = 'hg commit -m test-{reason} -u test -d "0 0"'

    return wd_hg, wd
