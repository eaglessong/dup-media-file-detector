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


# Shared behavioral recipes for both direct integration and shipped CLI regression.
PERMISSION_CASES = (
    'source_mode', 'destination_existing_mode', 'destination_missing_mode',
    'journal_mode', 'source_acl', 'destination_file_acl',
    'destination_directory_acl', 'destination_cleanup_acl', 'journal_acl',
    'destination_file_inheritance', 'destination_directory_inheritance',
)


def namespace_snapshot(root):
    """Include directory modes/times and files; exclude normal read-atime effects."""
    from tests.move_fixtures import namespace_snapshot as full_snapshot
    return full_snapshot(root)


from contextlib import contextmanager


@contextmanager
def permission_tree(case):
    import io
    import json
    import subprocess
    from types import SimpleNamespace
    from dup_media.relocate import Relocation
    from dup_media.scan import DEFAULT_EXTENSIONS

    with tempfile.TemporaryDirectory() as t:
        base = Path(t).resolve()
        source, dest, journal = base / 'source', base / 'dest', base / 'operation'
        make_tree(source)
        (source / 'c.jpg').write_bytes(b'second exact group')
        late = source / 'zz-blocked'
        late.mkdir()
        victim = late / 'second.jpg'
        victim.write_bytes(b'second exact group')
        acl_paths = []
        writable_dirs = []
        foreign = False

        def acl(path, rule):
            subprocess.run(['chmod', '+a', rule, str(path)], check=True, capture_output=True)
            acl_paths.append(path)

        def mode(path, value):
            writable_dirs.append(path)
            path.chmod(value)

        def denied(action):
            try:
                action()
            except PermissionError:
                return
            raise AssertionError('native permission fixture did not deny its claimed action')

        try:
            if case in ('source_mode', 'source_acl'):
                control = late / 'permission-control.txt'
                control.write_bytes(b'unselected control')
                if case == 'source_mode':
                    mode(late, 0o555)
                else:
                    acl(late, 'everyone deny delete_child')
                    acl(victim, 'everyone deny delete')
                    acl(control, 'everyone deny delete')
                denied(control.unlink)
                expected = 'source_permission_denied'
            elif case.startswith('destination_'):
                dest.mkdir()
                if case == 'destination_existing_mode':
                    mode(dest, 0o555)
                    denied(lambda: (dest / 'control').touch())
                elif case == 'destination_missing_mode':
                    mode(dest, 0o555)
                    denied(lambda: (dest / 'control').mkdir())
                    dest = dest / 'missing' / 'archive'
                elif case == 'destination_file_acl':
                    # Victims are nested, so check an existing final parent.
                    (dest / 'nested').mkdir()
                    acl(dest / 'nested', 'everyone deny add_file')
                    denied(lambda: (dest / 'nested' / 'control').touch())
                elif case == 'destination_directory_acl':
                    acl(dest, 'everyone deny add_subdirectory')
                    denied(lambda: (dest / 'control').mkdir())
                    dest = dest / 'missing'
                elif case == 'destination_cleanup_acl':
                    (dest / 'nested').mkdir()
                    control = dest / 'nested/control'
                    control.touch()
                    acl(dest / 'nested', 'everyone deny delete_child')
                    acl(control, 'everyone deny delete')
                    denied(control.unlink)
                else:
                    inheritance = ('file_inherit' if case.endswith('file_inheritance')
                                   else 'directory_inherit')
                    acl(dest, 'everyone deny add_file,' + inheritance + ',only_inherit')
                expected = ('permission_inheritance_unsupported' if 'inheritance' in case
                            else 'destination_permission_denied')
            elif case in ('journal_mode', 'journal_acl'):
                parent = base / 'operations'
                parent.mkdir()
                journal = parent / 'new-operation'
                if case == 'journal_mode':
                    mode(parent, 0o555)
                else:
                    acl(parent, 'everyone deny add_subdirectory')
                denied(lambda: (parent / 'control').mkdir())
                expected = 'journal_permission_denied'
            elif case == 'sticky_foreign':
                # Privileged fixture preparation ONLY. Application always ordinary user.
                mode(late, 0o1777)
                victim.chmod(0o644)  # Keep the foreign-owned file readable under umask077.
                try:
                    result = subprocess.run(['sudo', '-n', 'chown', '0:0', str(victim), str(late)],
                                            capture_output=True, text=True)
                    available = result.returncode == 0
                except OSError:
                    available = False
                if not available:
                    if os.environ.get('REQUIRE_MAC_MOVE_TESTS') == '1':
                        raise AssertionError('required foreign-owner fixture setup unavailable')
                    raise unittest.SkipTest('passwordless ownership setup required; mandatory in macOS CI')
                foreign = True
                assert late.stat().st_uid == victim.stat().st_uid == 0
                assert os.geteuid() != 0
                denied(victim.unlink)
                expected = 'source_permission_denied'
            elif case == 'creation_acl':
                dest.mkdir()
                acl(dest, 'everyone allow add_file,add_subdirectory,delete_child,search')
                expected = None
            elif case == 'sticky_owner':
                mode(late, 0o1777)
                expected = None
            elif case == 'acl_grants_delete':
                mode(late, 0o555)
                acl(late, 'everyone allow delete_child')
                expected = None
            else:
                raise AssertionError('unknown permission fixture')

            def run(dry):
                output = io.StringIO()
                code = Relocation(source, dest, None if dry else journal).run(DEFAULT_EXTENSIONS, output, dry)
                return code, [json.loads(line) for line in output.getvalue().splitlines()]

            yield SimpleNamespace(base=base, source=source, dest=dest, journal=journal,
                                  expected=expected, run=run)
        finally:
            if foreign:
                subprocess.run(['sudo', '-n', 'chown', f'{os.getuid()}:{os.getgid()}',
                                str(late), str(victim)], check=True, capture_output=True)
            for path in acl_paths:
                if path.exists():
                    subprocess.run(['chmod', '-N', str(path)], check=True, capture_output=True)
            for path in writable_dirs:
                path.chmod(0o700)
