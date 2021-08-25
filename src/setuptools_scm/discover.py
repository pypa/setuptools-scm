import os

from ._trace import trace
from .utils import iter_entry_points


def walk_potential_roots(root, search_parents=True):
    """
    Iterate though a path and each of its parents.
    :param root: File path.
    :param search_parents: If ``False`` the parents are not considered.
    """

    if not search_parents:
        yield root
        return

    tail = root

    while tail:
        yield root
        root, tail = os.path.split(root)


def match_entrypoint(root, name):
    """
    Consider a ``root`` as entry-point.
    :param root: File path.
    :param name: Subdirectory name.
    :return: ``True`` if a subdirectory ``name`` exits in ``root``.
    """

    if os.path.exists(os.path.join(root, name)):
        if not os.path.isabs(name):
            return True
        trace("ignoring bad ep", name=name, indent=2)

    return False


def iter_matching_entrypoints(path, entrypoint, config):
    """
    Consider different entry-points in ``root`` and optionally its parents.
    :param root: File path.
    :param entrypoint: Entry-point to consider.
    :param config: Configuration,
        read ``search_parent_directories``, write found parent to ``parent``.
    """

    trace("looking for ep", entrypoint=entrypoint, path=path)

    for wd in walk_potential_roots(path, config.search_parent_directories):
        for ep in iter_entry_points(entrypoint):
            if match_entrypoint(wd, ep.name):
                trace("found ep", ep=ep, wd=wd)
                config.parent = wd
                yield ep
