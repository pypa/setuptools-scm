from .utils import do, do_ex, trace
from .version import meta, tag_to_version

FILES_COMMAND = 'git ls-files'


def parse(root):
    rev_node, _, ret = do_ex('git rev-parse --verify --quiet HEAD', root)
    if ret:
        return meta('0.0')
    rev_node = rev_node[:7]
    out, err, ret = do_ex('git describe --dirty --tags --long', root)
    if '-' not in out and '.' not in out:
        revs = do('git rev-list HEAD', root)
        count = revs.count('\n')
        if ret:
            out = rev_node
        return meta('0.0', distance=count + 1, node=out)
    if ret:
        return
    dirty = out.endswith('-dirty')
    if dirty:
        out = out.rsplit('-', 1)[0]

    tag, number, node = out.rsplit('-', 2)
    version = tag_to_version(tag)
    number = int(number)
    if number:
        return meta(version, distance=number, node=node, dirty=dirty)
    else:
        return meta(version, dirty=dirty, node=node)
