import pytest
from setuptools_scm.version import meta, simplified_semver_version


@pytest.mark.parametrize('version, expected_next', [
    pytest.param(meta("1.0.0"), "1.0.0", id='exact'),

    pytest.param(meta("1.0"), "1.0.0", id='short_tag'),
    pytest.param(meta("1.0.0", distance=2, branch='default'), "1.0.1.dev2",
                 id='normal_branch'),

    pytest.param(meta("1.0", distance=2, branch='default'), "1.0.1.dev2",
                 id='normal_branch_short_tag'),
    pytest.param(meta("1.0.0", distance=2, branch='feature'), "1.1.0.dev2",
                 id='feature_branch'),
    pytest.param(meta("1.0", distance=2, branch='feature'), "1.1.0.dev2",
                 id='feature_branch_short_tag'),
    pytest.param(meta("1.0.0", distance=2, branch='features/test'), "1.1.0.dev2",
                 id='feature_in_branch'),
])
def test_next_semver(version, expected_next):
    computed = simplified_semver_version(version)
    assert computed == expected_next
