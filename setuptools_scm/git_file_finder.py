# -*- coding: utf-8 -*-
# Copyright © 2018 ACSONE SA/NV
# License LGPLv3 (http://www.gnu.org/licenses/lgpl-3.0-standalone.html)

import os
import subprocess
import tarfile


def _git_toplevel(path):
    try:
        out = subprocess.check_output([
            'git', 'rev-parse', '--show-toplevel',
        ], cwd=(path or '.'), universal_newlines=True)
        return os.path.realpath(out.strip())
    except subprocess.CalledProcessError:
        # git returned error, we are not in a git repo
        return None
    except OSError:
        # git command not found, probably
        return None


def _git_ls_files_and_dirs(toplevel):
    # use git archive instead of git ls-file to honor
    # export-ignore git attribute
    cmd = ['git', 'archive', '--prefix', toplevel + os.path.sep, 'HEAD']
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, cwd=toplevel)
    tf = tarfile.open(fileobj=proc.stdout, mode='r|*')
    git_files = set()
    git_dirs = set([toplevel])
    for member in tf.getmembers():
        name = member.name.replace('/', os.path.sep)
        if member.type == tarfile.DIRTYPE:
            git_dirs.add(name)
        else:
            git_files.add(name)
    return git_files, git_dirs


def find_files(path=''):
    """ setuptools compatible git file finder that follows symlinks

    Spec here: http://setuptools.readthedocs.io/en/latest/setuptools.html#\
        adding-support-for-revision-control-systems
    """
    toplevel = _git_toplevel(path)
    if not toplevel:
        return []
    git_files, git_dirs = _git_ls_files_and_dirs(toplevel)
    realpath = os.path.realpath(path)
    assert realpath.startswith(toplevel)
    assert realpath in git_dirs
    seen = set()
    res = []
    for dirpath, dirnames, filenames in os.walk(realpath, followlinks=True):
        realdirpath = os.path.realpath(dirpath)  # resolve symlink
        if realdirpath not in git_dirs or realdirpath in seen:
            dirnames[:] = []
            continue
        for filename in filenames:
            fullfilename = os.path.join(dirpath, filename)  # with symlink
            if os.path.realpath(fullfilename) in git_files:
                res.append(
                    os.path.join(path, os.path.relpath(fullfilename, path)))
        seen.add(realdirpath)
    return res
