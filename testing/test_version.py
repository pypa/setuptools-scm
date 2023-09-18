from __future__ import annotations

from dataclasses import replace
from datetime import date
from datetime import timedelta
from typing import Any

import pytest

from setuptools_scm import Configuration
from setuptools_scm import NonNormalizedVersion
from setuptools_scm.version import calver_by_date
from setuptools_scm.version import format_version
from setuptools_scm.version import guess_next_date_ver
from setuptools_scm.version import guess_next_version
from setuptools_scm.version import meta
from setuptools_scm.version import no_guess_dev_version
from setuptools_scm.version import release_branch_semver_version
from setuptools_scm.version import ScmVersion
from setuptools_scm.version import simplified_semver_version


c = Configuration()
c_non_normalize = Configuration(version_cls=NonNormalizedVersion)


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
def test_next_semver(version: ScmVersion, expected_next: str) -> None:
    computed = simplified_semver_version(version)
    assert computed == expected_next


def test_next_semver_bad_tag() -> None:
    version = meta("1.0.0-foo", preformatted=True, config=c)
    with pytest.raises(
        ValueError, match=r"1\.0\.0-foo.* can't be parsed as numeric version"
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
def test_next_release_branch_semver(version: ScmVersion, expected_next: str) -> None:
    computed = release_branch_semver_version(version)
    assert computed == expected_next


def m(tag: str, **kw: Any) -> ScmVersion:
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
def test_no_guess_version(version: ScmVersion, expected_next: str) -> None:
    computed = no_guess_dev_version(version)
    assert computed == expected_next


@pytest.mark.parametrize(
    "version, match",
    [
        ("1.0.dev1", "choosing custom numbers for the `.devX` distance"),
        ("1.0.post1", "already is a post release"),
    ],
)
def test_no_guess_version_bad(version: str, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        no_guess_dev_version(m(version, distance=1))


def test_bump_dev_version_zero() -> None:
    assert guess_next_version(m("1.0.dev0")) == "1.0"


def test_bump_dev_version_nonzero_raises() -> None:
    with pytest.raises(ValueError) as excinfo:
        guess_next_version(m("1.0.dev1"))

    assert str(excinfo.value) == (
        "choosing custom numbers for the `.devX` distance "
        "is not supported.\n "
        "The 1.0.dev1 can't be bumped\n"
        "Please drop the tag or create a new supported one ending in .dev0"
    )


@pytest.mark.parametrize(
    "tag, expected",
    [
        ("v1.0.0", "1.0.0"),
        ("v1.0.0-rc.1", "1.0.0rc1"),
        ("v1.0.0-rc.1+-25259o4382757gjurh54", "1.0.0rc1"),
    ],
)
def test_tag_regex1(tag: str, expected: str) -> None:
    if "+" in tag:
        # pytest bug wrt cardinality
        with pytest.warns(UserWarning):
            result = meta(tag, config=c)
    else:
        result = meta(tag, config=c)
    assert not isinstance(result.tag, str)
    assert result.tag.public == expected


@pytest.mark.issue("https://github.com/pypa/setuptools_scm/issues/471")
def test_version_bump_bad() -> None:
    class YikesVersion:
        val: str

        def __init__(self, val: str):
            self.val = val

        def __str__(self) -> str:
            return self.val

    config = Configuration(version_cls=YikesVersion)  # type: ignore[arg-type]
    with pytest.raises(
        ValueError,
        match=".*does not end with a number to bump, "
        "please correct or use a custom version scheme",
    ):
        guess_next_version(tag_version=meta("2.0.0-alpha.5-PMC", config=config))


def test_format_version_schemes() -> None:
    version = meta(
        "1.0",
        config=replace(
            c,
            local_scheme="no-local-version",
            version_scheme=[  # type: ignore[arg-type]
                lambda v: None,
                "guess-next-dev",
            ],
        ),
    )
    assert format_version(version) == "1.0"


def test_custom_version_schemes() -> None:
    version = meta(
        "1.0",
        config=replace(
            c,
            local_scheme="no-local-version",
            version_scheme="setuptools_scm.version:no_guess_dev_version",
        ),
    )
    custom_computed = format_version(version)
    assert custom_computed == no_guess_dev_version(version)


def date_offset(base_date: date | None = None, days_offset: int = 0) -> date:
    if base_date is None:
        from setuptools_scm.version import _source_epoch_or_utc_now

        base_date = _source_epoch_or_utc_now().date()
    return base_date - timedelta(days=days_offset)


def date_to_str(
    base_date: date | None = None,
    days_offset: int = 0,
    fmt: str = "%y.%m.%d",
) -> str:
    return format(date_offset(base_date, days_offset), fmt)


@pytest.mark.parametrize(
    "version, expected_next",
    [
        pytest.param(
            meta(date_to_str(days_offset=3), config=c_non_normalize),
            date_to_str(days_offset=3),
            id="exact",
        ),
        pytest.param(
            meta(date_to_str() + ".1", config=c_non_normalize),
            date_to_str() + ".1",
            id="exact patch",
        ),
        pytest.param(
            meta("20.01.02", config=c),
            "20.1.2",
            id="leading 0s",
        ),
        pytest.param(
            meta(date_to_str(days_offset=3), config=c_non_normalize, dirty=True),
            date_to_str() + ".0.dev0",
            id="dirty other day",
        ),
        pytest.param(
            meta(date_to_str(), config=c_non_normalize, distance=2, branch="default"),
            date_to_str() + ".1.dev2",
            id="normal branch",
        ),
        pytest.param(
            meta(date_to_str(fmt="%Y.%m.%d"), config=c_non_normalize),
            date_to_str(fmt="%Y.%m.%d"),
            id="4 digits year",
        ),
        pytest.param(
            meta(
                date_to_str(),
                config=c_non_normalize,
                distance=2,
                branch="release-2021.05.06",
            ),
            "2021.05.06",
            id="release branch",
        ),
        pytest.param(
            meta(
                date_to_str() + ".2",
                config=c_non_normalize,
                distance=2,
                branch="release-21.5.1",
            ),
            "21.5.1",
            id="release branch short",
        ),
        pytest.param(
            meta(
                date_to_str(days_offset=3) + ".2",
                config=c_non_normalize,
                node_date=date_offset(days_offset=2),
            ),
            date_to_str(days_offset=3) + ".2",
            id="node date clean",
        ),
        pytest.param(
            meta(
                date_to_str(days_offset=2) + ".2",
                config=c_non_normalize,
                distance=2,
                node_date=date_offset(days_offset=2),
            ),
            date_to_str(days_offset=2) + ".3.dev2",
            id="node date distance",
        ),
        pytest.param(
            meta(
                "1.2.0",
                config=c_non_normalize,
                distance=2,
                node_date=date_offset(days_offset=2),
            ),
            date_to_str(days_offset=2) + ".0.dev2",
            marks=pytest.mark.filterwarnings(
                "ignore:.*not correspond to a valid versioning date.*:UserWarning"
            ),
            id="using on old version tag",
        ),
    ],
)
def test_calver_by_date(version: ScmVersion, expected_next: str) -> None:
    computed = calver_by_date(version)
    assert computed == expected_next


@pytest.mark.parametrize(
    "version, expected_next",
    [
        pytest.param(meta("1.0.0", config=c), "1.0.0", id="SemVer exact stays"),
        pytest.param(
            meta("1.0.0", config=c_non_normalize, dirty=True),
            "09.02.13.1.dev0",
            id="SemVer dirty is replaced by date",
            marks=pytest.mark.filterwarnings("ignore:.*legacy version.*:UserWarning"),
        ),
    ],
)
def test_calver_by_date_semver(version: ScmVersion, expected_next: str) -> None:
    computed = calver_by_date(version)
    assert computed == expected_next


def test_calver_by_date_future_warning() -> None:
    with pytest.warns(UserWarning, match="your previous tag*"):
        calver_by_date(
            meta(date_to_str(days_offset=-2), config=c_non_normalize, distance=2)
        )


@pytest.mark.parametrize(
    ["tag", "node_date", "expected"],
    [
        pytest.param("20.03.03", date(2020, 3, 4), "20.03.04.0", id="next day"),
        pytest.param("20.03.03", date(2020, 3, 3), "20.03.03.1", id="same day"),
        pytest.param(
            "20.03.03.2", date(2020, 3, 3), "20.03.03.3", id="same day with patch"
        ),
        pytest.param(
            "v20.03.03", date(2020, 3, 4), "v20.03.04.0", id="next day with v prefix"
        ),
    ],
)
def test_calver_guess_next_data(tag: str, node_date: date, expected: str) -> None:
    version = meta(tag, config=c_non_normalize, node_date=node_date)
    next = guess_next_date_ver(
        version,
        node_date=node_date,
        version_cls=c_non_normalize.version_cls,
    )
    assert next == expected


def test_custom_version_cls() -> None:
    """Test that we can pass our own version class instead of pkg_resources"""

    class MyVersion:
        def __init__(self, tag_str: str):
            self.tag = tag_str

        def __str__(self) -> str:
            return "Custom %s" % self.tag

        def __repr__(self) -> str:
            return "MyVersion<Custom%s>" % self.tag

    config = Configuration(version_cls=MyVersion)  # type: ignore[arg-type]
    scm_version = meta("1.0.0-foo", config=config)

    assert isinstance(scm_version.tag, MyVersion)
    assert str(scm_version.tag) == "Custom 1.0.0-foo"
