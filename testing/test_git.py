import sys

from setuptools_scm import integration
from setuptools_scm.utils import do
from setuptools_scm import git
import pytest
from datetime import date
from os.path import join as opj
from setuptools_scm.file_finder_git import git_find_files


@pytest.fixture
def wd(wd):
    wd("git init")
    wd("git config user.email test@example.com")
    wd('git config user.name "a test"')
    wd.add_command = "git add ."
    wd.commit_command = "git commit -m test-{reason}"
    return wd


@pytest.mark.parametrize(
    "given, tag, number, node, dirty",
    [
        ("3.3.1-rc26-0-g9df187b", "3.3.1-rc26", 0, "g9df187b", False),
        ("17.33.0-rc-17-g38c3047c0", "17.33.0-rc", 17, "g38c3047c0", False),
    ],
)
def test_parse_describe_output(given, tag, number, node, dirty):
    parsed = git._git_parse_describe(given)
    assert parsed == (tag, number, node, dirty)


def test_root_relative_to(tmpdir, wd, monkeypatch):
    monkeypatch.delenv("SETUPTOOLS_SCM_DEBUG")
    p = wd.cwd.ensure("sub/package", dir=1)
    p.join("setup.py").write(
        """from setuptools import setup
setup(use_scm_version={"root": "../..",
                       "relative_to": __file__})
"""
    )
    res = do((sys.executable, "setup.py", "--version"), p)
    assert res == "0.1.dev0"


@pytest.mark.issue("https://github.com/pypa/setuptools_scm/issues/298")
def test_file_finder_no_history(wd, caplog):
    file_list = git_find_files(str(wd.cwd))
    assert file_list == []

    assert "listing git files failed - pretending there aren't any" in caplog.text


@pytest.mark.issue("https://github.com/pypa/setuptools_scm/issues/281")
def test_parse_call_order(wd):
    git.parse(str(wd.cwd), git.DEFAULT_DESCRIBE)


def test_version_from_git(wd):
    assert wd.version == "0.1.dev0"

    wd.commit_testfile()
    assert wd.version.startswith("0.1.dev1+g")
    assert not wd.version.endswith("1-")

    wd("git tag v0.1")
    assert wd.version == "0.1"

    wd.write("test.txt", "test2")
    assert wd.version.startswith("0.2.dev0+g")

    wd.commit_testfile()
    assert wd.version.startswith("0.2.dev1+g")

    wd("git tag version-0.2")
    assert wd.version.startswith("0.2")

    wd.commit_testfile()
    wd("git tag version-0.2.post210+gbe48adfpost3+g0cc25f2")
    with pytest.warns(
        UserWarning, match="tag '.*' will be stripped of its suffix '.*'"
    ):
        assert wd.version.startswith("0.2")

    wd.commit_testfile()
    wd("git tag 17.33.0-rc")
    assert wd.version == "17.33.0rc0"


@pytest.mark.issue(179)
def test_unicode_version_scheme(wd):
    scheme = b"guess-next-dev".decode("ascii")
    assert wd.get_version(version_scheme=scheme)


@pytest.mark.issue(108)
@pytest.mark.issue(109)
def test_git_worktree(wd):
    wd.write("test.txt", "test2")
    # untracked files dont change the state
    assert wd.version == "0.1.dev0"
    wd("git add test.txt")
    assert wd.version.startswith("0.1.dev0+d")


@pytest.mark.issue(86)
def test_git_dirty_notag(wd):
    wd.commit_testfile()
    wd.write("test.txt", "test2")
    wd("git add test.txt")
    assert wd.version.startswith("0.1.dev1")
    today = date.today()
    # we are dirty, check for the tag
    assert today.strftime(".d%Y%m%d") in wd.version


@pytest.fixture
def shallow_wd(wd, tmpdir):
    wd.commit_testfile()
    wd.commit_testfile()
    wd.commit_testfile()
    target = tmpdir.join("wd_shallow")
    do(["git", "clone", "file://%s" % wd.cwd, str(target), "--depth=1"])
    return target


def test_git_parse_shallow_warns(shallow_wd, recwarn):
    git.parse(str(shallow_wd))
    msg = recwarn.pop()
    assert "is shallow and may cause errors" in str(msg.message)


def test_git_parse_shallow_fail(shallow_wd):
    with pytest.raises(ValueError) as einfo:
        git.parse(str(shallow_wd), pre_parse=git.fail_on_shallow)

    assert "git fetch" in str(einfo.value)


def test_git_shallow_autocorrect(shallow_wd, recwarn):
    git.parse(str(shallow_wd), pre_parse=git.fetch_on_shallow)
    msg = recwarn.pop()
    assert "git fetch was used to rectify" in str(msg.message)
    git.parse(str(shallow_wd), pre_parse=git.fail_on_shallow)


def test_find_files_stop_at_root_git(wd):
    wd.commit_testfile()
    wd.cwd.ensure("project/setup.cfg")
    assert integration.find_files(str(wd.cwd / "project")) == []


@pytest.mark.issue(128)
def test_parse_no_worktree(tmpdir):
    ret = git.parse(str(tmpdir))
    assert ret is None


def test_alphanumeric_tags_match(wd):
    wd.commit_testfile()
    wd("git tag newstyle-development-started")
    assert wd.version.startswith("0.1.dev1+g")


def test_git_archive_export_ignore(wd):
    wd.write("test1.txt", "test")
    wd.write("test2.txt", "test")
    wd.write(
        ".git/info/attributes",
        # Explicitly include test1.txt so that the test is not affected by
        # a potentially global gitattributes file on the test machine.
        "/test1.txt -export-ignore\n/test2.txt export-ignore",
    )
    wd("git add test1.txt test2.txt")
    wd.commit()
    with wd.cwd.as_cwd():
        assert integration.find_files(".") == [opj(".", "test1.txt")]


@pytest.mark.issue(228)
def test_git_archive_subdirectory(wd):
    wd("mkdir foobar")
    wd.write("foobar/test1.txt", "test")
    wd("git add foobar")
    wd.commit()
    with wd.cwd.as_cwd():
        assert integration.find_files(".") == [opj(".", "foobar", "test1.txt")]


@pytest.mark.issue(251)
def test_git_archive_run_from_subdirectory(wd):
    wd("mkdir foobar")
    wd.write("foobar/test1.txt", "test")
    wd("git add foobar")
    wd.commit()
    with (wd.cwd / "foobar").as_cwd():
        assert integration.find_files(".") == [opj(".", "test1.txt")]


def test_git_feature_branch_increments_major(wd):
    wd.commit_testfile()
    wd("git tag 1.0.0")
    wd.commit_testfile()
    assert wd.get_version(version_scheme="python-simplified-semver").startswith("1.0.1")
    wd("git checkout -b feature/fun")
    wd.commit_testfile()
    assert wd.get_version(version_scheme="python-simplified-semver").startswith("1.1.0")


@pytest.mark.issue("https://github.com/pypa/setuptools_scm/issues/303")
def test_not_matching_tags(wd):
    wd.commit_testfile()
    wd("git tag apache-arrow-0.11.1")
    wd.commit_testfile()
    wd("git tag apache-arrow-js-0.9.9")
    wd.commit_testfile()
    assert wd.get_version(
        tag_regex=r"^apache-arrow-([\.0-9]+)$",
        git_describe_command="git describe --dirty --tags --long --exclude *js* ",
    ).startswith(
        "0.11.2"
    )
