import os
from datetime import date
from datetime import timedelta

import pytest

from setuptools_scm.config import Configuration
from setuptools_scm.version import calver_by_date
from setuptools_scm.version import format_version
from setuptools_scm.version import guess_next_version
from setuptools_scm.version import meta
from setuptools_scm.version import no_guess_dev_version
from setuptools_scm.version import release_branch_semver_version
from setuptools_scm.version import simplified_semver_version
from setuptools_scm.version import tags_to_versions


c = Configuration()


@pytest.mark.parametrize(
    "version, expected_next",
    [
        pytest.param(meta("1.0.0", config=c), "1.0.0", id="exact"),
        pytest.param(meta("1.0", config=c), "1.0.0", id="short_tag"),
        pytest.param(
            meta("1.0.0", distance=2, branch="default", config=c),
            "1.0.1.dev2",
            id="normal_branch",
        ),
        pytest.param(
            meta("1.0", distance=2, branch="default", config=c),
            "1.0.1.dev2",
            id="normal_branch_short_tag",
        ),
        pytest.param(
            meta("1.0.0", distance=2, branch="feature", config=c),
            "1.1.0.dev2",
            id="feature_branch",
        ),
        pytest.param(
            meta("1.0", distance=2, branch="feature", config=c),
            "1.1.0.dev2",
            id="feature_branch_short_tag",
        ),
        pytest.param(
            meta("1.0.0", distance=2, branch="features/test", config=c),
            "1.1.0.dev2",
            id="feature_in_branch",
        ),
    ],
)
def test_next_semver(version, expected_next):
    computed = simplified_semver_version(version)
    assert computed == expected_next


def test_next_semver_bad_tag():

    version = meta("1.0.0-foo", preformatted=True, config=c)
    with pytest.raises(
        ValueError, match="1.0.0-foo can't be parsed as numeric version"
    ):
        simplified_semver_version(version)


@pytest.mark.parametrize(
    "version, expected_next",
    [
        pytest.param(meta("1.0.0", config=c), "1.0.0", id="exact"),
        pytest.param(
            meta("1.0.0", distance=2, branch="master", config=c),
            "1.1.0.dev2",
            id="development_branch",
        ),
        pytest.param(
            meta("1.0.0rc1", distance=2, branch="master", config=c),
            "1.1.0.dev2",
            id="development_branch_release_candidate",
        ),
        pytest.param(
            meta("1.0.0", distance=2, branch="maintenance/1.0.x", config=c),
            "1.0.1.dev2",
            id="release_branch_legacy_version",
        ),
        pytest.param(
            meta("1.0.0", distance=2, branch="v1.0.x", config=c),
            "1.0.1.dev2",
            id="release_branch_with_v_prefix",
        ),
        pytest.param(
            meta("1.0.0", distance=2, branch="release-1.0", config=c),
            "1.0.1.dev2",
            id="release_branch_with_prefix",
        ),
        pytest.param(
            meta("1.0.0", distance=2, branch="bugfix/3434", config=c),
            "1.1.0.dev2",
            id="false_positive_release_branch",
        ),
    ],
)
def test_next_release_branch_semver(version, expected_next):
    computed = release_branch_semver_version(version)
    assert computed == expected_next


def m(tag, **kw):
    return meta(tag, **kw, config=c)


@pytest.mark.parametrize(
    "version, expected_next",
    [
        pytest.param(
            m("1.0.0", distance=2),
            "1.0.0.post1.dev2",
            id="dev_distance",
        ),
        pytest.param(
            m("1.0.dev0", distance=2), "1.0.dev2", id="dev_distance_after_dev_tag"
        ),
        pytest.param(
            m("1.0", distance=2),
            "1.0.post1.dev2",
            id="dev_distance_short_tag",
        ),
        pytest.param(
            m("1.0.0"),
            "1.0.0",
            id="no_dev_distance",
        ),
    ],
)
def test_no_guess_version(version, expected_next):
    computed = no_guess_dev_version(version)
    assert computed == expected_next


@pytest.mark.parametrize(
    "version, match",
    [
        ("1.0.dev1", "choosing custom numbers for the `.devX` distance"),
        ("1.0.post1", "already is a post release"),
    ],
)
def test_no_guess_version_bad(version, match):
    with pytest.raises(ValueError, match=match):
        no_guess_dev_version(m(version, distance=1))


def test_bump_dev_version_zero():
    assert guess_next_version("1.0.dev0") == "1.0"


def test_bump_dev_version_nonzero_raises():
    with pytest.raises(ValueError) as excinfo:
        guess_next_version("1.0.dev1")

    assert str(excinfo.value) == (
        "choosing custom numbers for the `.devX` distance "
        "is not supported.\n "
        "The 1.0.dev1 can't be bumped\n"
        "Please drop the tag or create a new supported one ending in .dev0"
    )


