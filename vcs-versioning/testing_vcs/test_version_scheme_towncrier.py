"""Tests for the towncrier-fragments version scheme."""

from __future__ import annotations

from pathlib import Path

import pytest
from vcs_versioning import _config
from vcs_versioning._scm_version import ScmVersion
from vcs_versioning._version_cls import Version
from vcs_versioning._version_schemes._towncrier import (
    _determine_bump_type,
    _find_fragments,
    version_from_fragments,
)


@pytest.fixture
def changelog_dir(tmp_path: Path) -> Path:
    """Create a temporary changelog.d directory."""
    changelog_d = tmp_path / "changelog.d"
    changelog_d.mkdir()
    return changelog_d


@pytest.fixture
def config(tmp_path: Path) -> _config.Configuration:
    """Create a minimal configuration object."""
    return _config.Configuration(root=tmp_path)


def test_find_fragments_empty(changelog_dir: Path) -> None:
    """Test finding fragments in an empty directory."""
    fragments = _find_fragments(changelog_dir.parent)
    assert all(len(frags) == 0 for frags in fragments.values())


def test_find_fragments_feature(changelog_dir: Path) -> None:
    """Test finding feature fragments."""
    (changelog_dir / "123.feature.md").write_text("Add new feature")
    (changelog_dir / "456.feature.md").write_text("Another feature")

    fragments = _find_fragments(changelog_dir.parent)
    assert len(fragments["feature"]) == 2
    assert "123.feature.md" in fragments["feature"]
    assert "456.feature.md" in fragments["feature"]


def test_find_fragments_bugfix(changelog_dir: Path) -> None:
    """Test finding bugfix fragments."""
    (changelog_dir / "789.bugfix.md").write_text("Fix bug")

    fragments = _find_fragments(changelog_dir.parent)
    assert len(fragments["bugfix"]) == 1
    assert "789.bugfix.md" in fragments["bugfix"]


def test_find_fragments_major(changelog_dir: Path) -> None:
    """Test finding major fragments."""
    (changelog_dir / "100.major.md").write_text("Major version bump")

    fragments = _find_fragments(changelog_dir.parent)
    assert len(fragments["major"]) == 1
    assert "100.major.md" in fragments["major"]


def test_find_fragments_breaking(changelog_dir: Path) -> None:
    """Test finding breaking fragments."""
    (changelog_dir / "200.breaking.md").write_text("Breaking change")

    fragments = _find_fragments(changelog_dir.parent)
    assert len(fragments["breaking"]) == 1
    assert "200.breaking.md" in fragments["breaking"]


def test_find_fragments_removal(changelog_dir: Path) -> None:
    """Test finding removal fragments."""
    (changelog_dir / "321.removal.md").write_text("Remove deprecated API")

    fragments = _find_fragments(changelog_dir.parent)
    assert len(fragments["removal"]) == 1
    assert "321.removal.md" in fragments["removal"]


def test_find_fragments_deprecation(changelog_dir: Path) -> None:
    """Test finding deprecation fragments."""
    (changelog_dir / "654.deprecation.md").write_text("Deprecate old method")

    fragments = _find_fragments(changelog_dir.parent)
    assert len(fragments["deprecation"]) == 1
    assert "654.deprecation.md" in fragments["deprecation"]


def test_find_fragments_doc(changelog_dir: Path) -> None:
    """Test finding doc fragments."""
    (changelog_dir / "111.doc.md").write_text("Update documentation")

    fragments = _find_fragments(changelog_dir.parent)
    assert len(fragments["doc"]) == 1
    assert "111.doc.md" in fragments["doc"]


def test_find_fragments_misc(changelog_dir: Path) -> None:
    """Test finding misc fragments."""
    (changelog_dir / "222.misc.md").write_text("Refactor internal code")

    fragments = _find_fragments(changelog_dir.parent)
    assert len(fragments["misc"]) == 1
    assert "222.misc.md" in fragments["misc"]


