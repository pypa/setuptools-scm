from __future__ import annotations

import itertools

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

import pytest

from setuptools_scm._run_cmd import has_command

if TYPE_CHECKING:
    pass


class WorkDir:
    """a simple model for a"""

    commit_command: str
    signed_commit_command: str
    add_command: str
    tag_command: str

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

    def create_basic_setup_py(
        self, name: str = "test-package", use_scm_version: str = "True"
    ) -> None:
        """Create a basic setup.py file with setuptools_scm configuration."""
        self.write(
            "setup.py",
            f"""__import__('setuptools').setup(
    name="{name}",
    use_scm_version={use_scm_version},
)""",
        )

    def create_basic_pyproject_toml(
        self, name: str = "test-package", dynamic_version: bool = True
    ) -> None:
        """Create a basic pyproject.toml file with setuptools_scm configuration."""
        dynamic_section = 'dynamic = ["version"]' if dynamic_version else ""
        self.write(
            "pyproject.toml",
            f"""[build-system]
requires = ["setuptools>=64", "setuptools_scm>=8"]
build-backend = "setuptools.build_meta"

[project]
name = "{name}"
{dynamic_section}

[tool.setuptools_scm]
""",
        )

    def create_basic_setup_cfg(self, name: str = "test-package") -> None:
        """Create a basic setup.cfg file with metadata."""
        self.write(
            "setup.cfg",
            f"""[metadata]
name = {name}
""",
        )

    def create_test_file(
        self, filename: str = "test.txt", content: str = "test content"
    ) -> None:
        """Create a test file and commit it to the repository."""
        # Create parent directories if they don't exist
        path = self.cwd / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        self.write(filename, content)
        self.add_and_commit()

    def create_tag(self, tag: str = "1.0.0") -> None:
        """Create a tag using the configured tag_command."""
        if hasattr(self, "tag_command"):
            self(self.tag_command, tag=tag)
        else:
            raise RuntimeError("No tag_command configured")

    def configure_git_commands(self) -> None:
        """Configure git commands without initializing the repository."""
        self.add_command = "git add ."
        self.commit_command = "git commit -m test-{reason}"
        self.tag_command = "git tag {tag}"

    def configure_hg_commands(self) -> None:
        """Configure mercurial commands without initializing the repository."""
        self.add_command = "hg add ."
        self.commit_command = 'hg commit -m test-{reason} -u test -d "0 0"'
        self.tag_command = "hg tag {tag}"

    def setup_git(
        self, monkeypatch: pytest.MonkeyPatch | None = None, *, init: bool = True
    ) -> WorkDir:
        """Set up git SCM for this WorkDir.

        Args:
            monkeypatch: Optional pytest MonkeyPatch to clear HOME environment
            init: Whether to initialize the git repository (default: True)

        Returns:
            Self for method chaining

        Raises:
            pytest.skip: If git executable is not found
        """
        if not has_command("git", warn=False):
            pytest.skip("git executable not found")

        self.configure_git_commands()

        if init:
            if monkeypatch:
                monkeypatch.delenv("HOME", raising=False)
            self("git init")
            self("git config user.email test@example.com")
            self('git config user.name "a test"')

        return self

    def setup_hg(self, *, init: bool = True) -> WorkDir:
        """Set up mercurial SCM for this WorkDir.

        Args:
            init: Whether to initialize the mercurial repository (default: True)

        Returns:
            Self for method chaining

        Raises:
            pytest.skip: If hg executable is not found
        """
        if not has_command("hg", warn=False):
            pytest.skip("hg executable not found")

        self.configure_hg_commands()

        if init:
            self("hg init")

        return self
