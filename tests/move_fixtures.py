"""Original disposable bytes; relocation tests never use private media."""
import io
import json
import os
from pathlib import Path
import tempfile
import unittest

from dup_media.move_fs import runtime, MoveError
from dup_media.relocate import Relocation
from dup_media.scan import DEFAULT_EXTENSIONS


def make_tree(root):
    root.mkdir()
    (root / 'nested').mkdir()
    (root / 'a.jpg').write_bytes(b'a' * 100)
    (root / 'nested/b.jpg').write_bytes(b'a' * 100)
    (root / 'unique.wav').write_bytes(b'u' * 50)
    (root / 'ignored.txt').write_bytes(b'a' * 100)


def tree(root):
    if not root.exists():
        return None
    result = {}
    for p in root.rglob('*'):
        if p.is_file():
            info = p.stat()
            result[str(p.relative_to(root))] = (p.read_bytes(), info.st_mode, info.st_uid,
                                               info.st_gid, info.st_mtime_ns)
    return result


class MoveFixture(unittest.TestCase):
    def setUp(self):
        try:
            runtime()
        except MoveError:
            if os.environ.get('REQUIRE_MOVE_TESTS') == '1':
                raise
            self.skipTest('privileged Linux metadata adapter required')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.source = self.base / 'source'
        self.dest = self.base / 'dest'
        self.journal = self.base / 'operation'
        make_tree(self.source)

    def run_move(self, dry=False):
        out = io.StringIO()
        code = Relocation(self.source, self.dest, None if dry else self.journal).run(DEFAULT_EXTENSIONS, out, dry)
        return code, [json.loads(s) for s in out.getvalue().splitlines()]