def test_find_fragments_ignores_template(changelog_dir: Path) -> None:
    """Test that template files are ignored."""
    (changelog_dir / "template.md").write_text("Template content")
    (changelog_dir / "README.md").write_text("README content")
    (changelog_dir / ".gitkeep").write_text("")

    fragments = _find_fragments(changelog_dir.parent)
    assert all(len(frags) == 0 for frags in fragments.values())


def test_find_fragments_mixed_types(changelog_dir: Path) -> None:
    """Test finding multiple fragment types."""
    (changelog_dir / "1.feature.md").write_text("Feature")
    (changelog_dir / "2.bugfix.md").write_text("Bugfix")
    (changelog_dir / "3.doc.md").write_text("Doc")

    fragments = _find_fragments(changelog_dir.parent)
    assert len(fragments["feature"]) == 1
    assert len(fragments["bugfix"]) == 1
    assert len(fragments["doc"]) == 1


def _empty_fragments() -> dict[str, list[str]]:
    return {
        "major": [],
        "breaking": [],
        "removal": [],
        "feature": [],
        "deprecation": [],
        "bugfix": [],
        "doc": [],
        "misc": [],
    }


def test_determine_bump_type_none() -> None:
    """Test bump type with no fragments."""
    assert _determine_bump_type(_empty_fragments()) is None


def test_determine_bump_type_major_fragment() -> None:
    """Test major bump with major fragments."""
    fragments = _empty_fragments()
    fragments["major"] = ["1.major.md"]
    assert _determine_bump_type(fragments) == "major"


def test_determine_bump_type_breaking_fragment() -> None:
    """Test major bump with breaking fragments."""
    fragments = _empty_fragments()
    fragments["breaking"] = ["1.breaking.md"]
    assert _determine_bump_type(fragments) == "major"


def test_determine_bump_type_major() -> None:
    """Test major bump with removal fragments."""
    fragments = _empty_fragments()
    fragments["removal"] = ["1.removal.md"]
    assert _determine_bump_type(fragments) == "major"


def test_determine_bump_type_major_with_others() -> None:
    """Test major bump takes precedence over other types."""
    fragments = _empty_fragments()
    fragments["removal"] = ["1.removal.md"]
    fragments["feature"] = ["2.feature.md"]
    fragments["bugfix"] = ["3.bugfix.md"]
    assert _determine_bump_type(fragments) == "major"


def test_determine_bump_type_breaking_with_others() -> None:
    """Test breaking bump takes precedence over minor and patch types."""
    fragments = _empty_fragments()
    fragments["breaking"] = ["1.breaking.md"]
    fragments["feature"] = ["2.feature.md"]
    fragments["bugfix"] = ["3.bugfix.md"]
    assert _determine_bump_type(fragments) == "major"


def test_determine_bump_type_minor_feature() -> None:
    """Test minor bump with feature fragments."""
    fragments = _empty_fragments()
    fragments["feature"] = ["1.feature.md"]
    assert _determine_bump_type(fragments) == "minor"


def test_determine_bump_type_minor_deprecation() -> None:
    """Test minor bump with deprecation fragments."""
    fragments = _empty_fragments()
    fragments["deprecation"] = ["1.deprecation.md"]
    assert _determine_bump_type(fragments) == "minor"


def test_determine_bump_type_minor_with_patch() -> None:
    """Test minor bump takes precedence over patch types."""
    fragments = _empty_fragments()
    fragments["feature"] = ["1.feature.md"]
    fragments["bugfix"] = ["2.bugfix.md"]
    fragments["doc"] = ["3.doc.md"]
    assert _determine_bump_type(fragments) == "minor"


def test_determine_bump_type_patch_bugfix() -> None:
    """Test patch bump with bugfix fragments."""
    fragments = _empty_fragments()
    fragments["bugfix"] = ["1.bugfix.md"]
    assert _determine_bump_type(fragments) == "patch"


def test_determine_bump_type_patch_doc() -> None:
    """Test patch bump with doc fragments."""
    fragments = _empty_fragments()
    fragments["doc"] = ["1.doc.md"]
    assert _determine_bump_type(fragments) == "patch"


def test_determine_bump_type_patch_misc() -> None:
    """Test patch bump with misc fragments."""
    fragments = _empty_fragments()
    fragments["misc"] = ["1.misc.md"]
    assert _determine_bump_type(fragments) == "patch"


