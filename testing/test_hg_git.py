import pytest

from setuptools_scm.utils import do_ex
from setuptools_scm.utils import has_command

python_hg, err, ret = do_ex("hg debuginstall --template {pythonexe}")

if ret:
    skip_no_hggit = True
else:
    out, err, ret = do_ex([python_hg.strip(), "-c", "import hggit"])
    print(out, err, ret)
    skip_no_hggit = bool(ret)


@pytest.mark.skipif(not has_command("hg", warn=False), reason="hg executable not found")
@pytest.mark.skipif(skip_no_hggit, reason="hg-git not installed")
def test_base(repositories_hg_git):
    wd, wd_git = repositories_hg_git

    assert wd_git.version == "0.1.dev0"
    assert wd.version == "0.1.dev0"

    wd_git.commit_testfile()
    wd("hg pull -u")

    version_git = wd_git.version
    version = wd.version

    assert version_git.startswith("0.1.dev1+g")
    assert version.startswith("0.1.dev1+g")

    assert not version_git.endswith("1-")
    assert not version.endswith("1-")

    wd_git("git tag v0.1")
    wd("hg pull -u")
    assert wd_git.version == "0.1"
    assert wd.version == "0.1"

    wd_git.write("test.txt", "test2")
    wd.write("test.txt", "test2")
    assert wd_git.version.startswith("0.2.dev0+g")
    assert wd.version.startswith("0.2.dev0+g")

    wd_git.commit_testfile()
    wd("hg pull")
    wd("hg up -C")
    assert wd_git.version.startswith("0.2.dev1+g")
    assert wd.version.startswith("0.2.dev1+g")

    wd_git("git tag version-0.2")
    wd("hg pull -u")
    assert wd_git.version.startswith("0.2")
    assert wd.version.startswith("0.2")

    wd_git.commit_testfile()
    wd_git("git tag version-0.2.post210+gbe48adfpost3+g0cc25f2")
    wd("hg pull -u")
    with pytest.warns(
        UserWarning, match="tag '.*' will be stripped of its suffix '.*'"
    ):
        assert wd_git.version.startswith("0.2")

    with pytest.warns(
        UserWarning, match="tag '.*' will be stripped of its suffix '.*'"
    ):
        assert wd.version.startswith("0.2")

    wd_git.commit_testfile()
    wd_git("git tag 17.33.0-rc")
    wd("hg pull -u")
    assert wd_git.version == "17.33.0rc0"
    assert wd.version == "17.33.0rc0"
