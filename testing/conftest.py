import os
import itertools
import pytest
import six

os.environ["SETUPTOOLS_SCM_DEBUG"] = "1"
VERSION_PKGS = ["setuptools", "setuptools_scm"]


def pytest_report_header():
    import pkg_resources

    res = []
    for pkg in VERSION_PKGS:
        version = pkg_resources.get_distribution(pkg).version
        path = __import__(pkg).__file__
        res.append("{} version {} from {!r}".format(pkg, version, path))
    return res


class Wd(object):
    commit_command = None
    add_command = None

    def __repr__(self):
        return "<WD {cwd}>".format(cwd=self.cwd)

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
        if isinstance(value, six.text_type):
            filename.write_text(value)
        else:
            filename.write_bytes(value)
        return filename

    def _reason(self, given_reason):
        if given_reason is None:
            return "number-{c}".format(c=next(self.__counter))
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


@pytest.yield_fixture(autouse=True)
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
