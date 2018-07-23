from setuptools_scm.config import Configuration

import pytest


@pytest.mark.parametrize(
    "tag, expected_version",
    [
        ("apache-arrow-0.9.0", "0.9.0"),
        ("arrow-0.9.0", "0.9.0"),
        ("arrow-0.9.0-rc", "0.9.0-rc"),
    ],
)
def test_tag_regex(tag, expected_version):
    config = Configuration()
    match = config.tag_regex.match(tag)
    version = match.group("version")
    assert version == expected_version