def test_determine_bump_type_patch_mixed() -> None:
    """Test patch bump with multiple patch-level fragment types."""
    fragments = _empty_fragments()
    fragments["bugfix"] = ["1.bugfix.md"]
    fragments["doc"] = ["2.doc.md"]
    fragments["misc"] = ["3.misc.md"]
    assert _determine_bump_type(fragments) == "patch"


def test_version_from_fragments_exact(
    changelog_dir: Path, config: _config.Configuration
) -> None:
    """Test version scheme when exactly on a tag."""
    version = ScmVersion(
        tag=Version("1.2.3"),
        distance=0,
        node="abc123",
        dirty=False,
        config=config,
    )
    result = version_from_fragments(version)
    assert result == "1.2.3"


def test_version_from_fragments_no_fragments(
    changelog_dir: Path, config: _config.Configuration
) -> None:
    """Test version scheme with no fragments falls back to guess-next-dev."""
    version = ScmVersion(
        tag=Version("1.2.3"),
        distance=5,
        node="abc123",
        dirty=False,
        config=config,
    )
    result = version_from_fragments(version)
    # Should fall back to guess_next_dev_version behavior
    assert result.startswith("1.2.4.dev5")


def test_version_from_fragments_major_bump(
    changelog_dir: Path, config: _config.Configuration
) -> None:
    """Test version scheme with removal fragments (major bump)."""
    (changelog_dir / "1.removal.md").write_text("Remove old API")

    version = ScmVersion(
        tag=Version("1.2.3"),
        distance=5,
        node="abc123",
        dirty=False,
        config=config,
    )
    result = version_from_fragments(version)
    assert result.startswith("2.0.0.dev5")


def test_version_from_fragments_major_fragment_bump(
    changelog_dir: Path, config: _config.Configuration
) -> None:
    """Test version scheme with major fragments (major bump)."""
    (changelog_dir / "1.major.md").write_text("First stable release")

    version = ScmVersion(
        tag=Version("0.5.3"),
        distance=5,
        node="abc123",
        dirty=False,
        config=config,
    )
    result = version_from_fragments(version)
    assert result.startswith("1.0.0.dev5")


def test_version_from_fragments_breaking_fragment_bump(
    changelog_dir: Path, config: _config.Configuration
) -> None:
    """Test version scheme with breaking fragments (major bump)."""
    (changelog_dir / "1.breaking.md").write_text("Breaking API change")

    version = ScmVersion(
        tag=Version("2.1.0"),
        distance=3,
        node="def456",
        dirty=False,
        config=config,
    )
    result = version_from_fragments(version)
    assert result.startswith("3.0.0.dev3")


def test_version_from_fragments_minor_bump(
    changelog_dir: Path, config: _config.Configuration
) -> None:
    """Test version scheme with feature fragments (minor bump)."""
    (changelog_dir / "1.feature.md").write_text("Add new feature")

    version = ScmVersion(
        tag=Version("1.2.3"),
        distance=5,
        node="abc123",
        dirty=False,
        config=config,
    )
    result = version_from_fragments(version)
    assert result.startswith("1.3.0.dev5")


def test_version_from_fragments_patch_bump(
    changelog_dir: Path, config: _config.Configuration
) -> None:
    """Test version scheme with bugfix fragments (patch bump)."""
    (changelog_dir / "1.bugfix.md").write_text("Fix bug")

    version = ScmVersion(
        tag=Version("1.2.3"),
        distance=5,
        node="abc123",
        dirty=False,
        config=config,
    )
    result = version_from_fragments(version)
    assert result.startswith("1.2.4.dev5")


def test_version_from_fragments_precedence(
    changelog_dir: Path, config: _config.Configuration
) -> None:
    """Test that removal > feature > bugfix precedence works."""
    # Add all three types - removal should win
    (changelog_dir / "1.removal.md").write_text("Remove API")
    (changelog_dir / "2.feature.md").write_text("Add feature")
    (changelog_dir / "3.bugfix.md").write_text("Fix bug")

    version = ScmVersion(
        tag=Version("1.2.3"),
        distance=5,
        node="abc123",
        dirty=False,
        config=config,
    )
    result = version_from_fragments(version)
    # Should use major bump
    assert result.startswith("2.0.0.dev5")


