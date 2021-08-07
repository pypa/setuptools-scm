from .utils import do
from .utils import do_ex
from .utils import require_command


class Workdir:
    def __init__(self, path):
        require_command(self.COMMAND)
        self.path = path

    def do_ex(self, cmd):
        return do_ex(cmd, cwd=self.path)

    def do(self, cmd):
        return do(cmd, cwd=self.path)
