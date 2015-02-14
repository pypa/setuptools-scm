import time
import pytest
from hgdistver import format_version, guess_next_tag


@pytest.mark.parametrize('tag, expected', [
    ('1.1', '1.2.dev'),
    ('1.2.dev', '1.2.dev'),
    pytest.mark.xfail(('1.1a2', '1.1a3.dev'), reason='bug'),
    ])
def test_next_tag(tag, expected):
    assert guess_next_tag(tag) == expected


@pytest.mark.parametrize('tag, distance, dirty, current, guessed', [
    ('1.1', None, False, '1.1', '1.1'),
    ('1.1', 0, False, '1.1.post0+n00', '1.2.dev0+n00'),
    ('1.1', 0, True, '1.1.post0+n00.time', '1.2.dev0+n00.time'),
    ('1.1', 3, False, '1.1.post3+n00', '1.2.dev3+n00'),
    ('1.1', 3, True, '1.1.post3+n00.time', '1.2.dev3+n00.time'),
    pytest.mark.xfail(('1.1.dev', 3, False, '1.1.dev3', '1.1.dev3'),
                      reason='missed case'),
    ])
@pytest.mark.parametrize('take_guess', [True, False])
def test_format_version(take_guess, tag, distance, dirty,
                        current, guessed, monkeypatch):
    monkeypatch.setattr(time, 'strftime', lambda x: x[0] + 'time')
    version = dict(locals(), node='00')
    if take_guess:
        assert format_version(version, True) == guessed
    else:
        assert format_version(version, False) == current
