"""Exceptions raised by vcs-versioning."""


class DirtyWorkingTreeError(ValueError):
    """Raised when the ``fail-on-uncommitted-changes`` local scheme sees a dirty tree."""