@pytest.mark.parametrize(
    "tag, expected",
    [
        pytest.param("v1.0.0", "1.0.0"),
        pytest.param("v1.0.0-rc.1", "1.0.0rc1"),
        pytest.param("v1.0.0-rc.1+-25259o4382757gjurh54", "1.0.0rc1"),
    ],
)
def test_tag_regex1(tag, expected):
    if "+" in tag:
        # pytest bug wrt cardinality
        with pytest.warns(UserWarning):
            result = meta(tag, config=c)
    else:
        result = meta(tag, config=c)

    assert result.tag.public == expected


@pytest.fixture(
    params=[
        ("SETUPTOOLS_SCM_OVERRIDE_DIRTY", "TrUe"),
        ("SETUPTOOLS_SCM_OVERRIDE_DIRTY", "T"),
        ("SETUPTOOLS_SCM_OVERRIDE_DIRTY", "1"),
        ("SETUPTOOLS_SCM_OVERRIDE_DIRTY", "FaLse"),
        ("SETUPTOOLS_SCM_OVERRIDE_DIRTY", "F"),
        ("SETUPTOOLS_SCM_OVERRIDE_DIRTY", "0"),
        ("SETUPTOOLS_SCM_OVERRIDE_DIRTY", ""),
        ("SETUPTOOLS_SCM_OVERRIDE_DIRTY_FOR_MY_PACKAGE", "true"),
        ("SETUPTOOLS_SCM_OVERRIDE_DIRTY_FOR_MY_PACKAGE", "t"),
        ("SETUPTOOLS_SCM_OVERRIDE_DIRTY_FOR_MY_PACKAGE", "1"),
        ("SETUPTOOLS_SCM_OVERRIDE_DIRTY_FOR_MY_PACKAGE", "false"),
        ("SETUPTOOLS_SCM_OVERRIDE_DIRTY_FOR_MY_PACKAGE", "f"),
        ("SETUPTOOLS_SCM_OVERRIDE_DIRTY_FOR_MY_PACKAGE", "0"),
        ("SETUPTOOLS_SCM_OVERRIDE_DIRTY_FOR_MY_PACKAGE", "anything_else"),
        [
            ("SETUPTOOLS_SCM_OVERRIDE_DIRTY", "true"),
            ("SETUPTOOLS_SCM_OVERRIDE_DIRTY_FOR_MY_PACKAGE", "false"),
        ],
        [
            ("SETUPTOOLS_SCM_OVERRIDE_DIRTY", "false"),
            ("SETUPTOOLS_SCM_OVERRIDE_DIRTY_FOR_MY_PACKAGE", "true"),
        ],
        [
            ("SETUPTOOLS_SCM_OVERRIDE_DIRTY", "true"),
            ("SETUPTOOLS_SCM_OVERRIDE_DIRTY_FOR_MY_PACKAGE", "true"),
        ],
        [
            ("SETUPTOOLS_SCM_OVERRIDE_DIRTY", "false"),
            ("SETUPTOOLS_SCM_OVERRIDE_DIRTY_FOR_MY_PACKAGE", "false"),
        ],
    ],
    ids=[
        "override_all_with_true",
        "override_all_with_t",
        "override_all_with_1",
        "override_all_with_false",
        "override_all_with_f",
        "override_all_with_0",
        "no_override_all",
        "override_my_package_only_with_true",
        "override_my_package_only_with_t",
        "override_my_package_only_with_1",
        "override_my_package_only_with_false",
        "override_my_package_only_with_f",
        "override_my_package_only_with_0",
        "no_override_my_package",
        "override_both_my_package_priority_false",
        "override_both_my_package_priority_true",
        "override_both_global_priority",
        "override_both_false",
    ],
)
def override_dirty_env(request):
    param = request.param
    if not isinstance(param, list):
        param = [param]

    dirty = None
    for key, val in param:
        os.environ[key] = val

        if dirty is not None and key == "SETUPTOOLS_SCM_OVERRIDE_DIRTY":
            continue

        if val.lower() in ["1", "t", "true"]:
            dirty = True
        elif val.lower() in ["0", "f", "false"]:
            dirty = False
        else:
            dirty = None

    yield dirty

    for key, _ in param:
        del os.environ[key]


@pytest.mark.parametrize(
    "is_dirty,distance",
    [
        pytest.param(True, None, id="dirty_no_distance"),
        pytest.param(False, None, id="no_dirty_no_distance"),
        pytest.param(True, 1, id="dirty_distance_1"),
        pytest.param(False, 1, id="no_dirty_distance_1"),
    ],
)
def test_ignore_dirty(override_dirty_env, is_dirty, distance):
    config = Configuration(dist_name="my_package")

    def check_version(version, distance, is_dirty, override_dirty):
        formatted_version = format_version(
            version,
            local_scheme="node-and-date",
            version_scheme="guess-next-dev",
        )

        if (is_dirty and override_dirty is None) or override_dirty:
            dirty_str = "+d20090213"
            if distance is None:
                distance = 0
        else:
            dirty_str = ""

        if distance is None:
            expected_version = "1.2.3"
        else:
            expected_version = f"1.2.4.dev{distance}{dirty_str}"

        assert formatted_version == expected_version

    version = meta("1.2.3", distance=distance, dirty=is_dirty, config=config)
    check_version(version, distance, is_dirty, override_dirty_env)


