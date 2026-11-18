from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from vcs_versioning._run_cmd import run


@pytest.mark.parametrize("merge_stderr", [False, True])
def test_output_capture_preserves_environment_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, merge_stderr: bool
) -> None:
    monkeypatch.setenv("GIT_DIR", "unrelated-repository")
    monkeypatch.setenv("PYTHONNOUSERSITE", "1")
    monkeypatch.setenv("PYTHONPATH", os.pathsep.join(["pip-build-env-example", "."]))
    code = """
import os
assert 'GIT_DIR' not in os.environ
assert 'PYTHONNOUSERSITE' not in os.environ
assert 'pip-build-env-' not in os.environ.get('PYTHONPATH', '')
assert os.environ['LC_ALL'] == 'C.UTF-8'
os.write(1, b'before\\n')
os.write(2, b'between\\n')
os.write(1, b'after\\n')
"""

    result = run([sys.executable, "-c", code], tmp_path, merge_stderr=merge_stderr)

    assert result.returncode == 0
    if merge_stderr:
        assert result.stdout == "before\nbetween\nafter"
        assert result.stderr is None
    else:
        assert result.stdout == "before\nafter"
        assert result.stderr == "between"


def test_default_output_streams_remain_separate(tmp_path: Path) -> None:
    result = run(
        [sys.executable, "-c", "import os; os.write(1, b'out'); os.write(2, b'err')"],
        tmp_path,
    )

    assert (result.stdout, result.stderr) == ("out", "err")
