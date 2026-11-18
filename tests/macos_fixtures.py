"""Original synthetic APFS fixtures; no media decoding or personal files."""
import ctypes
import os
from pathlib import Path
import sys
import tempfile
import unittest
from tests.move_fixtures import make_tree, MoveFixture


def set_attribute(path, key, value):
    api = ctypes.CDLL(None, use_errno=True)
    api.setxattr.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_void_p,
                            ctypes.c_size_t, ctypes.c_uint32, ctypes.c_int]
    if api.setxattr(os.fsencode(path), key.encode(), value, len(value), 0, 0) != 0:
        raise OSError(ctypes.get_errno(), 'synthetic attribute creation failed')


def get_attribute(path, key):
    api = ctypes.CDLL(None, use_errno=True)
    api.getxattr.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_void_p,
                            ctypes.c_size_t, ctypes.c_uint32, ctypes.c_int]
    api.getxattr.restype = ctypes.c_ssize_t
    data = ctypes.create_string_buffer(1024)
    size = api.getxattr(os.fsencode(path), key.encode(), data, len(data), 0, 0)
    if size < 0:
        import errno
        if ctypes.get_errno() == errno.ENOATTR:
            return None
        raise OSError(ctypes.get_errno(), 'synthetic attribute read failed')
    return data.raw[:size]


class MacFixture(unittest.TestCase):
    def setUp(self):
        if sys.platform != 'darwin':
            self.skipTest('native macOS APFS required')
        from dup_media.move_fs import runtime, filesystem
        runtime()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.source = self.base / 'source'
        self.dest = self.base / 'dest'
        self.journal = self.base / 'operation'
        make_tree(self.source)
        fd = os.open(self.source, os.O_RDONLY)
        try:
            self.assertEqual(filesystem(fd), 'apfs')
        finally:
            os.close(fd)

    run_move = MoveFixture.run_move
