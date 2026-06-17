"""Tests for the workdir-based chain API.

The chain is: VcsEnvironment -> Configuration -> Workdir -> ScmVersion -> format()
No context managers are needed.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from vcs_versioning import VcsEnvironment
from vcs_versioning._backends._scm_workdir import ScmWorkdir
from vcs_versioning._environment import (
    _DEFAULT_HG_COMMAND,
    _DEFAULT_SUBPROCESS_TIMEOUT,
    resolve_runtime_env,
)
from vcs_versioning._fallback_workdir import FallbackWorkdir
from vcs_versioning._pyproject_reading import PyProjectData
from vcs_versioning.overrides import GlobalOverrides, get_active_vcs_env

if TYPE_CHECKING:
    from vcs_versioning.test_api import WorkDir


def _empty_pyproject() -> PyProjectData:
    """An empty PyProjectData so tests don't inherit ambient pyproject.toml."""
    return PyProjectData.empty("vcs-versioning")


@pytest.fixture
def wd(wd: WorkDir, monkeypatch: pytest.MonkeyPatch) -> WorkDir:
    return wd.setup_git(monkeypatch)


class TestVcsEnvironment:
    def test_defaults(self) -> None:
        env = VcsEnvironment()
        assert env.subprocess_timeout == _DEFAULT_SUBPROCESS_TIMEOUT
        assert env.hg_command == _DEFAULT_HG_COMMAND
        assert env.source_date_epoch is None
        assert env.ignore_vcs_roots == ()
        assert env.tool_names == ("VCS_VERSIONING",)

    def test_from_env_no_args_uses_vcs_versioning(self) -> None:
        env = VcsEnvironment.from_env(env={"VCS_VERSIONING_SUBPROCESS_TIMEOUT": "77"})
        assert env.subprocess_timeout == 77
        assert env.tool_names == ("VCS_VERSIONING",)

    def test_from_env_tool_prepended_to_fallback(self) -> None:
        env = VcsEnvironment.from_env("MY_TOOL", env={})
        assert env.tool_names == ("MY_TOOL", "VCS_VERSIONING")

    def test_from_env_reads_timeout(self) -> None:
        env = VcsEnvironment.from_env(
            "MY_TOOL", env={"MY_TOOL_SUBPROCESS_TIMEOUT": "120"}
        )
        assert env.subprocess_timeout == 120

    def test_from_env_reads_source_date_epoch(self) -> None:
        env = VcsEnvironment.from_env(env={"SOURCE_DATE_EPOCH": "1234567890"})
        assert env.source_date_epoch == 1234567890

    def test_from_env_reads_hg_command(self) -> None:
        env = VcsEnvironment.from_env(
            "MY_TOOL", env={"MY_TOOL_HG_COMMAND": "/usr/bin/hg"}
        )
        assert env.hg_command == "/usr/bin/hg"

    def test_from_env_invalid_timeout_uses_default(self) -> None:
        env = VcsEnvironment.from_env(env={"VCS_VERSIONING_SUBPROCESS_TIMEOUT": "bad"})
        assert env.subprocess_timeout == _DEFAULT_SUBPROCESS_TIMEOUT

    def test_frozen(self) -> None:
        env = VcsEnvironment()
        with pytest.raises(AttributeError):
            env.subprocess_timeout = 999  # type: ignore[misc]


