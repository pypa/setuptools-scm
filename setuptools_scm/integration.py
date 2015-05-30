import os

from .version import _warn_if_setuptools_outdated
from .utils import trace, do
from .discover import find_matching_entrypoint
from . import get_version

def version_keyword(dist, keyword, value):
    _warn_if_setuptools_outdated()
    if not value:
        return
    if value is True:
        value = {}
    if getattr(value, '__call__', None):
        value = value()
    try:
        dist.metadata.version = get_version(**value)
    except Exception as e:
        trace('error', e)


def find_files(path='.'):
    if not path:
        path = '.'
    abs = os.path.abspath(path)
    ep = find_matching_entrypoint(abs, 'setuptools_scm.files_command')
    if ep:
        command = ep.load()
        try:
            if isinstance(command, str):
                return do(ep.load(), path).splitlines()
            else:
                return command(path)
        except Exception as e:
            import traceback
            print("File Finder Failed for %s" % ep)
            traceback.print_exc()
            return []

    else:
        return []
