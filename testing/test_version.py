import pytest
from setuptools_scm.config import Configuration
from setuptools_scm.version import meta, simplified_semver_version, tags_to_versions


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


@pytest.mark.parametrize(
    "tag, expected",
    [
        pytest.param("v1.0.0", "1.0.0"),
        pytest.param("v1.0.0-rc.1", "1.0.0rc1"),
        pytest.param("v1.0.0-rc.1+-25259o4382757gjurh54", "1.0.0rc1"),
    ],
)
def test_tag_regex1(tag, expected):
    config = Configuration()
    config.tag_regex = r"^(?P<prefix>v)?(?P<version>[^\+]+)(?P<suffix>.*)?$"
    if "+" in tag:
        # pytest bug wrt cardinality
        with pytest.warns(UserWarning):
            result = meta(tag, config=config)
    else:
        result = meta(tag, config=config)

    assert result.tag.public == expected


@pytest.mark.issue("https://github.com/pypa/setuptools_scm/issues/286")
def test_tags_to_versions():
    config = Configuration()
    versions = tags_to_versions(["1.0", "2.0", "3.0"], config=config)
    assert isinstance(versions, list)  # enable subscription