class TestBuildConfig:
    def test_build_config_sets_env(self, wd: WorkDir) -> None:
        env = VcsEnvironment.from_env(env={"SOURCE_DATE_EPOCH": "1234567890"})
        config = env.build_config(
            pyproject_data=_empty_pyproject(),
            relative_to=str(wd.cwd / "pyproject.toml"),
        )
        assert config._env is env
        assert config._env.source_date_epoch == 1234567890

    def test_build_config_forwards_kwargs(self, wd: WorkDir) -> None:
        env = VcsEnvironment.from_env()
        config = env.build_config(
            pyproject_data=_empty_pyproject(),
            relative_to=str(wd.cwd / "pyproject.toml"),
            dist_name="explicit",
        )
        assert config.dist_name == "explicit"

    def test_config_without_explicit_env_gets_default(self, wd: WorkDir) -> None:
        from vcs_versioning._config import Configuration
        from vcs_versioning._environment import VcsEnvironment

        config = Configuration(relative_to=str(wd.cwd / "pyproject.toml"))
        assert config._env is None
        with pytest.warns(
            DeprecationWarning, match="without VcsEnvironment.*build_config"
        ):
            env = config.env
        assert isinstance(env, VcsEnvironment)


class TestChainDiscoverWorkdir:
    def test_discover_finds_git(self, wd: WorkDir) -> None:
        wd.commit_testfile()
        env = VcsEnvironment.from_env()
        config = env.build_config(
            pyproject_data=_empty_pyproject(),
            relative_to=str(wd.cwd / "pyproject.toml"),
        )
        workdir = config.discover_workdir()
        assert workdir is not None
        assert isinstance(workdir, ScmWorkdir)
        assert workdir.path == wd.cwd

    def test_discover_returns_none_for_non_vcs(self, tmp_path: Path) -> None:
        env = VcsEnvironment.from_env()
        config = env.build_config(
            pyproject_data=_empty_pyproject(),
            relative_to=str(tmp_path / "pyproject.toml"),
        )
        workdir = config.discover_workdir()
        assert workdir is None or isinstance(workdir, FallbackWorkdir)


class TestFullChain:
    def test_tagged_version(self, wd: WorkDir) -> None:
        """Full chain: env -> config -> workdir -> scm_version -> format()."""
        wd.commit_testfile()
        wd("git tag v1.0.0")

        env = VcsEnvironment.from_env()
        config = env.build_config(
            pyproject_data=_empty_pyproject(),
            relative_to=str(wd.cwd / "pyproject.toml"),
        )
        workdir = config.discover_workdir()
        assert workdir is not None

        scm_version = workdir.get_scm_version()
        assert scm_version is not None

        version_string = scm_version.format()
        assert version_string == "1.0.0"

    def test_dev_version(self, wd: WorkDir) -> None:
        wd.commit_testfile()
        wd("git tag v1.0.0")
        wd.commit_testfile()

        env = VcsEnvironment.from_env()
        config = env.build_config(
            pyproject_data=_empty_pyproject(),
            relative_to=str(wd.cwd / "pyproject.toml"),
        )
        workdir = config.discover_workdir()
        assert workdir is not None

        scm_version = workdir.get_scm_version()
        assert scm_version is not None
        assert scm_version.distance == 1

        version_string = scm_version.format()
        assert "1.0.1.dev1" in version_string

    def test_workdir_receives_config(self, wd: WorkDir) -> None:
        wd.commit_testfile()
        env = VcsEnvironment.from_env()
        config = env.build_config(
            pyproject_data=_empty_pyproject(),
            relative_to=str(wd.cwd / "pyproject.toml"),
        )
        workdir = config.discover_workdir()
        assert workdir is not None
        assert workdir._config is config

    def test_timeout_threaded_to_workdir(self, wd: WorkDir) -> None:
        wd.commit_testfile()
        wd("git tag v1.0.0")

        env = VcsEnvironment.from_env(env={"VCS_VERSIONING_SUBPROCESS_TIMEOUT": "999"})
        config = env.build_config(
            pyproject_data=_empty_pyproject(),
            relative_to=str(wd.cwd / "pyproject.toml"),
        )
        workdir = config.discover_workdir()
        assert isinstance(workdir, ScmWorkdir)
        assert workdir._subprocess_timeout == 999

        scm_version = workdir.get_scm_version()
        assert scm_version is not None

    def test_source_date_epoch_threaded(self, wd: WorkDir) -> None:
        wd.commit_testfile()
        wd("git tag v1.0.0")
        wd.commit_testfile()

        env = VcsEnvironment.from_env(env={"SOURCE_DATE_EPOCH": "1234567890"})
        config = env.build_config(
            pyproject_data=_empty_pyproject(),
            relative_to=str(wd.cwd / "pyproject.toml"),
        )
        workdir = config.discover_workdir()
        assert workdir is not None

        scm_version = workdir.get_scm_version()
        assert scm_version is not None
        assert scm_version.time.year == 2009