def test_version_from_fragments_minor_over_patch(
    changelog_dir: Path, config: _config.Configuration
) -> None:
    """Test that feature takes precedence over bugfix."""
    (changelog_dir / "1.feature.md").write_text("Add feature")
    (changelog_dir / "2.bugfix.md").write_text("Fix bug")

    version = ScmVersion(
        tag=Version("1.2.3"),
        distance=5,
        node="abc123",
        dirty=False,
        config=config,
    )
    result = version_from_fragments(version)
    # Should use minor bump
    assert result.startswith("1.3.0.dev5")


def test_version_from_fragments_deprecation_is_minor(
    changelog_dir: Path, config: _config.Configuration
) -> None:
    """Test that deprecation triggers a minor bump."""
    (changelog_dir / "1.deprecation.md").write_text("Deprecate method")

    version = ScmVersion(
        tag=Version("1.2.3"),
        distance=5,
        node="abc123",
        dirty=False,
        config=config,
    )
    result = version_from_fragments(version)
    assert result.startswith("1.3.0.dev5")


def test_version_from_fragments_doc_is_patch(
    changelog_dir: Path, config: _config.Configuration
) -> None:
    """Test that doc changes trigger a patch bump."""
    (changelog_dir / "1.doc.md").write_text("Update docs")

    version = ScmVersion(
        tag=Version("1.2.3"),
        distance=5,
        node="abc123",
        dirty=False,
        config=config,
    )
    result = version_from_fragments(version)
    assert result.startswith("1.2.4.dev5")


def test_version_from_fragments_misc_is_patch(
    changelog_dir: Path, config: _config.Configuration
) -> None:
    """Test that misc changes trigger a patch bump."""
    (changelog_dir / "1.misc.md").write_text("Refactor")

    version = ScmVersion(
        tag=Version("1.2.3"),
        distance=5,
        node="abc123",
        dirty=False,
        config=config,
    )
    result = version_from_fragments(version)
    assert result.startswith("1.2.4.dev5")


def test_version_from_fragments_major_from_0_x(
    changelog_dir: Path, config: _config.Configuration
) -> None:
    """Test major bump from 0.x version."""
    (changelog_dir / "1.removal.md").write_text("Remove API")

    version = ScmVersion(
        tag=Version("0.5.3"),
        distance=5,
        node="abc123",
        dirty=False,
        config=config,
    )
    result = version_from_fragments(version)
    assert result.startswith("1.0.0.dev5")


def test_version_from_fragments_minor_from_0_x(
    changelog_dir: Path, config: _config.Configuration
) -> None:
    """Test minor bump from 0.x version."""
    (changelog_dir / "1.feature.md").write_text("Add feature")

    version = ScmVersion(
        tag=Version("0.5.3"),
        distance=5,
        node="abc123",
        dirty=False,
        config=config,
    )
    result = version_from_fragments(version)
    assert result.startswith("0.6.0.dev5")


def test_version_from_fragments_missing_changelog_dir(
    config: _config.Configuration,
) -> None:
    """Test version scheme when changelog.d directory doesn't exist."""
    version = ScmVersion(
        tag=Version("1.2.3"),
        distance=5,
        node="abc123",
        dirty=False,
        config=config,
    )
    # Should fall back to guess-next-dev when directory is missing
    result = version_from_fragments(version)
    assert result.startswith("1.2.4.dev5")


def test_version_from_fragments_dirty(
    changelog_dir: Path, config: _config.Configuration
) -> None:
    """Test version scheme with dirty working directory."""
    (changelog_dir / "1.feature.md").write_text("Add feature")

    version = ScmVersion(
        tag=Version("1.2.3"),
        distance=5,
        node="abc123",
        dirty=True,
        config=config,
    )
    result = version_from_fragments(version)
    # Should still bump correctly, dirty flag affects local version
    assert result.startswith("1.3.0.dev5")
