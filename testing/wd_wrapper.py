from __future__ import annotations

import itertools

from pathlib import Path
from typing import Any


class WorkDir:
    """a simple model for a"""

    commit_command: str
    signed_commit_command: str
    add_command: str

    def __repr__(self) -> str:
        return f"<WD {self.cwd}>"

    def __init__(self, cwd: Path) -> None:
        self.cwd = cwd
        self.__counter = itertools.count()

    def __call__(self, cmd: list[str] | str, *, timeout: int = 10, **kw: object) -> str:
        if kw:
            assert isinstance(cmd, str), "formatting the command requires text input"
            cmd = cmd.format(**kw)
        from setuptools_scm._run_cmd import run

        return run(cmd, cwd=self.cwd, timeout=timeout).stdout

    def write(self, name: str, content: str | bytes) -> Path:
        path = self.cwd / name
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
        return path

    def _reason(self, given_reason: str | None) -> str:
        if given_reason is None:
            return f"number-{next(self.__counter)}"
        else:
            return given_reason

    def add_and_commit(
        self, reason: str | None = None, signed: bool = False, **kwargs: object
    ) -> None:
        self(self.add_command)
        self.commit(reason=reason, signed=signed, **kwargs)

    def commit(self, reason: str | None = None, signed: bool = False) -> None:
        reason = self._reason(reason)
        self(
            self.commit_command if not signed else self.signed_commit_command,
            reason=reason,
        )

    def commit_testfile(self, reason: str | None = None, signed: bool = False) -> None:
        reason = self._reason(reason)
        self.write("test.txt", f"test {reason}")
        self(self.add_command)
        self.commit(reason=reason, signed=signed)

    def get_version(self, **kw: Any) -> str:
        __tracebackhide__ = True
        from setuptools_scm import get_version

        version = get_version(root=self.cwd, fallback_root=self.cwd, **kw)
        print(self.cwd.name, version, sep=": ")
        return version