class TestGetActiveVcsEnv:
    def test_returns_env_from_session_context(self) -> None:
        active = get_active_vcs_env()
        assert active is not None
        assert "SETUPTOOLS_SCM" in active.tool_names

    def test_nested_context_overrides(self) -> None:
        with GlobalOverrides.from_env("MY_TOOL", env={}) as ctx:
            active = get_active_vcs_env()
            assert active is not None
            assert active is ctx.vcs_env
            assert "MY_TOOL" in active.tool_names
        # session context is restored
        active = get_active_vcs_env()
        assert active is not None
        assert "SETUPTOOLS_SCM" in active.tool_names


class TestResolveRuntimeEnv:
    def test_returns_fresh_env_with_active_tool_names(self) -> None:
        env = resolve_runtime_env()
        assert isinstance(env, VcsEnvironment)
        assert "SETUPTOOLS_SCM" in env.tool_names
        assert "VCS_VERSIONING" in env.tool_names

    def test_preserves_tool_names_from_nested_context(self) -> None:
        with GlobalOverrides.from_env("CUSTOM_TOOL", env={}):
            env = resolve_runtime_env()
            assert "CUSTOM_TOOL" in env.tool_names
            assert "VCS_VERSIONING" in env.tool_names

    def test_merges_overridden_fields_from_context(self) -> None:
        with GlobalOverrides.from_env("TEST", env={"TEST_SUBPROCESS_TIMEOUT": "200"}):
            with GlobalOverrides.from_active(subprocess_timeout=999):
                env = resolve_runtime_env()
                assert env.subprocess_timeout == 999

    def test_reads_process_env_for_fresh_values(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SETUPTOOLS_SCM_IGNORE_VCS_ROOTS", "/tmp/ignore-me")
        env = resolve_runtime_env()
        assert "/tmp/ignore-me" in env.ignore_vcs_roots


class TestFrozenLegacyConfig:
    def test_proxies_non_deprecated_attrs(self) -> None:
        from vcs_versioning._config import Configuration, FrozenLegacyConfig

        config = Configuration()
        frozen = FrozenLegacyConfig(config)
        assert frozen.version_scheme == config.version_scheme
        assert frozen.dist_name == config.dist_name

    def test_deprecated_attr_emits_warning(self) -> None:
        from vcs_versioning._config import Configuration, FrozenLegacyConfig

        config = Configuration()
        frozen = FrozenLegacyConfig(config)
        with pytest.warns(DeprecationWarning, match="absolute_root.*deprecated"):
            _ = frozen.absolute_root

    def test_warns_only_once_per_attr(self) -> None:
        from vcs_versioning._config import Configuration, FrozenLegacyConfig

        config = Configuration()
        frozen = FrozenLegacyConfig(config)
        with pytest.warns(DeprecationWarning):
            _ = frozen.absolute_root
        # Second access should not warn
        import warnings as _w

        with _w.catch_warnings():
            _w.simplefilter("error")
            _ = frozen.absolute_root

    def test_setattr_raises(self) -> None:
        from vcs_versioning._config import Configuration, FrozenLegacyConfig

        config = Configuration()
        frozen = FrozenLegacyConfig(config)
        with pytest.raises((AttributeError, dataclasses.FrozenInstanceError)):
            frozen.version_scheme = "something"  # type: ignore[attr-defined]
