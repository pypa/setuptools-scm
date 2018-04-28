import os


def scm_find_files(path, scm_files, scm_dirs):
    """ setuptools compatible file finder that follows symlinks

    - path: the root directory from which to search
    - scm_files: set of scm controlled files
    - scm_files: set of scm controlled directories

    scm_files and scm_dirs must be absolute with symlinks resolved (realpath),
    with normalized case (normcase)

    Spec here: http://setuptools.readthedocs.io/en/latest/setuptools.html#\
        adding-support-for-revision-control-systems
    """
    realpath = os.path.normcase(os.path.realpath(path))
    seen = set()
    res = []
    for dirpath, dirnames, filenames in os.walk(realpath, followlinks=True):
        # dirpath with symlinks resolved
        realdirpath = os.path.normcase(os.path.realpath(dirpath))
        if realdirpath not in scm_dirs or realdirpath in seen:
            dirnames[:] = []
            continue
        for filename in filenames:
            # dirpath + filename with symlinks preserved
            fullfilename = os.path.join(dirpath, filename)
            if os.path.normcase(os.path.realpath(fullfilename)) in scm_files:
                res.append(
                    os.path.join(path, os.path.relpath(fullfilename, path)))
        seen.add(realdirpath)
    return res
