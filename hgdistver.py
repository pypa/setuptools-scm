"""
:copyright: 2010 by Ronny Pfannschmidt
:license: MIT

"""

# Genscript Metadata

import re
import os
import sys
import shlex
import subprocess

def trace_debug(*k):
    sys.stdout.write(' '.join(map(str,k)))
    sys.stdout.write('\n')
    sys.stdout.flush()

def trace(*k):
    pass


def do_ex(cmd, cwd='.'):
    trace('cmd', repr(cmd))
    p = subprocess.Popen(
        shlex.split(cmd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=cwd,
        env=dict(os.environ,
                 #disable hgrc processing other than .hg/hgrc
                 HGRCPATH='',
                 # try to disable i18n
                 LC_ALL='C',
                 LANGUAGE='',
                 HGPLAIN='1',
                )
    )
    out, err = p.communicate()
    trace('out', repr(out))
    trace('err', repr(err))
    trace('ret', p.returncode)
    return out.strip().decode(), err.strip().decode(), p.returncode

def do(cmd, cwd='.'):
    out, err, ret = do_ex(cmd, cwd)
    if ret:
        print(err)
    return out

# extended pep 386 regex
# see http://www.python.org/dev/peps/pep-0386/#the-new-versioning-algorithm
version_re = r"""^
(?P<prefix>\w+-?)?         # any text, may have a dash
                              # custom to deal with tag prefixes
(?P<version>\d+\.\d+)         # minimum 'N.N'
(?P<extraversion>(?:\.\d+)*)  # any number of extra '.N' segments
(?P<prerelfullversion>
(:?
    (?P<prerel>[abc]|rc)         # 'a' = alpha, 'b' = beta
                                 # 'c' or 'rc' = release candidate
    (?P<prerelversion>\d+(?:\.\d+)*)
)?)
# we dont mach those, its our job to generate them
##(?P<postdev>(\.post(?P<post>\d+))?(\.dev(?P<dev>\d+))?)?
$"""


def tag_to_version(tag):
    match = re.match(version_re, tag, re.VERBOSE)
    if match is not None:
        return ''.join(match.group(
            'version', 'extraversion', 'prerelfullversion',
        ))


def tags_to_versions(tags):
    return list(filter(None, map(tag_to_version, tags)))


def version_from_cachefile(root, cachefile=None):
    #XXX: for now we ignore root
    if not cachefile or not os.path.exists(cachefile):
        return
    #replaces 'with open()' from py2.6
    fd = open(cachefile)
    fd.readline()  # remove the comment
    version = None
    try:
        line = fd.readline()
        version_string = line.split(' = ')[1].strip()
        version = version_string[1:-1]
    except:  # any error means invalid cachefile
        pass
    fd.close()
    return version


def version_from_hg_id(root, cachefile=None):
    """stolen logic from mercurials setup.py as well"""
    l = do('hg id -i -t', root).split()
    node = l.pop(0)
    tags = tags_to_versions(l)
    if tags:
        return tags[0] + node[12:]  # '' or '+'


def _hg_tagdist_normalize_tagcommit(root, tag, dist, node):
    st = do('hg st --no-status --change %s' % str(node), root)

    trace('normalize', locals())
    if int(dist) == 1 and st == '.hgtags':
        return tag
    else:
        return '%s.post%s-%s' % (tag, dist, node)


def version_from_hg15_parents(root, cachefile=None):
    node = do('hg id -i', root)
    if node.strip('+') == '000000000000':
        return '0.0.post0-' + node

    cmd = 'hg parents --template "{latesttag} {latesttagdistance}"'
    out = do(cmd, root)
    try:
        tag, dist = out.split()
        if tag == 'null':
            tag = '0.0'
        else:
            tag = tag_to_version(tag)
        return _hg_tagdist_normalize_tagcommit(root, tag, dist, node)
    except ValueError:
        pass  # unpacking failed, old hg


def version_from_hg_log_with_tags(root, cachefile=None):
    #NOTE: this is only a fallback called from version_from_hg15_parents
    node = do('hg id -i', root)
    cmd = r'hg log -r %s:0 --template "{tags} \n"'
    cmd = cmd % node.rstrip('+')
    proc = subprocess.Popen(cmd,
                            cwd=root,
                            shell=True,
                            stdout=subprocess.PIPE,
                           )
    dist = -1  # no revs vs one rev is tricky

    for dist, line in enumerate(proc.stdout):
        line = line.decode()
        tags = tags_to_versions(line.split())
        if tags:
            return _hg_tagdist_normalize_tagcommit(root, tags[0], dist, node)

    return  '0.0.post%s-%s' % (dist + 1, node)


def _hg_version():
    hgver_out = do('hg --version')
    hgver_out = hgver_out.splitlines()[0].rstrip(')')
    return hgver_out.split('version ')[-1]


def version_from_hg(root, cachefile=None):
    # no .hg means no way to get it
    if not os.path.isdir(os.path.join(root, '.hg')):
        return
    # if id has a tag we are lucky
    version_from_id = version_from_hg_id(root)
    if version_from_id:
        return version_from_id
    if _hg_version() < '1.5':
        return version_from_hg_log_with_tags(root)
    else:
        return version_from_hg15_parents(root)


def version_from_git(root, cachefile=None):
    if not os.path.exists(os.path.join(root, '.git')):
        return
    valid_retcode = do_ex('git rev-parse --verify --quiet HEAD', root)
    if valid_retcode[2]:
        return "0.0.post0"

    out, err, ret = do_ex('git describe --dirty --tags --always', root)
    if '-' not in out and '.' not in out:
        revs = do('git rev-list HEAD', root)
        count = revs.count('\n')
        return '0.0.post%s-%s' % (count + 1, out)
    if ret:
        return
    if '-' not in out:
        return tag_to_version(out)
    else:
        tag, number, node = out.split('-')
        return '%s.post%s-%s' % (tag_to_version(tag), number, node)


def _archival_to_version(data):
    """stolen logic from mercurials setup.py"""
    if 'tag' in data:
        return tag_to_version(data['tag'])
    elif 'latesttag' in data:
        return '%(latesttag)s.post%(latesttagdistance)s-%(node).12s' % data
    else:
        return data.get('node', '')[:12]


def _data_from_archival(path):
    fp = open(path)
    try:
        content = fp.read()
    finally:
        fp.close()
    # the complex conditions come from reading pseudo-mime-messages
    return dict(x.split(': ', 1) 
                for x in content.splitlines()
                if x.strip() and ': ' in x)

def version_from_archival(root, cachefile=None):
    for parent in root, os.path.dirname(root):
        archival = os.path.join(parent, '.hg_archival.txt')
        if os.path.exists(archival):
            data = _data_from_archival(archival)
            return _archival_to_version(data)


def version_from_sdist_pkginfo(root, cachefile=None):
    pkginfo = os.path.join(root, 'PKG-INFO')
    if os.path.exists(pkginfo):
        data = _data_from_archival(pkginfo)
        version = data.get('Version')
        if version != 'UNKNOWN':
            return version


def write_cachefile(path, version):
    fd = open(path, 'w')
    try:
        fd.write('# this file is autogenerated by hgdistver + setup.py\n')
        fd.write('version = "%s"\n' % version)
    finally:
        fd.close()


methods = [
    version_from_hg,
    version_from_git,
    version_from_cachefile,
    version_from_sdist_pkginfo,
    version_from_archival,
]


def get_version(cachefile=None, root=None):
    if root is None:
        root = os.getcwd()
    if cachefile is not None:
        cachefile = os.path.join(root, cachefile)
    try:
        version = None
        for method in methods:
            version = method(root=root, cachefile=cachefile)
            if version:
                if version.endswith('+'):
                    import time
                    version += time.strftime('%Y%m%d')
                return str(version)
    finally:
        if cachefile and version:
            write_cachefile(cachefile, version)


def setuptools_version_keyword(dist, keyword, value):
    if value:
        dist.metadata.version = get_version(
            cachefile=getattr(dist, 'cache_hg_version_to', None))


def setuptools_cachefile_keyword(dist, keyword, value):
    pass



def find_hg_files(dirname=''):
    return do('hg st -armdc --no-status', dirname or '.').splitlines()

def find_git_files(dirname=''):

    return do('git ls-files', dirname or '.').splitlines()



def findroot(path, req):
    old = None
    while path != old:
        if os.path.exists(os.path.join(path, req)):
            return path
        old = path
        path = os.path.dirname(path)


def find_files(dirname=''):
    abs = os.path.abspath(dirname)
    hg = findroot(abs, '.hg')
    git = findroot(abs, '.git')
    if hg and git:
        m = max(hg, git)
        if max is hg:
            git = None
    if hg:
        return find_hg_files(dirname)
    elif git:
        return find_git_files(dirname)



if __name__ == '__main__':
    print('Guessed Version %s' % (get_version(),))
    if 'ls' in sys.argv:
        for fname in find_files('.'):
            print fname