@pytest.mark.issue("https://github.com/pypa/setuptools_scm/issues/286")
def test_tags_to_versions():
    versions = tags_to_versions(["1.0", "2.0", "3.0"], config=c)
    assert isinstance(versions, list)  # enable subscription


@pytest.mark.issue("https://github.com/pypa/setuptools_scm/issues/471")
def test_version_bump_bad():
    with pytest.raises(
        ValueError,
        match=".*does not end with a number to bump, "
        "please correct or use a custom version scheme",
    ):

        guess_next_version(tag_version="2.0.0-alpha.5-PMC")


def test_format_version_schemes():
    version = meta("1.0", config=c)
    format_version(
        version,
        local_scheme="no-local-version",
        version_scheme=[lambda v: None, "guess-next-dev"],
    )


def date_to_str(date_=None, days_offset=0, fmt="{dt:%y}.{dt.month}.{dt.day}"):
    date_ = date_ or date.today()
    date_ = date_ - timedelta(days=days_offset)
    return fmt.format(dt=date_)


@pytest.mark.parametrize(
    "version, expected_next",
    [
        pytest.param(
            meta(date_to_str(days_offset=3), config=c),
            date_to_str(days_offset=3),
            id="exact",
        ),
        pytest.param(
            meta(date_to_str() + ".1", config=c), date_to_str() + ".1", id="exact patch"
        ),
        pytest.param(
            meta("20.01.02", config=c),
            "20.1.2",
            id="leading 0s",
        ),
        pytest.param(
            meta(date_to_str(days_offset=3), config=c, dirty=True),
            date_to_str() + ".0.dev0",
            id="dirty other day",
        ),
        pytest.param(
            meta(date_to_str(), config=c, distance=2, branch="default"),
            date_to_str() + ".1.dev2",
            id="normal branch",
        ),
        pytest.param(
            meta(date_to_str(fmt="{dt:%Y}.{dt.month}.{dt.day}"), config=c),
            date_to_str(fmt="{dt:%Y}.{dt.month}.{dt.day}"),
            id="4 digits year",
        ),
        pytest.param(
            meta(date_to_str(), config=c, distance=2, branch="release-2021.05.06"),
            "2021.05.06",
            id="release branch",
        ),
        pytest.param(
            meta(date_to_str() + ".2", config=c, distance=2, branch="release-21.5.1"),
            "21.5.1",
            id="release branch short",
        ),
        pytest.param(
            meta(
                date_to_str(days_offset=3) + ".2",
                config=c,
                node_date=date.today() - timedelta(days=2),
            ),
            date_to_str(days_offset=3) + ".2",
            id="node date clean",
        ),
        pytest.param(
            meta(
                date_to_str(days_offset=2) + ".2",
                config=c,
                distance=2,
                node_date=date.today() - timedelta(days=2),
            ),
            date_to_str(date.today() - timedelta(days=2)) + ".3.dev2",
            id="node date distance",
        ),
        pytest.param(
            meta(
                "1.2.0",
                config=c,
                distance=2,
                node_date=date.today() - timedelta(days=2),
            ),
            date_to_str(days_offset=2) + ".0.dev2",
            marks=pytest.mark.filterwarnings(
                "ignore:.*not correspond to a valid versioning date.*:UserWarning"
            ),
            id="using on old version tag",
        ),
    ],
)
def test_calver_by_date(version, expected_next):
    computed = calver_by_date(version)
    assert computed == expected_next


@pytest.mark.parametrize(
    "version, expected_next",
    [
        pytest.param(meta("1.0.0", config=c), "1.0.0", id="SemVer exact"),
        pytest.param(
            meta("1.0.0", config=c, dirty=True),
            "1.0.0",
            id="SemVer dirty",
            marks=pytest.mark.xfail,
        ),
    ],
)
def test_calver_by_date_semver(version, expected_next):
    computed = calver_by_date(version)
    assert computed == expected_next


def test_calver_by_date_future_warning():
    with pytest.warns(UserWarning, match="your previous tag*"):
        calver_by_date(meta(date_to_str(days_offset=-2), config=c, distance=2))


def test_custom_version_cls():
    """Test that we can pass our own version class instead of pkg_resources"""

    class MyVersion:
        def __init__(self, tag_str: str):
            self.tag = tag_str

        def __repr__(self):
            return "Custom %s" % self.tag

    scm_version = meta("1.0.0-foo", config=Configuration(version_cls=MyVersion))

    assert isinstance(scm_version.tag, MyVersion)
    assert repr(scm_version.tag) == "Custom 1.0.0-foo"
