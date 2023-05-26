from __future__ import annotations

import logging
import textwrap
from pathlib import Path

from . import _types as _t

log = logging.getLogger(__name__)


def data_from_mime(path: _t.PathT) -> dict[str, str]:
    content = Path(path).read_text(encoding="utf-8")
    log.debug("mime %s content:\n%s", path, textwrap.indent(content, "    "))
    # the complex conditions come from reading pseudo-mime-messages
    data = dict(x.split(": ", 1) for x in content.splitlines() if ": " in x)

    log.debug("mime %s data:\n%s", path, data)
    return data
